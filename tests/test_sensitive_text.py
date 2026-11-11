"""The shared filter that keeps card numbers, IDs and secrets out of drafts, parse events and models."""
import pytest

from models.sensitive_text import contains_sensitive
from tests.test_ai_parse_api import FakeDBSession, FakeLineBotManager, _auth_headers, _load_web_app


@pytest.mark.parametrize("text", [
    "午餐 120 卡號 4111 1111 1111 1111",
    "4111-1111-1111-1111 午餐",
    "４１１１　１１１１　１１１１　１１１１",  # full-width digits fold to ASCII first
    "我的密碼是 abc123",
    "驗證碼 123456",
    "安全碼 123",
    "cvv 123",
    "OTP 482913",
    "身分證 A123456789",
    "A123456789",
    "a223456789 午餐 120",
    "轉到 0123456789012 午餐",  # bank-account-length run
    "打給 0912345678",
    "API key sk-abc",
])
def test_sensitive_text_is_caught(text):
    assert contains_sensitive(text), text


@pytest.mark.parametrize("text", [
    "午餐 120",
    "午餐麥當勞 150 用現金",
    "房租 35000 玉山帳戶",
    "旅費 1,200,000",
    "2026-11-10 午餐 120",
    "昨天晚餐 刷卡 450",
    "薪資 50000 存入玉山帳戶",
    "買筆電 98000 刷國泰卡",
    "計程車 280 現金",
    "6/13 火車票 460",
    "",
    None,
])
def test_ordinary_bookkeeping_is_not_blocked(text):
    assert not contains_sensitive(text), text


def _client(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    manager = FakeLineBotManager()
    db = FakeDBSession()
    monkeypatch.setattr(web_app, "linebot_manager", manager)
    monkeypatch.setattr(web_app, "db_session", db)
    return web_app.app.test_client(), manager, db


def test_web_parse_refuses_sensitive_text_before_parsing_or_storing(monkeypatch):
    client, manager, db = _client(monkeypatch)
    for path in ("/api/ai/parse", "/api/parse/local"):
        response = client.post(path, json={"text": "午餐 120 卡號 4111 1111 1111 1111"}, headers=_auth_headers())
        assert response.status_code == 422, path
        body = response.get_json()
        assert body["code"] == "SENSITIVE_TEXT" and "請移除" in body["message"]
    assert manager.message_parser.last_text is None  # never reached the parser
    assert manager.ai_parse_event_manager.last_user_id is None  # nothing was recorded
    assert db.commits == 0


def test_web_parse_still_accepts_an_ordinary_sentence(monkeypatch):
    client, manager, db = _client(monkeypatch)
    response = client.post("/api/ai/parse", json={"text": "早餐 100"}, headers=_auth_headers())
    assert response.status_code == 200 and manager.message_parser.last_text == "早餐 100"
