"""Fixed monthly income and expenses: generation, confirming, skipping, editing, deleting."""
import io
import zipfile
from datetime import date
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from models.account_privacy import DELETE_CONFIRMATION, AccountPrivacyService
from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.recurring_manager import RecurringError, RecurringManager, due_date_for
from models.schema import recurring_occurrences_table as occurrences
from models.schema import recurring_rules_table as rules
from models.schema import categories_table, transactions_table
from models.transaction_service import TransactionService
from models.user_manager import UserManager
from tests.test_ai_parse_api import _load_web_app
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def manager(session):
    return RecurringManager(session, TransactionService(BudgetManager(session), AssetManager(session)))


def rent(data, **overrides):
    return {"title": "房租", "type": "expense", "budget_category": "住宿", "amount": "12000",
            "day_of_month": 5, "start_date": "2026-08-01", "account_id": str(data["cash"]), **overrides}


def category(session, kind="expense"):
    return session.scalar(select(categories_table.c.name).where(
        categories_table.c.kind == kind, categories_table.c.scope == "transaction",
        categories_table.c.user_id.is_(None)).limit(1))


def november(data, session, **overrides):
    return rent(data, budget_category=category(session), start_date="2026-11-01", **overrides)


def test_a_shorter_month_uses_its_last_day():
    assert due_date_for(date(2026, 2, 1), 31) == date(2026, 2, 28)
    assert due_date_for(date(2028, 2, 1), 31) == date(2028, 2, 29)
    assert due_date_for(date(2026, 4, 1), 31) == date(2026, 4, 30)
    assert due_date_for(date(2026, 4, 1), 5) == date(2026, 4, 5)


