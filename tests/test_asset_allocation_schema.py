import os
import uuid
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from models.schema import (
    accounts_table,
    holding_cost_entries_table,
    holdings_table,
    metadata,
    portfolio_snapshot_items_table,
    portfolio_snapshots_table,
    portfolios_table,
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

    parsed_url = urlparse(database_url)
    database_name = parsed_url.path.lstrip("/")
    if not database_name.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point to a database ending with '_test'")

    host = parsed_url.hostname
    if host not in {"localhost", "127.0.0.1"} and os.getenv("ALLOW_NON_LOCAL_DB_TESTS") != "1":
        pytest.skip("DB smoke tests only run against localhost by default")

    return database_url


def _assert_integrity_error(connection, statement):
    savepoint = connection.begin_nested()
    try:
        with pytest.raises(IntegrityError):
            connection.execute(statement)
    finally:
        savepoint.rollback()


def test_asset_allocation_schema_records_and_constraints():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        metadata.drop_all(connection)
        metadata.create_all(connection)
        seed_reference_data(connection)

        user = UserManager(connection).get_or_create_user_for_identity(
            provider="line",
            provider_user_id="U-allocation-schema-user",
            display_name="Allocation Test User",
        )
        user_id = user["id"]
        source_account_id = uuid.uuid4()
        investment_account_id = uuid.uuid4()

        connection.execute(
            accounts_table.insert(),
            [
                {
                    "id": source_account_id,
                    "user_id": user_id,
                    "name": "薪轉帳戶",
                    "type": "bank",
                    "currency": "TWD",
                    "track_balance": True,
                    "balance": Decimal("100000"),
                },
                {
                    "id": investment_account_id,
                    "user_id": user_id,
                    "name": "投資帳戶",
                    "type": "investment",
                    "currency": "TWD",
                    "track_balance": True,
                    "balance": Decimal("20000"),
                },
            ],
        )

        portfolio_id = connection.execute(
            portfolios_table.insert()
            .values(
                user_id=user_id,
                name="長期 ETF",
                base_currency="TWD",
            )
            .returning(portfolios_table.c.id)
        ).scalar_one()

        holding_ids = connection.execute(
            holdings_table.insert()
            .values(
                [
                    {
                        "portfolio_id": portfolio_id,
                        "account_id": investment_account_id,
                        "name": "元大台灣 50",
                        "symbol": "0050",
                        "asset_class": "ETF",
                        "target_weight": Decimal("0.80000000"),
                    },
                    {
                        "portfolio_id": portfolio_id,
                        "account_id": investment_account_id,
                        "name": "元大台灣 50 正 2",
                        "symbol": "00631L",
                        "asset_class": "ETF",
                        "target_weight": Decimal("0.20000000"),
                    },
                ]
            )
            .returning(holdings_table.c.id)
        ).scalars().all()

        transfer_id = connection.execute(
            transfers_table.insert()
            .values(
                user_id=user_id,
                source_account_id=source_account_id,
                target_account_id=investment_account_id,
                source_amount=Decimal("20000"),
                source_currency="TWD",
                target_amount=Decimal("20000"),
                target_currency="TWD",
                target_per_source_rate=Decimal("1"),
                transfer_date=date(2026, 7, 21),
            )
            .returning(transfers_table.c.id)
        ).scalar_one()

        connection.execute(
            holding_cost_entries_table.insert(),
            [
                {
                    "holding_id": holding_ids[0],
                    "source_transfer_id": transfer_id,
                    "entry_type": "transfer",
                    "amount": Decimal("16000"),
                    "currency": "TWD",
                    "occurred_on": date(2026, 7, 21),
                },
                {
                    "holding_id": holding_ids[1],
                    "source_transfer_id": transfer_id,
                    "entry_type": "transfer",
                    "amount": Decimal("4000"),
                    "currency": "TWD",
                    "occurred_on": date(2026, 7, 21),
                },
            ],
        )

        snapshot_id = connection.execute(
            portfolio_snapshots_table.insert()
            .values(
                portfolio_id=portfolio_id,
                snapshot_date=date(2026, 7, 21),
                currency="TWD",
            )
            .returning(portfolio_snapshots_table.c.id)
        ).scalar_one()
        connection.execute(
            portfolio_snapshot_items_table.insert(),
            [
                {
                    "snapshot_id": snapshot_id,
                    "holding_id": holding_ids[0],
                    "value": Decimal("16500"),
                },
                {
                    "snapshot_id": snapshot_id,
                    "holding_id": holding_ids[1],
                    "value": Decimal("3900"),
                },
            ],
        )

        _assert_integrity_error(
            connection,
            holdings_table.insert().values(
                portfolio_id=portfolio_id,
                account_id=investment_account_id,
                name="超出比例",
                target_weight=Decimal("1.00000001"),
            ),
        )
        _assert_integrity_error(
            connection,
            holding_cost_entries_table.insert().values(
                holding_id=holding_ids[0],
                entry_type="manual_adjustment",
                amount=Decimal("0"),
                currency="TWD",
                occurred_on=date(2026, 7, 21),
            ),
        )
        _assert_integrity_error(
            connection,
            holding_cost_entries_table.insert().values(
                holding_id=holding_ids[0],
                entry_type="transfer",
                amount=Decimal("100"),
                currency="TWD",
                occurred_on=date(2026, 7, 21),
            ),
        )
        _assert_integrity_error(
            connection,
            portfolio_snapshots_table.insert().values(
                portfolio_id=portfolio_id,
                snapshot_date=date(2026, 7, 21),
                currency="TWD",
            ),
        )
        _assert_integrity_error(
            connection,
            portfolio_snapshot_items_table.insert().values(
                snapshot_id=snapshot_id,
                holding_id=holding_ids[0],
                value=Decimal("1"),
            ),
        )
