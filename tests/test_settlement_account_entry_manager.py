import uuid
from decimal import Decimal

from sqlalchemy import create_engine, insert, select

from models.budget_manager import BudgetManager
from models.asset_manager import AssetManager
from models.schema import (
    accounts_table,
    metadata,
    settlement_account_entries_table,
    settlements_table,
    transactions_table,
    trip_members_table,
)
from models.seed_data import seed_reference_data
from models.settlement_account_entry_manager import SettlementAccountEntryManager
from models.trip_manager import TripManager
from models.user_manager import UserManager
from tests.test_schema_smoke import _get_test_database_url


def _create_user(connection, provider_user_id, display_name):
    return UserManager(connection).get_or_create_user_for_identity(
        provider="line",
        provider_user_id=provider_user_id,
        display_name=display_name,
        provider_email=f"{provider_user_id}@example.test",
    )


def _create_account(connection, user_id, name, currency, balance):
    return connection.execute(
        insert(accounts_table)
        .values(
            user_id=user_id,
            name=name,
            type="bank",
            currency=currency,
            track_balance=True,
            balance=Decimal(str(balance)),
        )
        .returning(accounts_table.c.id)
    ).scalar_one()


def _balance(connection, account_id):
    return connection.execute(
        select(accounts_table.c.balance).where(accounts_table.c.id == account_id)
    ).scalar_one()


def test_settlement_account_entries_post_replay_reverse_and_protect_group_truth():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        metadata.drop_all(connection)
        metadata.create_all(connection)
        seed_reference_data(connection)

        payer = _create_user(connection, "U-settlement-payer", "付款者")
        recipient = _create_user(connection, "U-settlement-recipient", "收款者")
        payer_id = payer["id"]
        recipient_id = recipient["id"]

        trip_manager = TripManager(connection)
        trip = trip_manager.create_trip(
            user_id=payer_id,
            name="Settlement ownership test",
            destination="Taipei",
            start_date="2026-08-01",
            end_date="2026-08-02",
            timezone_name="Asia/Taipei",
            base_currency="TWD",
            default_currency="TWD",
            include_in_monthly_report=False,
        )
        payer_member = next(member for member in trip["members"] if member["user_id"] == str(payer_id))
        recipient_member_id = connection.execute(
            insert(trip_members_table)
            .values(
                trip_id=uuid.UUID(trip["id"]),
                user_id=recipient_id,
                display_name="收款者",
                role="editor",
                status="active",
                monthly_report_preference="pending",
            )
            .returning(trip_members_table.c.id)
        ).scalar_one()

        payer_account_id = _create_account(connection, payer_id, "付款帳戶", "TWD", 1000)
        recipient_account_id = _create_account(connection, recipient_id, "收款帳戶", "TWD", 500)
        wrong_currency_account_id = _create_account(connection, payer_id, "日幣帳戶", "JPY", 10000)
        settlement_id = connection.execute(
            insert(settlements_table)
            .values(
                trip_id=uuid.UUID(trip["id"]),
                from_member_id=uuid.UUID(payer_member["id"]),
                to_member_id=recipient_member_id,
                recorded_by_user_id=payer_id,
                amount=Decimal("200"),
                currency="TWD",
                status="confirmed",
            )
            .returning(settlements_table.c.id)
        ).scalar_one()

        manager = SettlementAccountEntryManager(connection)
        transaction_count_before = connection.execute(select(transactions_table.c.id)).all()

        try:
            manager.create_entry(payer_id, trip["id"], settlement_id, recipient_account_id)
            assert False, "使用者不應能選擇其他人的帳戶"
        except ValueError as exc:
            assert "權限不足" in str(exc)

        try:
            manager.create_entry(payer_id, trip["id"], settlement_id, wrong_currency_account_id)
            assert False, "結算幣別不一致時不應入帳"
        except ValueError as exc:
            assert "幣別" in str(exc)

        payer_entry = manager.create_entry(payer_id, trip["id"], settlement_id, payer_account_id)
        assert payer_entry["direction"] == "outgoing"
        assert payer_entry["replayed"] is False
        assert _balance(connection, payer_account_id) == Decimal("800.0000")

        replayed = manager.create_entry(payer_id, trip["id"], settlement_id, payer_account_id)
        assert replayed["replayed"] is True
        assert replayed["id"] == payer_entry["id"]
        assert _balance(connection, payer_account_id) == Decimal("800.0000")

        recipient_entry = manager.create_entry(
            recipient_id,
            trip["id"],
            settlement_id,
            recipient_account_id,
        )
        assert recipient_entry["direction"] == "incoming"
        assert _balance(connection, recipient_account_id) == Decimal("700.0000")
        assert connection.execute(select(transactions_table.c.id)).all() == transaction_count_before

        settlements_for_payer = BudgetManager(connection).get_trip_settlements(payer_id, trip["id"])
        assert settlements_for_payer[0]["account_entry"]["account_name"] == "付款帳戶"
        assert settlements_for_payer[0]["can_reverse_account"] is True
        assert settlements_for_payer[0]["can_void"] is False

        try:
            BudgetManager(connection).delete_trip_settlement(payer_id, trip["id"], settlement_id)
            assert False, "尚有私人帳戶入帳時不可撤銷群組結算"
        except ValueError as exc:
            assert "取消私人帳戶入帳" in str(exc)

        manager.reverse_entry(recipient_id, trip["id"], settlement_id)
        assert _balance(connection, recipient_account_id) == Decimal("500.0000")
        manager.reverse_entry(payer_id, trip["id"], settlement_id)
        assert _balance(connection, payer_account_id) == Decimal("1000.0000")

        replayed_reversal = manager.reverse_entry(payer_id, trip["id"], settlement_id)
        assert replayed_reversal["replayed"] is True
        assert _balance(connection, payer_account_id) == Decimal("1000.0000")

        settlement_activity = AssetManager(connection).get_account_activity(
            payer_id,
            payer_account_id,
            activity_filter="settlement",
        )
        assert len(settlement_activity["items"]) == 2
        assert settlement_activity["items"][0]["is_reversal"] is True
        assert settlement_activity["items"][0]["amount"] == 200
        assert settlement_activity["items"][1]["is_reversal"] is False
        assert settlement_activity["items"][1]["amount"] == -200

        entries = connection.execute(select(settlement_account_entries_table)).all()
        assert len(entries) == 2
        assert all(entry.status == "reversed" for entry in entries)

        success, message = BudgetManager(connection).delete_trip_settlement(
            payer_id,
            trip["id"],
            settlement_id,
        )
        assert success is True
        assert message == "結算已撤銷"
