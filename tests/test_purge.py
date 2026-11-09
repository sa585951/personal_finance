"""30-day permanent removal for deleted accounts, against PostgreSQL."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from models.account_privacy import DELETE_CONFIRMATION, DELETED_NAME, AccountPrivacyService
from models.asset_allocation_manager import AssetAllocationManager
from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.purge import DELETED_ACCOUNT_NAME, PurgeService
from models.schema import (
    accounts_table, ai_parse_events_table, portfolios_table, transactions_table, trip_members_table, users_table,
)
from models.user_manager import UserManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401

LATER = datetime.now(timezone.utc) + timedelta(days=31)


def count(session, table, *where):
    return session.scalar(select(func.count()).select_from(table).where(*where))


def test_nothing_is_purged_inside_the_30_day_window(command_db):
    engine, data = command_db
    with Session(engine) as s:
        AccountPrivacyService(s).delete_account(data["b"], DELETE_CONFIRMATION)
        s.commit()
        assert PurgeService(s).run()["deleted"] == {}
        assert count(s, accounts_table, accounts_table.c.user_id == data["b"]) == 1


def test_solo_user_is_removed_completely_and_rerun_is_a_no_op(command_db):
    engine, _ = command_db
    with Session(engine) as s:
        solo = UserManager(s).get_or_create_user_for_identity("qa", "purge-solo", "Solo")["id"]
        assets = AssetManager(s)
        assets.add_account(solo, "Solo cash", "cash", 100)
        cash = next(iter(assets.get_all_assets(solo).values()))["id"]
        BudgetManager(s).add_transaction(solo, "2026-10-01", "Lunch", 30, "expense", "伙食", account_id=cash)
        AssetAllocationManager(s).create_portfolio(solo, "Solo plan", "TWD")
        AccountPrivacyService(s).delete_account(solo, DELETE_CONFIRMATION)
        s.commit()

        result = PurgeService(s).run(now=LATER)
        s.commit()
        assert result["deleted"]["users"] == 1
        for table in (accounts_table, transactions_table, portfolios_table, ai_parse_events_table):
            assert count(s, table, table.c.user_id == solo) == 0
        assert count(s, users_table, users_table.c.id == solo) == 0
        assert PurgeService(s).run(now=LATER)["deleted"] == {}


def test_shared_trip_records_stay_for_other_members(command_db):
    engine, data = command_db
    with Session(engine) as s:
        # B pays a shared-trip expense from B's own account, then deletes the account.
        BudgetManager(s).add_transaction(
            data["b"], "2026-10-02", "Taxi", 200, "expense", "交通", trip_id=data["trip"],
            account_id=data["b_cash"], paid_by_member_id=data["bm"], split_member_ids=[data["am"], data["bm"]])
        AccountPrivacyService(s).delete_account(data["b"], DELETE_CONFIRMATION)
        s.commit()
        trip_rows_before = count(s, transactions_table, transactions_table.c.trip_id == data["trip"])

        PurgeService(s).run(now=LATER)
        s.commit()
        # Every shared-trip expense, including the one B paid, is still there for A.
        assert count(s, transactions_table, transactions_table.c.trip_id == data["trip"]) == trip_rows_before
        # B's account is referenced by that expense, so it stays but loses its name.
        assert s.scalar(select(accounts_table.c.name).where(accounts_table.c.id == data["b_cash"])) == DELETED_ACCOUNT_NAME
        assert s.scalar(select(trip_members_table.c.display_name).where(
            trip_members_table.c.id == data["bm"])) == DELETED_NAME
        # A is untouched.
        assert count(s, accounts_table, accounts_table.c.user_id == data["a"], accounts_table.c.deleted_at.is_(None)) == 2


def test_active_users_soft_deleted_rows_are_not_purged(command_db):
    engine, data = command_db
    with Session(engine) as s:
        s.execute(update(transactions_table).where(transactions_table.c.user_id == data["a"]).values(
            deleted_at=datetime.now(timezone.utc) - timedelta(days=60),
            purge_after=datetime.now(timezone.utc) - timedelta(days=30)))
        s.commit()
        assert PurgeService(s).run(now=LATER)["deleted"] == {}
        assert count(s, transactions_table, transactions_table.c.user_id == data["a"]) >= 1
