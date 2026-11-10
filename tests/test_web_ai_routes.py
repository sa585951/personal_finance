"""Web one-sentence bookkeeping: consent, limits and the failure mapping, with a fake provider."""
import uuid

from models.line_ai_gateway import AIRequestBlocked
from tests.test_ai_parse_api import FakeDBSession, FakeLineBotManager, _auth_headers, _load_web_app


class FakeGateway:
    def __init__(self, block=None):
        self.block = block
        self.calls = []

    def status(self, owner):
        return {"enabled": True, "consented": True, "remaining": 17, "daily_limit": 20}

    def generate(self, owner, event_id, prompt):
        self.calls.append((owner, event_id))
        if self.block:
            raise self.block
        return object()


class FakeAIService:
    """Calls the generator the way the real service does for text the rules cannot read."""

    def parse(self, text, *, generate=None):
        if generate:
            generate(f"prompt:{text}")
        return {
            "intent": "create_transaction", "source": "gemini", "raw_text": text,
            "legacy": {"type": "expense"},
            "transaction": {"type": "expense", "title": "午餐", "budget_category": "伙食", "amount": "120",
                            "description": "", "account_hint": None, "currency": None, "date": None,
                            "merchant": None},
            "flow": None, "missing_fields": [], "errors": [],
        }


def _setup(monkeypatch, gateway):
    web_app = _load_web_app(monkeypatch)
    manager = FakeLineBotManager()
    manager.message_parser.ai_parse_service = FakeAIService()
    manager.line_ai_gateway = gateway
    monkeypatch.setattr(web_app, "linebot_manager", manager)
    monkeypatch.setattr(web_app, "db_session", FakeDBSession())
    return web_app.app.test_client()


def _post(client, body):
    return client.post("/api/parse/ai", json=body, headers=_auth_headers())


def test_ai_is_reported_off_when_no_gateway_is_configured(monkeypatch):
    client = _setup(monkeypatch, None)
    status = client.get("/api/ai/status", headers=_auth_headers()).get_json()
    assert status["data"] == {"available": False}
    response = _post(client, {"text": "昨天午餐 120", "client_request_id": str(uuid.uuid4())})
    assert response.status_code == 503 and response.get_json()["code"] == "AI_DISABLED"


def test_status_shows_remaining_requests_and_the_notice(monkeypatch):
    client = _setup(monkeypatch, FakeGateway())
    data = client.get("/api/ai/status", headers=_auth_headers()).get_json()["data"]
    assert data["available"] and data["consented"] and data["remaining"] == 17
    assert "Google Gemini" in data["notice"] and "同意 AI" not in data["notice"]


def test_requires_a_request_id_and_limits_length(monkeypatch):
    gateway = FakeGateway()
    client = _setup(monkeypatch, gateway)
    assert _post(client, {"text": "午餐 120"}).status_code == 400
    long_text = "午餐" + "1" * 250
    response = _post(client, {"text": long_text, "client_request_id": str(uuid.uuid4())})
    assert response.status_code == 400 and response.get_json()["code"] == "AI_TEXT_TOO_LONG"
    assert gateway.calls == []


def test_success_uses_a_web_event_id_and_returns_the_draft(monkeypatch):
    gateway = FakeGateway()
    client = _setup(monkeypatch, gateway)
    request_id = str(uuid.uuid4())
    response = _post(client, {"text": "昨天跟朋友吃午餐 120", "client_request_id": request_id})
    body = response.get_json()
    assert response.status_code == 200 and body["data"]["parse_result"]["transaction"]["amount"] == "120"
    assert gateway.calls == [("22222222-2222-2222-2222-222222222222", f"web:{request_id}")]


def test_blocked_requests_map_to_distinct_statuses(monkeypatch):
    cases = [
        (AIRequestBlocked("line notice", "consent_required"), 409, "AI_CONSENT_REQUIRED"),
        (AIRequestBlocked("用完", "daily_limit"), 429, "AI_DAILY_LIMIT"),
        (AIRequestBlocked("人多", "busy"), 429, "AI_BUSY"),
        (AIRequestBlocked("上限", "budget"), 429, "AI_BUDGET"),
        (AIRequestBlocked("其他"), 422, "AI_BLOCKED"),
    ]
    for blocked, status, code in cases:
        client = _setup(monkeypatch, FakeGateway(block=blocked))
        response = _post(client, {"text": "昨天午餐 120", "client_request_id": str(uuid.uuid4())})
        assert response.status_code == status and response.get_json()["code"] == code
    # The Web never shows LINE's "回覆同意 AI" instructions.
    client = _setup(monkeypatch, FakeGateway(block=cases[0][0]))
    message = _post(client, {"text": "昨天午餐 120", "client_request_id": str(uuid.uuid4())}).get_json()["message"]
    assert "line notice" not in message and "Google Gemini" in message


def test_sensitive_or_non_bookkeeping_text_never_reaches_the_provider(monkeypatch):
    gateway = FakeGateway()
    client = _setup(monkeypatch, gateway)
    for text in ("我的密碼 12345", "你好嗎", "4111 1111 1111 1111 午餐"):
        response = _post(client, {"text": text, "client_request_id": str(uuid.uuid4())})
        assert response.status_code == 422, text
    assert gateway.calls == []


def test_consent_endpoint_validates_and_stores(monkeypatch):
    client = _setup(monkeypatch, FakeGateway())
    stored = []
    import models.line_ai_gateway as module
    monkeypatch.setattr(module, "set_line_ai_consent", lambda session, owner, value: stored.append((str(owner), value)))
    assert client.post("/api/ai/consent", json={"consented": "yes"}, headers=_auth_headers()).status_code == 400
    ok = client.post("/api/ai/consent", json={"consented": True}, headers=_auth_headers())
    assert ok.status_code == 200 and stored == [("22222222-2222-2222-2222-222222222222", True)]
    off = client.post("/api/ai/consent", json={"consented": False}, headers=_auth_headers())
    assert off.status_code == 200 and stored[-1][1] is False
