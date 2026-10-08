from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.receipt_import_service import ReceiptImportService
from models.schema import metadata, transactions_table, accounts_table, account_movements_table
from models.seed_data import seed_reference_data
from models.taiwan_invoice import parse_invoice_qr
from models.transaction_service import TransactionService
from models.user_manager import UserManager
from tests.test_schema_smoke import _get_test_database_url


def qr(number="AB12345678", amount=120):
    return number + "1151001" + "1234" + "00000000" + f"{amount:08X}" + "00000000" + "12345678" + "A" * 22 + "=="


def test_invoice_header_parses_without_retaining_secret_fields():
    result = parse_invoice_qr(qr(), today=date(2026, 10, 8))
    assert result == {"invoice_number": "AB12345678", "issued_on": date(2026, 10, 1),
                      "seller_identifier": "12345678", "total_amount": Decimal(120), "currency": "TWD"}


@pytest.mark.parametrize("payload", [None, "**right", "x" * 77, qr(amount=0),
    qr().replace("1151001", "1150230"), qr().replace("12345678A", "00000000A"),
    qr().replace("00000078", "000000ZZ"), qr() + "not-a-colon"])
def test_invalid_invoice_headers(payload):
    with pytest.raises(ValueError):
        parse_invoice_qr(payload, today=date(2026, 10, 8))


@pytest.fixture
def receipt_db():
    engine = create_engine(_get_test_database_url(), future=True)
    with engine.begin() as connection:
        metadata.drop_all(connection)
        metadata.create_all(connection)
        seed_reference_data(connection)
        users = UserManager(connection)
        owner = users.get_or_create_user_for_identity(provider="line", provider_user_id="receipt-owner", display_name="Owner")
        other = users.get_or_create_user_for_identity(provider="line", provider_user_id="receipt-other", display_name="Other")
        assets = AssetManager(connection)
        assets.add_account(owner["id"], "Receipt cash", "cash", 1000, currency="TWD")
        account = next(iter(assets.get_all_assets(owner["id"]).values()))["id"]
    yield engine, owner["id"], other["id"], account
    engine.dispose()


def service(session):
    return ReceiptImportService(session, TransactionService(BudgetManager(session), AssetManager(session)))


def create_payload(account):
    return {"action": "create", "item": "午餐", "budget_category": "伙食", "account_id": account, "merchant": "餐廳"}


def test_receipt_create_replay_isolation_and_deleted_transaction(receipt_db):
    engine, uid, other, account = receipt_db
    with Session(engine) as session:
        svc = service(session)
        first = svc.import_qr(uid, {"qr_payload": qr(), "input_method": "qr_camera"})
        rid = first["receipt"]["id"]
        assert not first["duplicate"]
        assert svc.import_qr(uid, {"qr_payload": qr(), "input_method": "qr_image"})["duplicate"]
        assert not svc.import_qr(other, {"qr_payload": qr(), "input_method": "qr_image"})["duplicate"]
        with pytest.raises(ValueError, match="權限"):
            svc.matches(other, rid)
        result = svc.resolve(uid, rid, create_payload(account))
        tid = result["receipt"]["transaction_id"]
        assert svc.resolve(uid, rid, create_payload(account))["replayed"]
        assert session.execute(select(accounts_table.c.balance).where(accounts_table.c.id == account)).scalar_one() == 880
        assert session.execute(select(func.count()).select_from(account_movements_table)).scalar_one() == 1
        BudgetManager(session).delete_transaction(uid, tid)
        assert svc.import_qr(uid, {"qr_payload": qr(), "input_method": "qr_camera"})["receipt"]["status"] == "pending"
        # Recreate must not replay a deleted transaction's client_request_id.
        recreated = svc.resolve(uid, rid, create_payload(account))
        assert recreated["receipt"]["transaction_id"] != tid
        session.commit()


