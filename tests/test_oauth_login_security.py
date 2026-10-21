from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from sqlalchemy import update

from models.schema import oauth_login_states_table as states
from tests.test_ai_parse_api import _load_web_app


def start(app, client, path="/trips/example"):
    response = client.get("/line-login-start", query_string={"redirect": path})
    assert response.status_code == 302
    params = {key: values[0] for key, values in parse_qs(urlparse(response.location).query).items()}
    browser = client.get_cookie(app.LINE_LOGIN_BROWSER_COOKIE, path="/line-login-callback").value
    return params, browser


def provider(monkeypatch, app, nonce):
    calls = []
    def post(*args, **kwargs):
        calls.append(kwargs)
        token = jwt.encode({
            "sub": "line-user", "name": "Test", "iss": "https://access.line.me",
            "aud": app.LINE_CHANNEL_ID, "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5), "nonce": nonce,
        }, app.LINE_CHANNEL_SECRET, algorithm="HS256")
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"id_token": token})
    monkeypatch.setattr(app.requests, "post", post)
    app.user_manager = SimpleNamespace(get_or_create_user_for_identity=lambda **kwargs: {
        "id": "22222222-2222-2222-2222-222222222222", "display_name": "Test",
    })
    return calls


def test_state_is_random_browser_bound_and_callback_does_not_contact_provider_without_cookie(monkeypatch):
    app = _load_web_app(monkeypatch)
    first, second = app.app.test_client(), app.app.test_client()
    params, _ = start(app, first)
    other, _ = start(app, second)
    assert params["state"] != other["state"] and params["nonce"] != other["nonce"]
    calls = provider(monkeypatch, app, params["nonce"])
    response = second.get("/line-login-callback", query_string={"state": params["state"], "code": "test"})
    assert response.status_code == 400 and not calls


@pytest.mark.parametrize("kind", ["expired", "missing", "tampered"])
def test_invalid_states_do_not_exchange_provider_tokens(monkeypatch, kind):
    app = _load_web_app(monkeypatch)
    client = app.app.test_client()
    params, _ = start(app, client)
    if kind == "expired":
        app.oauth_login_state_manager.session.execute(update(states).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    if kind == "missing":
        client.delete_cookie(app.LINE_LOGIN_BROWSER_COOKIE, path="/line-login-callback")
    calls = provider(monkeypatch, app, params["nonce"])
    response = client.get("/line-login-callback", query_string={"state": "x" * 64 if kind == "tampered" else params["state"], "code": "test"})
    assert response.status_code == 400 and not calls
    assert response.headers["Cache-Control"] == "no-store"


def test_success_consumes_state_even_if_browser_cookie_is_replayed(monkeypatch):
    app = _load_web_app(monkeypatch)
    client = app.app.test_client()
    params, browser = start(app, client)
    calls = provider(monkeypatch, app, params["nonce"])
    query = {"state": params["state"], "code": "test"}
    response = client.get("/line-login-callback", query_string=query)
    assert response.status_code == 302
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert set(parse_qs(urlparse(response.location).query)) == {"redirect"}
    assert response.location.startswith("https://frontend.example.test/auth-callback?")
    auth_cookie = client.get_cookie(app.APP_AUTH_COOKIE_NAME)
    assert auth_cookie and auth_cookie.http_only and auth_cookie.secure
    assert auth_cookie.same_site == "Lax" and auth_cookie.origin_only
    client.set_cookie(app.LINE_LOGIN_BROWSER_COOKIE, browser, path="/line-login-callback")
    assert client.get("/line-login-callback", query_string=query).status_code == 400
    assert len(calls) == 1 and calls[0]["timeout"] == 10


def test_wrong_provider_nonce_never_creates_app_session(monkeypatch):
    app = _load_web_app(monkeypatch)
    client = app.app.test_client()
    params, _ = start(app, client)
    provider(monkeypatch, app, "wrong")
    def forbidden(*args, **kwargs):
        pytest.fail("invalid nonce must not create an app session")
    monkeypatch.setattr(app, "_create_app_auth_token", forbidden)
    response = client.get("/line-login-callback", query_string={"state": params["state"], "code": "test"})
    assert response.status_code == 400


@pytest.mark.parametrize("path", ["//evil.example", "/\\evil.example", "/%5cevil.example", "/%2fevil.example", "/%0a/evil.example"])
def test_redirects_cannot_escape_the_frontend_origin(monkeypatch, path):
    app = _load_web_app(monkeypatch)
    client = app.app.test_client()
    params, browser = start(app, client, path)
    challenge = app.oauth_login_state_manager.consume(params["state"], browser)
    assert challenge["redirect_path"] == "/"
