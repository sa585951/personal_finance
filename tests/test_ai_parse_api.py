import importlib
import sys
import uuid

import jwt


class FakeMessageParser:
    def __init__(self):
        self.last_text = None

    def parse_shared(self, text):
        self.last_text = text
        return {
            "intent": "create_transaction",
            "source": "gemini",
            "raw_text": text,
            "legacy": {"type": "expense", "amount": 100},
            "transaction": {
                "type": "expense",
                "title": "早餐",
                "budget_category": "伙食",
                "amount": "100",
                "description": "早餐",
                "account_hint": None,
                "currency": None,
                "date": None,
                "merchant": None,
            },
            "flow": None,
            "missing_fields": [],
            "errors": [],
        }


class FakeAIParseEventManager:
    def __init__(self):
        self.last_user_id = None
        self.last_source = None
        self.last_parse_result = None
        self.confirmed_event = None
        self.list_request = None

    def record_from_parse_result(self, user_id, source, parse_result):
        self.last_user_id = user_id
        self.last_source = source
        self.last_parse_result = parse_result
        return {"id": uuid.UUID("11111111-1111-1111-1111-111111111111")}

    def confirm_event(self, user_id, event_id, result_type, result_id):
        self.confirmed_event = {
            "user_id": user_id,
            "event_id": event_id,
            "result_type": result_type,
            "result_id": result_id,
        }
        return {"id": uuid.UUID(str(event_id)), "status": "confirmed"}

    def list_recent_events(self, user_id, limit=20):
        self.list_request = {"user_id": user_id, "limit": limit}
        return [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "source": "web",
                "raw_input": "早餐 100",
                "status": "confirmed",
                "result_type": "expense",
                "result_id": "33333333-3333-3333-3333-333333333333",
            }
        ]


class FakeLineBotManager:
    def __init__(self):
        self.message_parser = FakeMessageParser()
        self.ai_parse_event_manager = FakeAIParseEventManager()


class FakeDBSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.removes = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def remove(self):
        self.removes += 1


class FakeBudgetManager:
    def __init__(self):
        self.last_created_transaction_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        self.last_payload = None

    def add_transaction(
        self,
        user_id,
        date,
        item,
        amount,
        transaction_type,
        budget_category,
        description="",
        **kwargs,
    ):
        self.last_payload = {
            "user_id": user_id,
            "date": date,
            "item": item,
            "amount": amount,
            "transaction_type": transaction_type,
            "budget_category": budget_category,
            "description": description,
            **kwargs,
        }
        return True, "交易新增成功"


class FakeAssetManager:
    def __init__(self):
        self.transfer_payload = None
        self.recent_request = None

    def transfer(self, user_id, source_id, dest_id, amount, note=None):
        self.transfer_payload = {
            "user_id": user_id,
            "source_id": source_id,
            "dest_id": dest_id,
            "amount": amount,
            "note": note,
        }
        return True, "轉帳成功"

    def get_recent_transfers(self, user_id, limit=10):
        self.recent_request = {"user_id": user_id, "limit": limit}
        return [
            {
                "id": "transfer-1",
                "source_name": "薪資帳戶",
                "source_type": "bank",
                "target_name": "投資帳戶",
                "target_type": "investment",
                "target_amount": 5000,
                "target_currency": "TWD",
                "transfer_date": "2026-06-11",
                "note": "定期定額",
            }
        ]


