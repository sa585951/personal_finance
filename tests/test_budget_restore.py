"""R08: restore a monthly budget by its existing logical identity."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from urllib.parse import quote

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.schema import budgets_table, transaction_splits_table, transactions_table
from tests.test_account_request_integrity import account_snapshot
from tests.test_financial_command_idempotency import command_db  # noqa: F401
from tests.test_twd_monthly_reports import api_client


MONTH = "2026-11"
CATEGORY = "伙食"
ORIGINAL = {"month": MONTH, "category": CATEGORY, "amount": 1500, "notes": "old budget"}


def budget_rows(session):
    return session.execute(select(budgets_table).order_by(budgets_table.c.id)).all()


def ledger_snapshot(session):
    return [
        *account_snapshot(session),
        *[session.execute(select(table).order_by(*table.primary_key.columns)).all()
          for table in (transactions_table, transaction_splits_table)],
    ]


def test_set_budget_restores_deleted_row_and_updates_summary(command_db, monkeypatch):
    engine, data = command_db
    client, headers = api_client(monkeypatch, engine, data)
    assert client.post("/api/budgets", json=ORIGINAL, headers=headers).status_code == 201
    with Session(engine) as session:
        manager = BudgetManager(session)
        manager.set_budget(data["b"], MONTH, CATEGORY, 4100, "other owner")
        manager.set_budget(data["a"], "2026-12", CATEGORY, 4200, "other month")
        manager.set_budget(data["a"], MONTH, "交通", 4300, "other category")
        session.commit()
        before = ledger_snapshot(session)
        original = next(row for row in budget_rows(session) if row.notes == "old budget")
        unrelated = [row for row in budget_rows(session) if row.id != original.id]

    deleted = client.delete(f"/api/budgets/{MONTH}/{quote(CATEGORY)}", headers=headers)
    assert deleted.status_code == 200
    with Session(engine) as session:
        tombstone = next(row for row in budget_rows(session) if row.id == original.id)
        assert tombstone.deleted_at and tombstone.purge_after
    summary = client.get(f"/api/budgets/summary/{MONTH}", headers=headers)
    assert summary.status_code == 200
    assert all(row["category"] != CATEGORY for row in summary.json["data"])

    restored = client.post("/api/budgets", json={
        **ORIGINAL, "amount": "2300.5000", "notes": "new budget",
    }, headers=headers)
    assert restored.status_code == 201 and restored.json["success"] is True
    assert restored.json["data"]["transaction_id"] is None
    with Session(engine) as session:
        rows = budget_rows(session)
        row = next(row for row in rows if row.id == original.id)
        assert row.created_at == original.created_at
        assert (row.amount, row.notes, row.currency) == (Decimal("2300.5000"), "new budget", original.currency)
        assert row.deleted_at is None and row.purge_after is None
        assert [row for row in rows if row.id != original.id] == unrelated
        assert ledger_snapshot(session) == before
    summary = client.get(f"/api/budgets/summary/{MONTH}", headers=headers)
    assert summary.status_code == 200
    assert next(row for row in summary.json["data"] if row["category"] == CATEGORY) == {
        "category": CATEGORY, "budget": 2300.5, "spent": 0.0, "remaining": 2300.5, "notes": "new budget",
    }


def test_invalid_budget_amount_keeps_original_tombstone(command_db, monkeypatch):
    engine, data = command_db
    client, headers = api_client(monkeypatch, engine, data)
    assert client.post("/api/budgets", json=ORIGINAL, headers=headers).status_code == 201
    assert client.delete(f"/api/budgets/{MONTH}/{quote(CATEGORY)}", headers=headers).status_code == 200
    with Session(engine) as session:
        before = budget_rows(session)
    invalid = client.post("/api/budgets", json={**ORIGINAL, "amount": 0}, headers=headers)
    assert invalid.status_code == 400
    with Session(engine) as session:
        assert budget_rows(session) == before


@pytest.mark.parametrize("deleted", [False, True])
def test_concurrent_budget_settings_keep_one_row_and_coherent_values(command_db, deleted):
    engine, data = command_db
    owner = data["a"]
    original_id = None
    if deleted:
        with Session(engine) as session:
            manager = BudgetManager(session)
            manager.set_budget(owner, MONTH, CATEGORY, 1500, "old budget")
            original_id = budget_rows(session)[0].id
            manager.delete_budget(owner, MONTH, CATEGORY)
            session.commit()

    barrier = Barrier(2)
    intents = [(1900, "first"), (2700, "second")]

    def write(intent):
        with Session(engine) as session:
            barrier.wait(timeout=8)
            result = BudgetManager(session).set_budget(owner, MONTH, CATEGORY, *intent)
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert all(result[0] for result in executor.map(write, intents))
    with Session(engine) as session:
        rows = budget_rows(session)
        assert len(rows) == 1
        row = rows[0]
        if original_id is not None:
            assert row.id == original_id
        assert row.user_id == owner and row.period_start == date(2026, 11, 1)
        assert (row.amount, row.notes) in intents
        assert row.deleted_at is None and row.purge_after is None