def test_matches_and_link_do_not_modify_manual_transaction(receipt_db):
    engine, uid, _, account = receipt_db
    with Session(engine) as session:
        budgets = BudgetManager(session)
        for amount, day, kind in [(120, "2026-10-01", "expense"), (120, "2026-10-02", "expense"),
                                  (120, "2026-10-03", "expense"), (121, "2026-10-01", "expense"), (120, "2026-10-01", "income")]:
            budgets.add_transaction(uid, day, "手動", amount, kind, "伙食" if kind == "expense" else "薪資", merchant="餐廳")
        svc = service(session)
        rid = svc.import_qr(uid, {"qr_payload": qr(), "input_method": "qr_image"})["receipt"]["id"]
        candidates = svc.matches(uid, rid, "餐廳")["candidates"]
        assert len(candidates) == 2
        assert candidates[0]["date"] == "2026-10-01"
        before = session.execute(select(func.count()).select_from(transactions_table)).scalar_one()
        svc.resolve(uid, rid, {"action": "link", "transaction_id": candidates[0]["id"], "merchant": "別的名稱"})
        assert session.execute(select(func.count()).select_from(transactions_table)).scalar_one() == before
        assert session.execute(select(transactions_table.c.merchant).where(transactions_table.c.id == candidates[0]["id"])).scalar_one() == "餐廳"


def test_ignore_reopen_and_failed_create_rollback(receipt_db):
    engine, uid, _, account = receipt_db
    with Session(engine) as session:
        svc = service(session)
        rid = svc.import_qr(uid, {"qr_payload": qr(), "input_method": "qr_image"})["receipt"]["id"]
        svc.resolve(uid, rid, {"action": "ignore"})
        assert svc.import_qr(uid, {"qr_payload": qr(), "input_method": "qr_camera"})["receipt"]["status"] == "ignored"
        assert svc.resolve(uid, rid, {"action": "reopen"})["receipt"]["status"] == "pending"
        session.commit()
        with pytest.raises(ValueError):
            svc.resolve(uid, rid, {**create_payload(account), "account_id": str(uuid4())})
        session.rollback()
        assert session.execute(select(func.count()).select_from(transactions_table)).scalar_one() == 0
        assert session.execute(select(accounts_table.c.balance).where(accounts_table.c.id == account)).scalar_one() == 1000


def test_concurrent_import_and_confirm_only_post_once(receipt_db):
    engine, uid, _, account = receipt_db
    def import_one(source):
        with Session(engine) as session:
            result = service(session).import_qr(uid, {"qr_payload": qr(), "input_method": source})
            session.commit()
            return result["receipt"]["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(import_one, ["qr_camera", "qr_image"]))
    assert ids[0] == ids[1]
    def confirm(_):
        with Session(engine) as session:
            result = service(session).resolve(uid, ids[0], create_payload(account))
            session.commit()
            return result["receipt"]["transaction_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        tids = list(pool.map(confirm, [1, 2]))
    assert tids[0] == tids[1]
    with Session(engine) as session:
        assert session.execute(select(func.count()).select_from(transactions_table)).scalar_one() == 1
        assert session.execute(select(accounts_table.c.balance).where(accounts_table.c.id == account)).scalar_one() == 880


def test_failure_after_posting_rolls_back_movement_and_receipt(receipt_db, monkeypatch):
    engine, uid, _, account = receipt_db
    with Session(engine) as session:
        svc = service(session)
        rid = svc.import_qr(uid, {"qr_payload": qr(), "input_method": "qr_camera"})["receipt"]["id"]
        session.commit()
        def fail_link(*args, **kwargs):
            raise RuntimeError("simulated receipt persistence failure")
        monkeypatch.setattr(svc, "_update", fail_link)
        with pytest.raises(RuntimeError):
            svc.resolve(uid, rid, create_payload(account))
        session.rollback()
        assert session.execute(select(func.count()).select_from(transactions_table)).scalar_one() == 0
        assert session.execute(select(func.count()).select_from(account_movements_table)).scalar_one() == 0
        assert session.execute(select(accounts_table.c.balance).where(accounts_table.c.id == account)).scalar_one() == 1000
