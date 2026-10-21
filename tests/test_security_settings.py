import pytest

from models.security_settings import load_security_settings


def production(**changes):
    return {"NOMICA_ENV": "production", "FRONTEND_BASE_URL": "https://nomica.example",
            "VITE_BACKEND_BASE_URL": "https://nomica.example", **changes}


@pytest.mark.parametrize("changes", [
    {"NOMICA_ENV": "prod"}, {"NOMICA_ENV": "unknown"}, {"DEV_AUTH_BYPASS": "true"},
    {"DEV_AUTH_BYPASS": "1"}, {"FLASK_DEBUG": "1"}, {"FLASK_DEBUG": "true"}, {"FLASK_DEBUG": "yes"},
    {"FRONTEND_BASE_URL": "http://nomica.example"},
    {"VITE_BACKEND_BASE_URL": "https://backend.example"},
    {"FRONTEND_BASE_URL": "https://user:password@nomica.example"},
    {"FRONTEND_BASE_URL": "https://nomica.example/path"},
    {"FRONTEND_BASE_URL": "https://nomica.example?query=1"},
])
def test_unsafe_public_settings_fail_closed(changes):
    with pytest.raises(ValueError):
        load_security_settings(production(**changes))


def test_missing_environment_defaults_to_secure_production():
    settings = production()
    settings.pop("NOMICA_ENV")
    assert load_security_settings(settings).secure_cookies
    assert not load_security_settings(settings).dev_auth_bypass


@pytest.mark.parametrize("environment", ["development", "testing"])
def test_development_auth_requires_explicit_local_origins(environment):
    settings = {"NOMICA_ENV": environment, "FRONTEND_BASE_URL": "http://localhost:5173",
                "VITE_BACKEND_BASE_URL": "http://localhost:5000", "DEV_AUTH_BYPASS": "true"}
    result = load_security_settings(settings)
    assert result.dev_auth_bypass and not result.secure_cookies
    with pytest.raises(ValueError):
        load_security_settings({**settings, "FRONTEND_BASE_URL": "https://public.example"})


def test_enabling_debug_after_startup_cannot_serve_public_requests(monkeypatch):
    from tests.test_ai_parse_api import _load_web_app
    app = _load_web_app(monkeypatch)
    app.app.debug = True
    response = app.app.test_client().get("/healthcheck")
    assert response.status_code == 503


def test_loopback_bypass_cannot_be_used_with_a_public_host(monkeypatch):
    from tests.test_ai_parse_api import _load_web_app
    app = _load_web_app(monkeypatch)
    monkeypatch.setattr(app, "DEV_AUTH_BYPASS", True)
    response = app.app.test_client().get("/api/auth/me", base_url="https://public.example")
    assert response.status_code == 403
