"""Operator usage overview: gated by NOMICA_ADMIN_LINE_USER_ID, counts only, no financial content."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import insert, update
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from models.admin_usage import is_admin, usage_overview
from models.budget_manager import BudgetManager
from models.schema import transactions_table, user_identities_table
from models.user_manager import UserManager
from tests.test_ai_parse_api import _load_web_app
from tests.test_financial_command_idempotency import command_db  # noqa: F401

ADMIN_LINE_ID = "U-admin-line-id"


def record(session, user_id, title="Secret lunch", amount=120):
    budget = BudgetManager(session)
    budget.add_transaction(user_id, "2026-10-02", title, amount, "expense", "伙食")
    session.commit()
    return budget.last_created_transaction_id


def link_line(engine, user_id, provider_user_id=ADMIN_LINE_ID):
    with Session(engine) as s:
        s.execute(insert(user_identities_table).values(
            user_id=user_id, provider="line", provider_user_id=provider_user_id))
        s.commit()


def test_admin_is_the_user_whose_line_identity_matches_the_env_value(command_db, monkeypatch):
    engine, data = command_db
    link_line(engine, data["a"])
    with Session(engine) as s:
        monkeypatch.delenv("NOMICA_ADMIN_LINE_USER_ID", raising=False)
        assert is_admin(s, data["a"]) is False  # not configured: nobody is admin
        monkeypatch.setenv("NOMICA_ADMIN_LINE_USER_ID", ADMIN_LINE_ID)
        assert is_admin(s, data["a"]) is True
        assert is_admin(s, data["b"]) is False
        monkeypatch.setenv("NOMICA_ADMIN_LINE_USER_ID", "   ")
        assert is_admin(s, data["a"]) is False


def test_overview_counts_records_and_recent_activity_without_financial_content(command_db):
    engine, data = command_db
    with Session(engine) as s:
        before = next(u for u in usage_overview(s)["users"] if u["name"] == "A")
        old_id = record(s, data["a"], "Old secret")
        record(s, data["a"], "New secret")
        s.execute(update(transactions_table).where(transactions_table.c.id == old_id)
                  .values(created_at=datetime.now(timezone.utc) - timedelta(days=30)))
        deleted_id = record(s, data["a"], "Deleted secret")
        s.execute(update(transactions_table).where(transactions_table.c.id == deleted_id)
                  .values(deleted_at=datetime.now(timezone.utc)))
        s.commit()
        overview = usage_overview(s)

    by_name = {user["name"]: user for user in overview["users"]}
    assert len(by_name) == overview["total_users"] >= 2
    first = by_name["A"]
    # Two kept records added; the soft-deleted one is ignored and the 30-day-old one is not "recent".
    assert first["total_records"] == before["total_records"] + 2
    assert first["recent_records"] == before["recent_records"] + 1
    assert first["last_record_at"] is not None
    assert overview["active_users"] >= 1
    silent = next(user for user in overview["users"] if user["total_records"] == 0)
    assert silent["last_record_at"] is None and silent["recent_records"] == 0
    assert "secret" not in str(overview).lower() and "120" not in str(overview["users"][0].keys())
    assert set(first) == {"name", "joined_at", "last_record_at", "total_records", "recent_records"}


@pytest.fixture
def api(command_db, monkeypatch):
    engine, data = command_db
    app = _load_web_app(monkeypatch)
    db = scoped_session(sessionmaker(bind=engine))
    monkeypatch.setattr(app, "db_session", db)
    monkeypatch.setattr(app, "user_manager", UserManager(db))
    monkeypatch.setattr(app, "DEV_AUTH_BYPASS", True)
    client = app.app.test_client()
    yield client, engine, app
    db.remove()


def get(client, path):
    return client.get(path, base_url="http://localhost", environ_base={"REMOTE_ADDR": "127.0.0.1"})


def test_endpoint_is_404_for_everyone_but_the_operator(api, monkeypatch):
    client, engine, app = api
    monkeypatch.setenv("NOMICA_ADMIN_LINE_USER_ID", ADMIN_LINE_ID)
    assert get(client, "/api/admin/usage").status_code == 404  # the dev user has no LINE identity

    with Session(engine) as s:
        dev_user_id = UserManager(s).get_user_by_identity("dev", "local-dev-user")["id"]
    link_line(engine, dev_user_id)
    response = get(client, "/api/admin/usage")
    assert response.status_code == 200
    assert {"total_users", "active_users", "users", "recent_days"} <= set(response.get_json()["data"])

    monkeypatch.delenv("NOMICA_ADMIN_LINE_USER_ID")
    assert get(client, "/api/admin/usage").status_code == 404
