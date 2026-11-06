from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from queue import Queue
from time import monotonic, sleep
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.schema import (
    account_movements_table, accounts_table, financial_commands_table,
    transaction_splits_table, transactions_table,
)
from models.trip_manager import TripManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def snapshot(session):
    return [session.execute(select(table).order_by(*table.primary_key.columns)).all()
            for table in (accounts_table, transactions_table, transaction_splits_table, account_movements_table, financial_commands_table)]


@pytest.mark.parametrize("operation", ["create", "edit"])
@pytest.mark.parametrize("first", ["write", "delete"])
def test_trip_delete_and_transaction_write_follow_commit_order(command_db, operation, first):
    engine, data = command_db
    owner, trip = data["a"], data["trip"]
    with Session(engine) as session:
        before = snapshot(session)
        source_id = session.scalar(select(transactions_table.c.id).where(transactions_table.c.trip_id == trip))

    def apply_write(session):
        manager = BudgetManager(session)
        body = dict(date="2026-10-02", item="Concurrent trip write", amount=125,
                    transaction_type="expense", budget_category="伙食", account_id=data["cash"],
                    paid_by_member_id=data["am"], split_member_ids=[data["am"]])
        if operation == "create":
            manager.add_transaction(owner, trip_id=trip, client_request_id=uuid4(), **body)
        else:
            manager.update_transaction(owner, source_id, **body)

    def delete(session):
        TripManager(session).delete_trip(owner, trip)

    first_action, second_action = (apply_write, delete) if first == "write" else (delete, apply_write)
    worker_pid = Queue()

    def compete():
        with Session(engine) as session:
            session.execute(text("SET LOCAL lock_timeout = '10s'"))
            worker_pid.put(session.scalar(text("SELECT pg_backend_pid()")))
            try:
                second_action(session)
            except ValueError as error:
                session.rollback()
                return str(error)
            session.commit()
            return None

    with ThreadPoolExecutor(max_workers=1) as pool, Session(engine) as holder:
        holder_pid = holder.scalar(text("SELECT pg_backend_pid()"))
        first_action(holder)
        pending = pool.submit(compete)
        blocked = False
        try:
            pid = worker_pid.get(timeout=5)
            deadline = monotonic() + 5
            with engine.connect() as observer:
                while not pending.done() and monotonic() < deadline:
                    blockers = observer.scalar(text("SELECT pg_blocking_pids(:pid)"), {"pid": pid})
                    if holder_pid in blockers:
                        blocked = True
                        break
                    sleep(0.02)
        finally:
            holder.commit()
        rejected = pending.result(timeout=10)

    with Session(engine) as session:
        if first == "delete":
            assert snapshot(session) == before, "A deleted trip must not leave any late ledger write"
            assert rejected == "找不到旅行或權限不足"
        else:
            assert rejected is None
            balance = session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data["cash"]))
            assert balance == Decimal("875")
            assert session.execute(select(account_movements_table.c.amount_delta)).scalars().all() == [Decimal("-125")]
        assert blocked, "Competing requests must serialize on the trip"
        with pytest.raises(ValueError, match="找不到旅行"):
            TripManager(session).get_trip(owner, trip)
