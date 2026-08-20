import importlib
import sys
import uuid
from datetime import datetime, timedelta, timezone

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
        self.last_create_replayed = False
        self.last_payload = None
        self.last_list_request = None

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

    def get_all_transactions(self, user_id, **kwargs):
        self.last_list_request = {"user_id": user_id, **kwargs}
        if kwargs.get("return_pagination"):
            return {
                "items": [{"id": "transaction-1"}],
                "pagination": {
                    "next_cursor": "next-page",
                    "has_more": True,
                    "limit": 10,
                    "total_count": 12,
                },
            }
        return [{"id": "transaction-1"}]


class FakeAssetManager:
    def __init__(self):
        self.transfer_payload = None
        self.recent_request = None
        self.update_payload = None
        self.update_transfer_payload = None
        self.deleted_transfer = None
        self.adjustment_payload = None
        self.adjustment_list_request = None

    def update_account(self, user_id, account_key, **changes):
        self.update_payload = {
            "user_id": user_id,
            "account_key": account_key,
            **changes,
        }
        return True, "帳戶更新成功"

    def transfer(self, user_id, source_id, dest_id, amount, note=None):
        self.transfer_payload = {
            "user_id": user_id,
            "source_id": source_id,
            "dest_id": dest_id,
            "amount": amount,
            "note": note,
        }
        return True, "轉帳成功"

    def update_transfer(self, user_id, transfer_id, source_id, dest_id, amount, note=None):
        self.update_transfer_payload = {
            "user_id": user_id,
            "transfer_id": transfer_id,
            "source_id": source_id,
            "dest_id": dest_id,
            "amount": amount,
            "note": note,
        }
        return True, "轉帳已更新"

    def delete_transfer(self, user_id, transfer_id):
        self.deleted_transfer = {
            "user_id": user_id,
            "transfer_id": transfer_id,
        }
        return True, "轉帳已刪除"

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

    def create_balance_adjustment(
        self,
        user_id,
        account_key,
        new_balance,
        reason,
        note=None,
        client_request_id=None,
    ):
        self.adjustment_payload = {
            "user_id": user_id,
            "account_key": account_key,
            "new_balance": new_balance,
            "reason": reason,
            "note": note,
            "client_request_id": client_request_id,
        }
        return {
            "id": "adjustment-1",
            "account_id": account_key,
            "amount_delta": 500,
            "balance_before": 1000,
            "balance_after": 1500,
            "reason": reason,
            "note": note,
            "adjusted_at": "2026-08-20T12:00:00+00:00",
            "replayed": client_request_id == "44444444-4444-4444-4444-444444444444",
        }

    def get_account_adjustments(self, user_id, account_key, limit=10):
        self.adjustment_list_request = {
            "user_id": user_id,
            "account_key": account_key,
            "limit": limit,
        }
        return [{"id": "adjustment-1", "balance_after": 1500}]


class FakeAuthSessionManager:
    def __init__(self):
        self.revoked_session = None
        self.sessions = {
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa": {
                "id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                "user_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
                "provider": "line",
                "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
                "revoked_at": None,
            }
        }

    def validate_session(self, session_id, user_id):
        session = self.sessions.get(str(session_id))
        if not session or str(session["user_id"]) != str(user_id):
            return None
        if session.get("revoked_at"):
            return None
        if session["expires_at"] <= datetime.now(timezone.utc):
            return None
        return session

    def revoke_session(self, session_id, user_id):
        session = self.sessions.get(str(session_id))
        if not session or str(session["user_id"]) != str(user_id):
            return False
        session["revoked_at"] = datetime.now(timezone.utc)
        self.revoked_session = {"session_id": str(session_id), "user_id": str(user_id)}
        return True

    def list_user_identities(self, user_id):
        return [
            {
                "provider": "line",
                "provider_email": None,
                "provider_display_name": "Test User",
                "created_at": datetime.now(timezone.utc),
            }
        ]

    def create_session(self, user_id, provider, expires_at):
        return {
            "id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            "user_id": uuid.UUID(str(user_id)),
            "provider": provider,
            "expires_at": expires_at,
        }


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
    web_app = importlib.import_module("web_app")
    web_app.auth_session_manager = FakeAuthSessionManager()
    return web_app


