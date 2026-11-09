"""Beta measurement: product events API and the unchanged-draft flag."""
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import scoped_session, sessionmaker

from models.ai_parse_event_manager import AIParseEventManager
from models.schema import product_events_table
from models.user_manager import UserManager
from tests.test_ai_parse_api import _load_web_app
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def test_draft_unchanged_compares_only_fields_the_parser_filled():
    payload = {"transaction": {"amount": "120", "budget_category": "伙食", "title": "午餐", "date": None}}
    same = {"amount": 120, "budget_category": "伙食", "item": "午餐", "date": "2026-11-10"}
    assert AIParseEventManager.draft_unchanged(payload, same) is True
    assert AIParseEventManager.draft_unchanged(payload, {**same, "amount": 130}) is False
    assert AIParseEventManager.draft_unchanged(payload, {**same, "item": "晚餐"}) is False
    assert AIParseEventManager.draft_unchanged({"transaction": {}}, same) is False
    assert AIParseEventManager.draft_unchanged(None, same) is False


@pytest.fixture
def client(command_db, monkeypatch):
    engine, _ = command_db
    app = _load_web_app(monkeypatch)
    db = scoped_session(sessionmaker(bind=engine))
    monkeypatch.setattr(app, "db_session", db)
    monkeypatch.setattr(app, "user_manager", UserManager(db))
    monkeypatch.setattr(app, "DEV_AUTH_BYPASS", True)
    test_client = app.app.test_client()

    def post(body):
        return test_client.post("/api/events", json=body, base_url="http://localhost",
                                environ_base={"REMOTE_ADDR": "127.0.0.1"})
    yield post, engine, app
    db.remove()


def _count(engine):
    with engine.connect() as conn:
        return conn.scalar(select(func.count()).select_from(product_events_table))


def test_allowlisted_event_is_stored(client):
    post, engine, _ = client
    assert post({"name": "home_click", "props": {"target": "trip"}}).status_code == 204
    assert _count(engine) == 1


@pytest.mark.parametrize("body", [
    {"name": "anything"},
    {"name": "home_click", "props": {"text": "x" * 41}},
    {"name": "home_click", "props": {"nested": {"a": 1}}},
    {"name": "home_click", "props": {f"k{i}": "v" for i in range(6)}},
    ["not", "an", "object"],
])
def test_unknown_names_and_free_text_are_rejected(client, body):
    post, engine, _ = client
    assert post(body).status_code == 400
    assert _count(engine) == 0


def test_daily_cap_silently_drops_extra_events(client, monkeypatch):
    post, engine, app = client
    monkeypatch.setattr(app, "PRODUCT_EVENTS_PER_DAY", 2)
    for _ in range(3):
        assert post({"name": "home_view"}).status_code == 204
    assert _count(engine) == 2
