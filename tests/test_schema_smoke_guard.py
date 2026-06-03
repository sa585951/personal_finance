import pytest

from tests.test_schema_smoke import _get_test_database_url


def test_schema_smoke_requires_explicit_test_database_url(monkeypatch):
    monkeypatch.setenv("RUN_DB_SMOKE_TESTS", "1")
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://personal_finance:personal_finance@localhost:5433/personal_finance",
    )

    with pytest.raises(pytest.skip.Exception):
        _get_test_database_url()


def test_schema_smoke_rejects_non_test_database_name(monkeypatch):
    monkeypatch.setenv("RUN_DB_SMOKE_TESTS", "1")
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql://personal_finance:personal_finance@localhost:5433/personal_finance",
    )

    with pytest.raises(pytest.fail.Exception):
        _get_test_database_url()


def test_schema_smoke_accepts_local_test_database(monkeypatch):
    monkeypatch.setenv("RUN_DB_SMOKE_TESTS", "1")
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql://personal_finance:personal_finance@localhost:5433/personal_finance_test",
    )

    assert (
        _get_test_database_url()
        == "postgresql://personal_finance:personal_finance@localhost:5433/personal_finance_test"
    )