def _auth_headers():
    token = _auth_token()
    return {"Authorization": f"Bearer {token}"}


def _auth_token(**overrides):
    payload = {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "session_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "provider": "line",
        "name": "Test User",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    payload.update(overrides)
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_auth_me_accepts_bearer_token(monkeypatch):
    web_app = _load_web_app(monkeypatch)

    response = web_app.app.test_client().get("/api/auth/me", headers=_auth_headers())
    payload = response.get_json()

    assert response.status_code == 200
    assert payload == {
        "success": True,
        "data": {
            "user_id": "22222222-2222-2222-2222-222222222222",
            "name": "Test User",
            "provider": "line",
            "session_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        },
    }


def test_auth_me_accepts_cookie_token(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    client = web_app.app.test_client()
    client.set_cookie(web_app.APP_AUTH_COOKIE_NAME, _auth_token())

    response = client.get("/api/auth/me")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["user_id"] == "22222222-2222-2222-2222-222222222222"


def test_auth_me_rejects_missing_token(monkeypatch):
    web_app = _load_web_app(monkeypatch)

    response = web_app.app.test_client().get("/api/auth/me")

    assert response.status_code == 401
    assert response.get_json() == {"message": "Token is missing!"}


def test_auth_me_rejects_expired_cookie_token(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    client = web_app.app.test_client()
    client.set_cookie(
        web_app.APP_AUTH_COOKIE_NAME,
        _auth_token(exp=datetime.now(timezone.utc) - timedelta(minutes=1)),
    )

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.get_json() == {"message": "Token has expired!"}


def test_auth_me_rejects_token_without_session_id(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    payload = {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "name": "Test User",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    token = jwt.encode(payload, "test-secret", algorithm="HS256")

    response = web_app.app.test_client().get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.get_json() == {"message": "Session is missing!"}


def test_auth_me_rejects_revoked_session(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    web_app.auth_session_manager.sessions["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"][
        "revoked_at"
    ] = datetime.now(timezone.utc)

    response = web_app.app.test_client().get("/api/auth/me", headers=_auth_headers())

    assert response.status_code == 401
    assert response.get_json() == {"message": "Session is invalid!"}


def test_auth_me_rejects_expired_session(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    web_app.auth_session_manager.sessions["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"][
        "expires_at"
    ] = datetime.now(timezone.utc) - timedelta(minutes=1)

    response = web_app.app.test_client().get("/api/auth/me", headers=_auth_headers())

    assert response.status_code == 401
    assert response.get_json() == {"message": "Session is invalid!"}


def test_cookie_auth_rejects_unsafe_request_without_allowed_origin(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    client = web_app.app.test_client()
    client.set_cookie(web_app.APP_AUTH_COOKIE_NAME, _auth_token())

    response = client.post("/api/ai/parse", json={"text": "早餐 100"})

    assert response.status_code == 403
    assert response.get_json() == {"message": "Cookie auth origin is not allowed!"}


def test_cookie_auth_allows_unsafe_request_from_allowed_origin(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    client = web_app.app.test_client()
    client.set_cookie(web_app.APP_AUTH_COOKIE_NAME, _auth_token())

    response = client.post(
        "/api/ai/parse",
        json={"text": "   "},
        headers={"Origin": "http://127.0.0.1:5174"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"success": False, "message": "缺少 text 欄位"}


def test_auth_account_lists_provider_statuses(monkeypatch):
    web_app = _load_web_app(monkeypatch)

    response = web_app.app.test_client().get("/api/auth/account", headers=_auth_headers())
    payload = response.get_json()

    assert response.status_code == 200
    providers = {item["provider"]: item for item in payload["data"]["providers"]}
    assert providers["line"]["status"] == "connected"
    assert providers["line"]["role"] == "快速記帳入口"
    assert providers["apple"]["status"] == "not_enabled"
    assert providers["google"]["status"] == "not_enabled"


def test_logout_clears_auth_cookie(monkeypatch):
    web_app = _load_web_app(monkeypatch)

    response = web_app.app.test_client().post("/api/auth/logout", headers=_auth_headers())
    set_cookie_headers = response.headers.getlist("Set-Cookie")

    assert response.status_code == 200
    assert response.get_json() == {"success": True}
    assert web_app.auth_session_manager.revoked_session == {
        "session_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "user_id": "22222222-2222-2222-2222-222222222222",
    }
    assert any(
        header.startswith(f"{web_app.APP_AUTH_COOKIE_NAME}=;")
        and "HttpOnly" in header
        and "Secure" in header
        and "SameSite=None" in header
        for header in set_cookie_headers
    )


def test_production_auth_cookie_options_are_http_only_secure(monkeypatch):
    web_app = _load_web_app(monkeypatch)

    options = web_app._auth_cookie_options()

    assert options["httponly"] is True
    assert options["secure"] is True
    assert options["samesite"] == "None"
    assert options["path"] == "/"
    assert options["max_age"] == 30 * 24 * 60 * 60


def test_create_app_auth_token_includes_session_id(monkeypatch):
    web_app = _load_web_app(monkeypatch)

    token = web_app._create_app_auth_token(
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
            "display_name": "Test User",
        },
        "line",
    )
    payload = jwt.decode(token, "test-secret", algorithms=["HS256"])

    assert payload["user_id"] == "22222222-2222-2222-2222-222222222222"
    assert payload["session_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert payload["provider"] == "line"


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
    assert payload["replayed"] is False
    assert fake_linebot_manager.ai_parse_event_manager.confirmed_event == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "event_id": "11111111-1111-1111-1111-111111111111",
        "result_type": "expense",
        "result_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
    }
    assert fake_db_session.commits == 1


def test_add_transaction_replay_returns_existing_result_without_reconfirming(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_linebot_manager = FakeLineBotManager()
    fake_budget_manager = FakeBudgetManager()
    fake_budget_manager.last_create_replayed = True
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
            "client_request_id": "44444444-4444-4444-4444-444444444444",
            "parse_event_id": "11111111-1111-1111-1111-111111111111",
        },
        headers=_auth_headers(),
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["replayed"] is True
    assert fake_budget_manager.last_payload["client_request_id"] == (
        "44444444-4444-4444-4444-444444444444"
    )
    assert fake_linebot_manager.ai_parse_event_manager.confirmed_event is None
    assert fake_db_session.commits == 1


def test_get_transactions_returns_pagination_contract(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_budget_manager = FakeBudgetManager()
    monkeypatch.setattr(web_app, "budget_manager", fake_budget_manager)

    response = web_app.app.test_client().get(
        "/api/transactions?type=expense&month=2027-03&limit=10&cursor=page-one",
        headers=_auth_headers(),
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"] == [{"id": "transaction-1"}]
    assert payload["pagination"]["total_count"] == 12
    assert fake_budget_manager.last_list_request["transaction_type"] == "expense"
    assert fake_budget_manager.last_list_request["month"] == "2027-03"
    assert fake_budget_manager.last_list_request["cursor"] == "page-one"
    assert fake_budget_manager.last_list_request["return_pagination"] is True


def test_get_transactions_without_pagination_query_keeps_legacy_shape(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_budget_manager = FakeBudgetManager()
    monkeypatch.setattr(web_app, "budget_manager", fake_budget_manager)

    response = web_app.app.test_client().get("/api/transactions", headers=_auth_headers())
    payload = response.get_json()

    assert response.status_code == 200
    assert payload == {"success": True, "data": [{"id": "transaction-1"}]}
    assert fake_budget_manager.last_list_request["return_pagination"] is False


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


def test_update_asset_api_accepts_account_profile_changes(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_asset_manager = FakeAssetManager()
    fake_db_session = FakeDBSession()
    monkeypatch.setattr(web_app, "asset_manager", fake_asset_manager)
    monkeypatch.setattr(web_app, "db_session", fake_db_session)

    response = web_app.app.test_client().put(
        "/api/assets/account-1",
        json={
            "bank_name": "台新定存",
            "account_type": "bank",
            "currency": "TWD",
            "balance": 30000,
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "帳戶更新成功"
    assert fake_asset_manager.update_payload == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "account_key": "account-1",
        "bank_name": "台新定存",
        "account_type": "bank",
        "currency": "TWD",
        "balance": 30000,
    }
    assert fake_db_session.commits == 1


def test_create_asset_adjustment_api_records_reason_and_commits(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_asset_manager = FakeAssetManager()
    fake_db_session = FakeDBSession()
    monkeypatch.setattr(web_app, "asset_manager", fake_asset_manager)
    monkeypatch.setattr(web_app, "db_session", fake_db_session)

    response = web_app.app.test_client().post(
        "/api/assets/account-1/adjustments",
        json={
            "new_balance": 1500,
            "reason": "statement_reconciliation",
            "note": "依帳單核對",
            "client_request_id": "33333333-3333-3333-3333-333333333333",
        },
        headers=_auth_headers(),
    )
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["success"] is True
    assert payload["replayed"] is False
    assert fake_asset_manager.adjustment_payload == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "account_key": "account-1",
        "new_balance": 1500,
        "reason": "statement_reconciliation",
        "note": "依帳單核對",
        "client_request_id": "33333333-3333-3333-3333-333333333333",
    }
    assert fake_db_session.commits == 1


def test_create_asset_adjustment_api_returns_replayed_result(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_asset_manager = FakeAssetManager()
    fake_db_session = FakeDBSession()
    monkeypatch.setattr(web_app, "asset_manager", fake_asset_manager)
    monkeypatch.setattr(web_app, "db_session", fake_db_session)

    response = web_app.app.test_client().post(
        "/api/assets/account-1/adjustments",
        json={
            "new_balance": 1500,
            "reason": "balance_correction",
            "client_request_id": "44444444-4444-4444-4444-444444444444",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()["replayed"] is True
    assert fake_db_session.commits == 1


def test_get_asset_adjustments_api_is_scoped_to_account(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_asset_manager = FakeAssetManager()
    monkeypatch.setattr(web_app, "asset_manager", fake_asset_manager)

    response = web_app.app.test_client().get(
        "/api/assets/account-1/adjustments?limit=5",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()["data"] == [{"id": "adjustment-1", "balance_after": 1500}]
    assert fake_asset_manager.adjustment_list_request == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "account_key": "account-1",
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


def test_update_transfer_api_passes_payload_and_commits(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_asset_manager = FakeAssetManager()
    fake_db_session = FakeDBSession()
    monkeypatch.setattr(web_app, "asset_manager", fake_asset_manager)
    monkeypatch.setattr(web_app, "db_session", fake_db_session)

    response = web_app.app.test_client().put(
        "/api/transfers/transfer-1",
        json={
            "source_id": "salary",
            "dest_id": "travel",
            "amount": 3000,
            "note": "旅費儲蓄",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "轉帳已更新"
    assert fake_asset_manager.update_transfer_payload == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "transfer_id": "transfer-1",
        "source_id": "salary",
        "dest_id": "travel",
        "amount": 3000,
        "note": "旅費儲蓄",
    }
    assert fake_db_session.commits == 1


def test_delete_transfer_api_soft_deletes_and_commits(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    fake_asset_manager = FakeAssetManager()
    fake_db_session = FakeDBSession()
    monkeypatch.setattr(web_app, "asset_manager", fake_asset_manager)
    monkeypatch.setattr(web_app, "db_session", fake_db_session)

    response = web_app.app.test_client().delete(
        "/api/transfers/transfer-1",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "轉帳已刪除"
    assert fake_asset_manager.deleted_transfer == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "transfer_id": "transfer-1",
    }
    assert fake_db_session.commits == 1


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
    assert query["bot_prompt"] == ["aggressive"]


def test_line_login_state_rejects_external_redirect(monkeypatch):
    web_app = _load_web_app(monkeypatch)

    response = web_app.app.test_client().get("/line-login-start?redirect=https://evil.example/phish")
    from urllib.parse import parse_qs, urlparse

    query = parse_qs(urlparse(response.headers["Location"]).query)
    redirect_path = web_app._decode_line_login_state(query["state"][0])
    assert redirect_path == "/"
