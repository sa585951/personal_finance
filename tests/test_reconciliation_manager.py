from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import create_engine, insert, select, update

from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.reconciliation_manager import ReconciliationManager
from models.schema import (
    account_movements_table,
    accounts_table,
    metadata,
    transfers_table,
)
from models.seed_data import seed_reference_data
from models.user_manager import UserManager
from tests.test_schema_smoke import _get_test_database_url


def test_reconciliation_replays_transaction_transfer_and_adjustment_movements():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        metadata.drop_all(connection)
        metadata.create_all(connection)
        seed_reference_data(connection)

        user = UserManager(connection).get_or_create_user_for_identity(
            provider="line",
            provider_user_id="U-reconciliation",
            display_name="Reconciliation User",
        )
        user_id = user["id"]
        assets = AssetManager(connection)
        assets.add_account(user_id, "來源帳戶", "bank", Decimal("1000"), currency="TWD")
        assets.add_account(user_id, "目標帳戶", "bank", Decimal("500"), currency="TWD")
        source_id = UUID(assets.find_asset_by_name(user_id, "來源帳戶")["id"])
        target_id = UUID(assets.find_asset_by_name(user_id, "目標帳戶")["id"])

        budgets = BudgetManager(connection)
        budgets.add_transaction(
            user_id,
            date="2026-08-21",
            item="午餐",
            amount=Decimal("100"),
            transaction_type="expense",
            budget_category="伙食",
            account_id=source_id,
        )
        transaction_id = budgets.last_created_transaction_id
        budgets.update_transaction(
            user_id,
            transaction_id,
            date="2026-08-21",
            item="午餐",
            amount=Decimal("120"),
            transaction_type="expense",
            budget_category="伙食",
            account_id=source_id,
        )
        budgets.delete_transaction(user_id, transaction_id)

        assets.transfer(user_id, source_id, target_id, Decimal("200"), note="配置")
        transfer_id = connection.execute(select(transfers_table.c.id)).scalar_one()
        assets.update_transfer(
            user_id,
            transfer_id,
            source_id,
            target_id,
            Decimal("150"),
            note="配置更新",
        )
        assets.delete_transfer(user_id, transfer_id)

        assets.create_balance_adjustment(
            user_id,
            source_id,
            Decimal("950"),
            reason="statement_reconciliation",
            note="測試對帳",
        )

        report = ReconciliationManager(connection).reconcile(user_id=user_id)
        by_id = {account["account_id"]: account for account in report["accounts"]}

        assert report["summary"] == {
            "total": 2,
            "matched": 2,
            "mismatched": 0,
            "missing_anchor": 0,
        }
        assert by_id[str(source_id)]["expected_balance"] == Decimal("950.0000")
        assert by_id[str(source_id)]["stored_balance"] == Decimal("950.0000")
        assert by_id[str(source_id)]["movements"]["transaction"]["amount_delta"] == Decimal("0")
        assert by_id[str(source_id)]["movements"]["transfer"]["amount_delta"] == Decimal("0")
        assert by_id[str(source_id)]["movements"]["adjustment"]["amount_delta"] == Decimal("-50.0000")
        assert by_id[str(target_id)]["expected_balance"] == Decimal("500.0000")

        operations = connection.execute(
            select(
                account_movements_table.c.source_type,
                account_movements_table.c.operation,
                account_movements_table.c.amount_delta,
                account_movements_table.c.balance_before,
                account_movements_table.c.balance_after,
            ).order_by(account_movements_table.c.created_at, account_movements_table.c.id)
        ).all()
        assert len(operations) == 12
        assert {row.operation for row in operations} == {
            "create",
            "update_reversal",
            "update_apply",
            "delete_reversal",
        }
        assert all(row.balance_after == row.balance_before + row.amount_delta for row in operations)

        connection.execute(
            update(accounts_table)
            .where(accounts_table.c.id == target_id)
            .values(balance=Decimal("501"))
        )
        mismatch = ReconciliationManager(connection).reconcile(account_id=target_id)["accounts"][0]
        assert mismatch["status"] == "mismatch"
        assert mismatch["difference"] == Decimal("-1.0000")


def test_reconciliation_reports_missing_anchor_without_guessing():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        metadata.drop_all(connection)
        metadata.create_all(connection)
        seed_reference_data(connection)
        user = UserManager(connection).get_or_create_user_for_identity(
            provider="line",
            provider_user_id="U-no-anchor",
            display_name="No Anchor",
        )
        account_id = connection.execute(
            insert(accounts_table)
            .values(
                user_id=user["id"],
                name="Legacy account",
                type="bank",
                currency="TWD",
                track_balance=True,
                balance=Decimal("100"),
            )
            .returning(accounts_table.c.id)
        ).scalar_one()

        report = ReconciliationManager(connection).reconcile(account_id=account_id)
        account = report["accounts"][0]

        assert account["status"] == "missing_anchor"
        assert account["expected_balance"] is None
        assert account["difference"] is None
        assert report["summary"]["missing_anchor"] == 1