def _load_web_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://personal_finance:personal_finance@localhost:5433/personal_finance")
    monkeypatch.setenv("LINE_LOGIN_CHANNEL_ID", "line-login-channel")
    monkeypatch.setenv("LINE_LOGIN_CHANNEL_SECRET", "line-login-secret")
    monkeypatch.setenv("LINE_MSG_CHANNEL_ACCESS_TOKEN", "line-message-token")
    monkeypatch.setenv("LINE_MSG_CHANNEL_SECRET", "line-message-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("VITE_BACKEND_BASE_URL", "http://127.0.0.1:5001")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://127.0.0.1:5174")
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")

    sys.modules.pop("web_app", None)
    return importlib.import_module("web_app")


def _auth_headers():
    token = jwt.encode({"user_id": "22222222-2222-2222-2222-222222222222"}, "test-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_ai_parse_api_rejects_empty_text(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_db_session = FakeDBSession()
    monkeypatch.setattr(web_app, "db_session", fake_db_session)

    response = web_app.app.test_client().post(
        "/api/ai/parse",
        json={"text": "   "},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    assert response.get_json() == {"success": False, "message": "缺少 text 欄位"}
    assert fake_db_session.commits == 0


def test_ai_parse_api_returns_parse_result_and_records_event(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_linebot_manager = FakeLineBotManager()
    fake_db_session = FakeDBSession()
    monkeypatch.setattr(web_app, "linebot_manager", fake_linebot_manager)
    monkeypatch.setattr(web_app, "db_session", fake_db_session)

    response = web_app.app.test_client().post(
        "/api/ai/parse",
        json={"text": "早餐 100"},
        headers=_auth_headers(),
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["parse_event_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["data"]["parse_result"]["transaction"]["amount"] == "100"
    assert fake_linebot_manager.message_parser.last_text == "早餐 100"
    assert fake_linebot_manager.ai_parse_event_manager.last_user_id == "22222222-2222-2222-2222-222222222222"
    assert fake_linebot_manager.ai_parse_event_manager.last_source == "web"
    assert fake_db_session.commits == 1


def test_add_transaction_confirms_parse_event_when_present(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_linebot_manager = FakeLineBotManager()
    fake_budget_manager = FakeBudgetManager()
    fake_db_session = FakeDBSession()
    monkeypatch.setattr(web_app, "linebot_manager", fake_linebot_manager)
    monkeypatch.setattr(web_app, "budget_manager", fake_budget_manager)
    monkeypatch.setattr(web_app, "db_session", fake_db_session)

    response = web_app.app.test_client().post(
        "/api/transactions",
        json={
            "date": "2027-03-01",
            "item": "早餐",
            "amount": 100,
            "type": "expense",
            "budget_category": "伙食",
            "description": "AI 套用",
            "parse_event_id": "11111111-1111-1111-1111-111111111111",
        },
        headers=_auth_headers(),
    )
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["data"]["transaction_id"] == "33333333-3333-3333-3333-333333333333"
    assert fake_linebot_manager.ai_parse_event_manager.confirmed_event == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "event_id": "11111111-1111-1111-1111-111111111111",
        "result_type": "expense",
        "result_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
    }
    assert fake_db_session.commits == 1


def test_ai_parse_events_api_returns_recent_events(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_linebot_manager = FakeLineBotManager()
    monkeypatch.setattr(web_app, "linebot_manager", fake_linebot_manager)

    response = web_app.app.test_client().get(
        "/api/ai/parse-events?limit=5",
        headers=_auth_headers(),
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"][0]["status"] == "confirmed"
    assert fake_linebot_manager.ai_parse_event_manager.list_request == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "limit": "5",
    }


def test_transfer_api_passes_allocation_note(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_asset_manager = FakeAssetManager()
    fake_db_session = FakeDBSession()
    monkeypatch.setattr(web_app, "asset_manager", fake_asset_manager)
    monkeypatch.setattr(web_app, "db_session", fake_db_session)

    response = web_app.app.test_client().post(
        "/api/transfer",
        json={
            "source_id": "salary",
            "dest_id": "investment",
            "amount": 5000,
            "note": "定期定額",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "轉帳成功"
    assert fake_asset_manager.transfer_payload == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "source_id": "salary",
        "dest_id": "investment",
        "amount": 5000,
        "note": "定期定額",
    }
    assert fake_db_session.commits == 1


def test_recent_transfers_api_returns_allocation_history(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_asset_manager = FakeAssetManager()
    monkeypatch.setattr(web_app, "asset_manager", fake_asset_manager)

    response = web_app.app.test_client().get(
        "/api/transfers/recent?limit=8",
        headers=_auth_headers(),
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"][0]["note"] == "定期定額"
    assert fake_asset_manager.recent_request == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "limit": "8",
    }


def test_line_login_start_creates_signed_state_with_safe_redirect(monkeypatch):
    web_app = _load_web_app(monkeypatch)

    response = web_app.app.test_client().get("/line-login-start?redirect=/trips/invite/test-token")
    location = response.headers["Location"]

    assert response.status_code == 302
    assert location.startswith("https://access.line.me/oauth2/v2.1/authorize?")
    assert "client_id=line-login-channel" in location

    from urllib.parse import parse_qs, urlparse

    query = parse_qs(urlparse(location).query)
    redirect_path = web_app._decode_line_login_state(query["state"][0])
    assert redirect_path == "/trips/invite/test-token"


def test_line_login_state_rejects_external_redirect(monkeypatch):
    web_app = _load_web_app(monkeypatch)

    response = web_app.app.test_client().get("/line-login-start?redirect=https://evil.example/phish")
    from urllib.parse import parse_qs, urlparse

    query = parse_qs(urlparse(response.headers["Location"]).query)
    redirect_path = web_app._decode_line_login_state(query["state"][0])
    assert redirect_path == "/"
