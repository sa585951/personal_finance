import os
import uuid
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select

from models.asset_allocation_manager import AllocationNotFoundError, AssetAllocationManager
from models.asset_manager import AssetManager
from models.schema import (
    accounts_table,
    metadata,
    portfolio_snapshot_items_table,
    portfolio_snapshots_table,
    transfers_table,
)
from models.seed_data import seed_reference_data
from models.user_manager import UserManager


load_dotenv()


def _get_test_database_url():
    if os.getenv("RUN_DB_SMOKE_TESTS") != "1":
        pytest.skip("Set RUN_DB_SMOKE_TESTS=1 to run DB smoke tests")
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for destructive DB smoke tests")
    parsed = urlparse(database_url)
    if not parsed.path.lstrip("/").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point to a database ending with '_test'")
    if parsed.hostname not in {"localhost", "127.0.0.1"} and os.getenv("ALLOW_NON_LOCAL_DB_TESTS") != "1":
        pytest.skip("DB smoke tests only run against localhost by default")
    return database_url


def _create_account(connection, user_id, name, account_type, currency="TWD", balance="0"):
    account_id = uuid.uuid4()
    connection.execute(
        accounts_table.insert().values(
            id=account_id,
            user_id=user_id,
            name=name,
            type=account_type,
            currency=currency,
            track_balance=True,
            balance=Decimal(balance),
        )
    )
    return account_id


def test_asset_allocation_manager_validates_ownership_costs_snapshots_and_preview():
    engine = create_engine(_get_test_database_url(), future=True)
    with engine.begin() as connection:
        metadata.drop_all(connection)
        metadata.create_all(connection)
        seed_reference_data(connection)

        user_manager = UserManager(connection)
        user = user_manager.get_or_create_user_for_identity(
            "line",
            "U-allocation-manager",
            "Allocation User",
        )
        other_user = user_manager.get_or_create_user_for_identity(
            "line",
            "U-other-allocation-manager",
            "Other User",
        )
        bank_id = _create_account(connection, user["id"], "薪轉", "bank", balance="100000")
        investment_id = _create_account(connection, user["id"], "台股投資", "investment")
        usd_investment_id = _create_account(
            connection,
            user["id"],
            "美股投資",
            "investment",
            currency="USD",
        )
        other_investment_id = _create_account(
            connection,
            other_user["id"],
            "他人投資",
            "investment",
        )

        manager = AssetAllocationManager(connection)
        portfolio = manager.create_portfolio(user["id"], "長期 ETF", "TWD")

        with pytest.raises(ValueError, match="investment"):
            manager.create_holding(user["id"], portfolio["id"], bank_id, "錯誤銀行標的")
        with pytest.raises(ValueError, match="幣別"):
            manager.create_holding(user["id"], portfolio["id"], usd_investment_id, "VOO")
        with pytest.raises(AllocationNotFoundError, match="權限不足"):
            manager.create_holding(user["id"], portfolio["id"], other_investment_id, "他人標的")
        with pytest.raises(AllocationNotFoundError, match="權限不足"):
            manager.get_portfolio(other_user["id"], portfolio["id"])

        holding_0050 = manager.create_holding(
            user["id"],
            portfolio["id"],
            investment_id,
            "元大台灣 50",
            symbol="0050",
            asset_class="ETF",
            target_weight="0.8",
        )
        holding_00631l = manager.create_holding(
            user["id"],
            portfolio["id"],
            investment_id,
            "元大台灣 50 正 2",
            symbol="00631l",
            asset_class="ETF",
            target_weight="0.2",
        )
        assert holding_00631l["symbol"] == "00631L"

        transfer_id = connection.execute(
            transfers_table.insert()
            .values(
                user_id=user["id"],
                source_account_id=bank_id,
                target_account_id=investment_id,
                source_amount=Decimal("20000"),
                source_currency="TWD",
                target_amount=Decimal("20000"),
                target_currency="TWD",
                target_per_source_rate=Decimal("1"),
                transfer_date=date(2026, 7, 21),
            )
            .returning(transfers_table.c.id)
        ).scalar_one()

        cost_0050 = manager.create_cost_entry(
            user["id"],
            holding_0050["id"],
            "transfer",
            "16000",
            "2026-07-21",
            source_transfer_id=transfer_id,
        )
        manager.create_cost_entry(
            user["id"],
            holding_00631l["id"],
            "transfer",
            "4000",
            "2026-07-21",
            source_transfer_id=transfer_id,
        )
        with pytest.raises(ValueError, match="不可超過"):
            manager.update_cost_entry(
                user["id"],
                cost_0050["id"],
                amount="16001",
            )

        asset_manager = AssetManager(connection)
        with pytest.raises(ValueError, match="已分配到投資標的"):
            asset_manager.update_transfer(
                user["id"],
                transfer_id,
                bank_id,
                investment_id,
                "20000",
            )
        with pytest.raises(ValueError, match="已分配到投資標的"):
            asset_manager.delete_transfer(user["id"], transfer_id)

        cost_preview = manager.allocation_preview(user["id"], portfolio["id"], "10000")
        assert cost_preview["basis"] == "recorded_cost"
        assert cost_preview["as_of"] is None

        with pytest.raises(ValueError, match="不可變更所屬帳戶"):
            manager.update_holding(
                user["id"],
                holding_0050["id"],
                account_id=_create_account(
                    connection,
                    user["id"],
                    "第二投資帳戶",
                    "investment",
                ),
            )

        with pytest.raises(ValueError, match="所有 active Holding"):
            manager.create_or_update_snapshot(
                user["id"],
                portfolio["id"],
                "2026-07-21",
                [{"holding_id": holding_0050["id"], "value": "16500"}],
            )

        snapshot = manager.create_or_update_snapshot(
            user["id"],
            portfolio["id"],
            "2026-07-21",
            [
                {"holding_id": holding_0050["id"], "value": "16500"},
                {"holding_id": holding_00631l["id"], "value": "3900"},
            ],
        )
        assert snapshot["total_value"] == 20400.0
        updated_snapshot = manager.create_or_update_snapshot(
            user["id"],
            portfolio["id"],
            "2026-07-21",
            [
                {"holding_id": holding_0050["id"], "value": "17000"},
                {"holding_id": holding_00631l["id"], "value": "4000"},
            ],
            note="月底更新",
        )
        assert updated_snapshot["id"] == snapshot["id"]
        assert updated_snapshot["total_value"] == 21000.0
        assert connection.execute(select(func.count()).select_from(portfolio_snapshots_table)).scalar_one() == 1
        assert connection.execute(select(func.count()).select_from(portfolio_snapshot_items_table)).scalar_one() == 2

        preview = manager.allocation_preview(user["id"], portfolio["id"], "10000")
        assert preview["basis"] == "snapshot"
        assert preview["as_of"] == "2026-07-21"
        assert sum(item["recommended_amount"] for item in preview["allocations"]) == 10000.0
        assert all(item["recommended_amount"] >= 0 for item in preview["allocations"])

        detail = manager.get_portfolio(user["id"], portfolio["id"])
        assert len(detail["holdings"]) == 2
        assert sum(item["recorded_cost"] for item in detail["holdings"]) == 20000.0

        manager.delete_holding(user["id"], holding_0050["id"])
        archived_detail = manager.get_portfolio(user["id"], portfolio["id"])
        archived_holding = next(
            item for item in archived_detail["holdings"] if item["id"] == holding_0050["id"]
        )
        assert archived_holding["is_active"] is False
        assert archived_holding["archived_at"] is not None