def test_generates_the_last_three_months_once(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        m.create_rule(data["a"], rent(data, budget_category=category(s)), today=date(2026, 8, 1))
        assert m.generate_due(data["a"], today=date(2026, 11, 20)) == 4 - 1  # Sep, Oct, Nov (Aug is out of the window)
        assert m.generate_due(data["a"], today=date(2026, 11, 20)) == 0  # idempotent
        pending = m.list_pending(data["a"])
        assert [p["due_date"] for p in pending] == ["2026-09-05", "2026-10-05", "2026-11-05"]
        s.commit()


def test_nothing_is_generated_before_the_day_or_before_the_start(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        m.create_rule(data["a"], rent(data, budget_category=category(s), start_date="2026-11-10"), today=date(2026, 11, 1))
        assert m.generate_due(data["a"], today=date(2026, 11, 20)) == 0   # Nov 5 is before the start date
        assert m.generate_due(data["a"], today=date(2026, 12, 4)) == 0    # Dec 5 has not come yet
        assert m.generate_due(data["a"], today=date(2026, 12, 5)) == 1
        s.rollback()


def test_end_date_and_pause_stop_generation(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        rule_id = m.create_rule(data["a"], rent(data, budget_category=category(s), end_date="2026-10-31"),
                                today=date(2026, 8, 1))
        assert m.generate_due(data["a"], today=date(2026, 12, 20)) == 1  # only Oct 5 falls in the window and range
        m.update_rule(data["a"], rule_id, {"is_active": False}, today=date(2026, 12, 20))
        m.update_rule(data["a"], rule_id, {"end_date": None}, today=date(2026, 12, 20))
        assert m.generate_due(data["a"], today=date(2026, 12, 20)) == 0
        assert m.list_rules(data["a"], today=date(2026, 12, 20))[0]["next_due"] is None
        s.rollback()


def test_confirming_creates_one_transaction_and_is_not_repeatable(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        m.create_rule(data["a"], november(data, s), today=date(2026, 11, 1))
        m.generate_due(data["a"], today=date(2026, 11, 20))
        [item] = m.list_pending(data["a"])
        before = s.scalar(select(func.count()).select_from(transactions_table))
        balance = AssetManager(s).get_all_assets(data["a"])
        cash_before = next(a["balance"] for a in balance.values() if a["bank_name"] == "cash")
        transaction_id = m.confirm(data["a"], item["id"], amount="500")
        assert s.scalar(select(func.count()).select_from(transactions_table)) == before + 1
        row = s.execute(select(transactions_table).where(transactions_table.c.id == UUID(transaction_id))).mappings().one()
        assert (row["title"], float(row["original_amount"]), row["transaction_date"]) == ("房租", 500.0, date(2026, 11, 5))
        cash_after = next(a["balance"] for a in AssetManager(s).get_all_assets(data["a"]).values() if a["bank_name"] == "cash")
        assert cash_before - cash_after == 500
        assert m.list_pending(data["a"]) == []
        with pytest.raises(RecurringError, match="已經處理"):
            m.confirm(data["a"], item["id"])
        s.rollback()


def test_an_unaffordable_confirm_fails_and_stays_pending(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        m.create_rule(data["a"], november(data, s), today=date(2026, 11, 1))  # 12,000 against a 1,000 balance
        m.generate_due(data["a"], today=date(2026, 11, 20))
        s.commit()
        [item] = m.list_pending(data["a"])
        with pytest.raises(ValueError, match="餘額不足"):
            m.confirm(data["a"], item["id"])
        s.rollback()
        assert [p["id"] for p in m.list_pending(data["a"])] == [item["id"]]


def test_pending_items_do_not_touch_the_ledger_until_confirmed(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        before = s.scalar(select(func.count()).select_from(transactions_table))
        m.create_rule(data["a"], november(data, s), today=date(2026, 11, 1))
        m.generate_due(data["a"], today=date(2026, 11, 20))
        assert s.scalar(select(func.count()).select_from(transactions_table)) == before
        s.rollback()


def test_changing_the_amount_keeps_it_pending_until_confirmed(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        m.create_rule(data["a"], november(data, s), today=date(2026, 11, 1))
        m.generate_due(data["a"], today=date(2026, 11, 20))
        [item] = m.list_pending(data["a"])
        before = s.scalar(select(func.count()).select_from(transactions_table))
        m.update_pending_amount(data["a"], item["id"], "300")
        assert s.scalar(select(func.count()).select_from(transactions_table)) == before
        [changed] = m.list_pending(data["a"])
        assert changed["amount"] == 300.0
        with pytest.raises(RecurringError, match="金額"):
            m.update_pending_amount(data["a"], item["id"], "0")
        m.confirm(data["a"], item["id"])
        with pytest.raises(RecurringError, match="已經處理"):
            m.update_pending_amount(data["a"], item["id"], "100")
        s.rollback()


def test_skipped_months_are_not_generated_again(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        m.create_rule(data["a"], november(data, s), today=date(2026, 11, 1))
        m.generate_due(data["a"], today=date(2026, 11, 20))
        m.skip(data["a"], m.list_pending(data["a"])[0]["id"])
        assert m.generate_due(data["a"], today=date(2026, 11, 21)) == 0
        assert m.list_pending(data["a"]) == []
        s.rollback()


def test_editing_a_rule_does_not_change_pending_items_but_deleting_removes_them(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        rule_id = m.create_rule(data["a"], november(data, s), today=date(2026, 11, 1))
        m.generate_due(data["a"], today=date(2026, 11, 20))
        m.update_rule(data["a"], rule_id, {"amount": "13000", "title": "新房租"}, today=date(2026, 11, 20))
        [item] = m.list_pending(data["a"])
        assert (item["title"], item["amount"]) == ("房租", 12000.0)
        assert m.list_rules(data["a"])[0]["amount"] == 13000.0
        m.generate_due(data["a"], today=date(2026, 12, 20))
        assert sorted(p["amount"] for p in m.list_pending(data["a"])) == [12000.0, 13000.0]

        m.delete_rule(data["a"], rule_id)
        assert m.list_rules(data["a"]) == [] and m.list_pending(data["a"]) == []
        assert s.scalar(select(func.count()).select_from(occurrences)) == 0
        s.rollback()


def test_rule_validation_and_isolation(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        good = rent(data, budget_category=category(s))
        for bad, message in (
            ({"amount": "0"}, "金額"), ({"amount": "abc"}, "金額"), ({"title": " "}, "項目"),
            ({"day_of_month": 32}, "1～31"), ({"type": "transfer"}, "類型"),
            ({"budget_category": "不存在的分類"}, "分類"), ({"end_date": "2026-07-01"}, "結束日"),
            ({"account_id": str(data["b_cash"])}, "帳戶"),  # someone else's account
        ):
            with pytest.raises(RecurringError, match=message):
                m.create_rule(data["a"], {**good, **bad}, today=date(2026, 8, 1))
        rule_id = m.create_rule(data["a"], good, today=date(2026, 8, 1))
        with pytest.raises(RecurringError):
            m.update_rule(data["b"], rule_id, {"title": "x"})
        with pytest.raises(RecurringError):
            m.delete_rule(data["b"], rule_id)
        assert m.list_rules(data["b"]) == []
        s.rollback()


def test_export_and_account_deletion_cover_recurring_data(command_db):
    engine, data = command_db
    with Session(engine) as s:
        m = manager(s)
        m.create_rule(data["b"], rent(data, budget_category=category(s), account_id=str(data["b_cash"])), today=date(2026, 8, 1))
        s.commit()
        from models.readable_export import build_workbook
        from openpyxl import load_workbook
        sheet = load_workbook(io.BytesIO(build_workbook(s, data["b"])))["固定收支"]
        assert [c.value for c in sheet[2]][:2] == ["房租", "支出"]
        archive = zipfile.ZipFile(io.BytesIO(AccountPrivacyService(s).export_zip(data["b"])))
        assert {"recurring_rules.csv", "recurring_occurrences.csv"} <= set(archive.namelist())

        AccountPrivacyService(s).delete_account(data["b"], DELETE_CONFIRMATION)
        s.commit()
        assert s.scalar(select(func.count()).select_from(rules).where(rules.c.user_id == data["b"])) == 0


@pytest.fixture
def api(command_db, monkeypatch):
    engine, _ = command_db
    app = _load_web_app(monkeypatch)
    db = scoped_session(sessionmaker(bind=engine))
    monkeypatch.setattr(app, "db_session", db)
    monkeypatch.setattr(app, "user_manager", UserManager(db))
    monkeypatch.setattr(app, "budget_manager", BudgetManager(db))
    monkeypatch.setattr(app, "asset_manager", AssetManager(db))
    monkeypatch.setattr(app, "DEV_AUTH_BYPASS", True)
    yield app.app.test_client(), engine
    db.remove()


def test_api_flow(api):
    client, engine = api
    kw = dict(base_url="http://localhost", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    with Session(engine) as s:
        name = category(s)
    created = client.post("/api/recurring/rules", json={
        "title": "訂閱", "type": "expense", "budget_category": name, "amount": 199,
        "day_of_month": 1, "start_date": "2020-01-01"}, **kw)
    assert created.status_code == 201, created.get_json()
    listing = client.get("/api/recurring", **kw).get_json()["data"]
    assert len(listing["rules"]) == 1 and len(listing["pending"]) == 3
    first = listing["pending"][0]["id"]
    assert client.post(f"/api/recurring/occurrences/{first}/confirm", json={}, **kw).status_code == 200
    assert client.post(f"/api/recurring/occurrences/{first}/confirm", json={}, **kw).status_code == 400
    skip = listing["pending"][1]["id"]
    assert client.put(f"/api/recurring/occurrences/{skip}", json={"amount": 55}, **kw).status_code == 200
    assert client.put(f"/api/recurring/occurrences/{skip}", json={"amount": -1}, **kw).status_code == 400
    assert client.post(f"/api/recurring/occurrences/{skip}/skip", **kw).status_code == 200
    assert len(client.get("/api/recurring", **kw).get_json()["data"]["pending"]) == 1
    bad = client.post("/api/recurring/rules", json={"title": "x"}, **kw)
    assert bad.status_code == 400
    rule_id = listing["rules"][0]["id"]
    assert client.delete(f"/api/recurring/rules/{rule_id}", **kw).status_code == 200
    assert client.get("/api/recurring", **kw).get_json()["data"] == {"rules": [], "pending": []}
