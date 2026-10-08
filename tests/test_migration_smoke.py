import os
from pathlib import Path
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from models.schema import metadata


def _get_test_database_url():
    if os.getenv("RUN_DB_SMOKE_TESTS") != "1":
        pytest.skip("Set RUN_DB_SMOKE_TESTS=1 to run DB migration smoke tests")

    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for destructive DB migration smoke tests")

    parsed_url = urlparse(database_url)
    database_name = parsed_url.path.lstrip("/")
    if not database_name.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point to a database ending with '_test'")
    if parsed_url.hostname not in {"localhost", "127.0.0.1"}:
        pytest.skip("DB migration smoke tests only run against localhost")

    return database_url


def test_alembic_can_upgrade_an_empty_database_to_head(monkeypatch):
    database_url = _get_test_database_url()
    engine = create_engine(database_url, future=True)

    # Safety: this test only accepts a local database whose name ends in _test.
    with engine.begin() as connection:
        metadata.drop_all(connection)
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    engine.dispose()

    monkeypatch.setenv("DATABASE_URL", database_url)
    project_root = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(project_root / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    verification_engine = create_engine(database_url, future=True)
    with verification_engine.connect() as connection:
        inspector = inspect(connection)
        account_columns = {column["name"] for column in inspector.get_columns("accounts")}
        account_checks = {
            constraint.get("name") for constraint in inspector.get_check_constraints("accounts")
        }
        table_names = set(inspector.get_table_names())
        billing_indexes = {
            index["name"] for index in inspector.get_indexes("credit_card_billing_profiles")
        }
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    verification_engine.dispose()

    assert revision == "20261008_0016"
    assert "receipt_documents" in table_names
    assert {"icon_key", "color_key"}.issubset(account_columns)
    assert {"ck_accounts_icon_key", "ck_accounts_color_key"}.issubset(account_checks)
    assert "credit_card_billing_profiles" in table_names
    assert "ix_credit_card_billing_profiles_user" in billing_indexes

    # Exercise the deployed 0015 -> 0016 path, not only metadata.create_all.
    command.downgrade(alembic_config, "20260925_0015")
    command.upgrade(alembic_config, "head")
    deployed_engine = create_engine(database_url, future=True)
    with deployed_engine.connect() as connection:
        receipt_indexes = {index["name"] for index in inspect(connection).get_indexes("receipt_documents")}
        assert "ix_receipts_user_date" in receipt_indexes
        assert connection.execute(text("SELECT count(*) FROM receipt_documents")).scalar_one() == 0
    deployed_engine.dispose()
