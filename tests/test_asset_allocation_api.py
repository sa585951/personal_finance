import importlib
import sys
from datetime import datetime, timedelta, timezone

import jwt

from models.asset_allocation_manager import AllocationNotFoundError


USER_ID = "22222222-2222-2222-2222-222222222222"


class FakeAuthSessionManager:
    def validate_session(self, session_id, user_id):
        return {
            "id": session_id,
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "revoked_at": None,
        }


class FakeDBSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def remove(self):
        pass


class FakeAssetAllocationManager:
    def __init__(self):
        self.calls = []

    def list_portfolios(self, user_id):
        return [{"id": "portfolio-1", "name": "長期 ETF"}]

    def create_portfolio(self, user_id, name, base_currency):
        self.calls.append(("create_portfolio", user_id, name, base_currency))
        return {"id": "portfolio-1", "name": name, "base_currency": base_currency}

    def get_portfolio(self, user_id, portfolio_id):
        if portfolio_id == "missing":
            raise AllocationNotFoundError("找不到 Portfolio 或權限不足")
        return {"id": portfolio_id, "holdings": []}

    def create_holding(self, user_id, portfolio_id, account_id, name, **kwargs):
        if account_id == "bank-account":
            raise ValueError("Holding 只能連結 investment 帳戶")
        self.calls.append(("create_holding", user_id, portfolio_id, account_id, name, kwargs))
        return {"id": "holding-1", "name": name}

    def create_or_update_snapshot(self, user_id, portfolio_id, snapshot_date, items, note=None):
        self.calls.append(("snapshot", user_id, portfolio_id, snapshot_date, items, note))
        return {"id": "snapshot-1", "snapshot_date": snapshot_date, "items": items}

    def allocation_preview(self, user_id, portfolio_id, amount):
        self.calls.append(("preview", user_id, portfolio_id, amount))
        return {"portfolio_id": portfolio_id, "new_amount": float(amount), "allocations": []}


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
    web_app.db_session = FakeDBSession()
    web_app.asset_allocation_manager = FakeAssetAllocationManager()
    return web_app


def _auth_headers():
    token = jwt.encode(
        {
            "user_id": USER_ID,
            "session_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "provider": "line",
            "exp": datetime.now(timezone.utc) + timedelta(days=1),
        },
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_portfolio_routes_use_authenticated_user_and_commit(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    client = web_app.app.test_client()

    response = client.post(
        "/api/portfolios",
        json={"name": "長期 ETF", "base_currency": "TWD"},
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    assert response.get_json()["data"]["name"] == "長期 ETF"
    assert web_app.asset_allocation_manager.calls == [
        ("create_portfolio", USER_ID, "長期 ETF", "TWD")
    ]
    assert web_app.db_session.commits == 1


def test_allocation_routes_map_validation_and_ownership_errors(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    client = web_app.app.test_client()

    invalid_holding = client.post(
        "/api/portfolios/portfolio-1/holdings",
        json={"account_id": "bank-account", "name": "0050"},
        headers=_auth_headers(),
    )
    missing_portfolio = client.get(
        "/api/portfolios/missing",
        headers=_auth_headers(),
    )

    assert invalid_holding.status_code == 400
    assert invalid_holding.get_json()["message"] == "Holding 只能連結 investment 帳戶"
    assert missing_portfolio.status_code == 404
    assert missing_portfolio.get_json()["message"] == "找不到 Portfolio 或權限不足"
    assert web_app.db_session.rollbacks == 2


def test_snapshot_and_preview_routes_keep_shared_api_shape(monkeypatch):
    web_app = _load_web_app(monkeypatch)
    client = web_app.app.test_client()
    items = [{"holding_id": "holding-1", "value": 12000}]

    snapshot = client.post(
        "/api/portfolios/portfolio-1/snapshots",
        json={"snapshot_date": "2026-07-21", "items": items},
        headers=_auth_headers(),
    )
    preview = client.post(
        "/api/portfolios/portfolio-1/allocation-preview",
        json={"amount": 20000},
        headers=_auth_headers(),
    )

    assert snapshot.status_code == 201
    assert snapshot.get_json()["data"]["items"] == items
    assert preview.status_code == 200
    assert preview.get_json()["data"]["new_amount"] == 20000.0
