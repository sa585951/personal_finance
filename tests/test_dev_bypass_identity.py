"""Loopback dev bypass must expose the same user id that write routes receive.

Web clients bind financial writes to /api/auth/me via X-Nomica-Request-Owner.
If the two ids differ, every create is rejected as REQUEST_OWNER_CHANGED.
"""
from tests.test_ai_parse_api import _load_web_app


class FakeUserManager:
    def __init__(self):
        self.calls = []

    def get_or_create_user_for_identity(self, provider, provider_user_id, display_name=None, provider_email=None, **_):
        self.calls.append((provider, provider_user_id))
        return {"id": f"00000000-0000-0000-0000-{len(provider_user_id):012d}", "display_name": display_name}


def _bypass_app(monkeypatch):
    app = _load_web_app(monkeypatch)
    monkeypatch.setattr(app, "DEV_AUTH_BYPASS", True)
    users = FakeUserManager()
    monkeypatch.setattr(app, "user_manager", users)
    return app, users


def _localhost(client, path, **kwargs):
    return client.get(path, base_url="http://localhost", environ_base={"REMOTE_ADDR": "127.0.0.1"}, **kwargs)


def test_auth_me_returns_internal_id_used_by_token_required(monkeypatch):
    app, users = _bypass_app(monkeypatch)
    seen = {}

    @app.app.route("/__test/owner")
    @app.token_required
    def owner(current_user_id):
        seen["id"] = current_user_id
        return {"ok": True}

    client = app.app.test_client()
    me = _localhost(client, "/api/auth/me", headers={"X-Dev-User": "amy-dev-user"})
    _localhost(client, "/__test/owner", headers={"X-Dev-User": "amy-dev-user"})

    assert me.status_code == 200
    assert me.get_json()["data"]["user_id"] == seen["id"]
    assert me.get_json()["data"]["name"] == "Amy"
    assert users.calls == [("dev", "amy-dev-user"), ("dev", "amy-dev-user")]


def test_unknown_dev_user_header_falls_back_to_default_user(monkeypatch):
    app, users = _bypass_app(monkeypatch)
    response = _localhost(app.app.test_client(), "/api/auth/me", headers={"X-Dev-User": "attacker"})
    assert response.status_code == 200
    assert users.calls == [("dev", "local-dev-user")]
