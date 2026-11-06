import base64
import json
from decimal import Decimal

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.schema import account_movements_table, accounts_table, transaction_splits_table, transactions_table
from models.trip_manager import TripManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401
from tests.test_twd_monthly_reports import api_client


@pytest.mark.parametrize("archived", [False, True])
def test_deleted_trip_preserves_private_share_and_restore_never_duplicates(command_db, monkeypatch, archived):
    engine, data = command_db
    owner, member, trip_id = data["a"], data["b"], data["trip"]
    with Session(engine) as session:
        trips = TripManager(session)
        trips.update_current_member_monthly_report_preference(member, trip_id, "include")
        session.execute(update(transactions_table).where(transactions_table.c.trip_id == trip_id).values(
            description="Shared private note", merchant="Shared private merchant",
        ))
        if archived:
            trips.archive_trip(owner, trip_id)
        session.commit()
        source = session.execute(select(transactions_table.c.id)).scalar_one()
        tables = (transactions_table, transaction_splits_table, accounts_table, account_movements_table)
        snapshot = [session.execute(select(t).order_by(t.c.id)).all() for t in tables]

    client, headers = api_client(monkeypatch, engine, {**data, "a": member})

    def report():
        response = client.get("/api/transactions?monthly_report=true&month=2026-10&limit=1", headers=headers)
        assert response.status_code == 200
        assert response.json["pagination"]["total_count"] == 1
        return response.json["data"][0]

    assert report()["converted_amount"] == 500
    with Session(engine) as session:
        TripManager(session).delete_trip(owner, trip_id)
        session.commit()

    private = report()
    assert private["converted_amount"] == 500 and private["budget_category"] == "伙食"
    assert private["date"] == "2026-10-01"
    assert private["can_edit"] is False and private["can_delete"] is False
    assert private.get("trip_id") is None and private["is_trip_share"] is True
    for secret in ("Shared private note", "Shared private merchant", "Dinner", str(owner), str(source), str(trip_id)):
        assert secret not in json.dumps(private)
    assert client.get(f"/api/transactions/{source}", headers=headers).status_code == 404
    shared = client.get("/api/transactions?include_trips=true", headers=headers)
    assert shared.status_code == 200 and not shared.json["data"]

    with Session(engine) as session:
        manager = TripManager(session)
        with pytest.raises(ValueError):
            manager.restore_trip(member, trip_id)
        restored = manager.restore_trip(owner, trip_id)
        repeated = manager.restore_trip(owner, trip_id)
        assert restored["id"] == repeated["id"] == trip_id
        assert restored["status"] == ("archived" if archived else "active")
        assert BudgetManager(session).calculate_monthly_report_expenses(member, "2026-10")["伙食"] == Decimal("500")
        assert [session.execute(select(t).order_by(t.c.id)).all() for t in tables] == snapshot
        session.commit()
    assert report()["converted_amount"] == 500
    assert client.get(f"/api/transactions/{source}", headers=headers).status_code == 200


def test_deleted_trip_report_cursor_uses_private_identity(command_db, monkeypatch):
    engine, data = command_db
    owner, member, trip_id = data["a"], data["b"], data["trip"]
    with Session(engine) as session:
        trips = TripManager(session)
        trips.update_current_member_monthly_report_preference(member, trip_id, "include")
        BudgetManager(session).add_transaction(member, "2026-10-01", "Personal expense", 20, "expense", "交通")
        trips.delete_trip(owner, trip_id)
        session.commit()
        shared_id = session.scalar(select(transactions_table.c.id).where(transactions_table.c.trip_id == trip_id))
    client, headers = api_client(monkeypatch, engine, {**data, "a": member})
    path = "/api/transactions?monthly_report=true&month=2026-10&limit=1"
    first = client.get(path, headers=headers).json
    second = client.get(path + "&cursor=" + first["pagination"]["next_cursor"], headers=headers).json
    assert {first["data"][0]["converted_amount"], second["data"][0]["converted_amount"]} == {20, 500}

    # Fetch a cursor on a private row, with at least one older item following it.
    with Session(engine) as session:
        BudgetManager(session).add_transaction(member, "2026-09-30", "Older expense", 5, "expense", "交通")
        session.commit()
    path = "/api/transactions?monthly_report=true&limit=1"
    first = client.get(path, headers=headers).json
    second = client.get(path + "&cursor=" + first["pagination"]["next_cursor"], headers=headers).json
    private = second if second["data"][0]["converted_amount"] == 500 else first
    cursor = private["pagination"]["next_cursor"]
    decoded = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
    assert decoded["id"] == private["data"][0]["id"]
    assert decoded["id"] != str(shared_id)
    assert decoded["created_at"] == "1970-01-01T00:00:00+00:00"
