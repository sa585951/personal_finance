from types import SimpleNamespace

import pytest

from models.linebot.manager import GeminiModelAdapter
from models.linebot.parsers import GeminiParser
from models.optional_access import OptionalAccess, load_optional_access
from tests.test_ai_parse_api import FakeDBSession, _auth_headers, _load_web_app


def test_public_defaults_disable_all_unverified_optional_entries():
    policy = load_optional_access({})
    assert not policy.ai_parse and not policy.line_interactions and not policy.cloud_ai


@pytest.mark.parametrize("key", ["NOMICA_AI_MODE", "NOMICA_LINE_MODE"])
@pytest.mark.parametrize("value", ["public", "enabled", "true", "synthetic"])
def test_public_optional_modes_fail_closed(key, value):
    with pytest.raises(ValueError):
        load_optional_access({"NOMICA_ENV": "production", key: value,
                              "FRONTEND_BASE_URL": "https://nomica.example",
                              "VITE_BACKEND_BASE_URL": "https://nomica.example"})


def test_synthetic_mode_never_enables_cloud():
    policy = load_optional_access({"NOMICA_ENV": "testing", "NOMICA_AI_MODE": "synthetic",
        "NOMICA_LINE_MODE": "synthetic", "FRONTEND_BASE_URL": "http://localhost:5173",
        "VITE_BACKEND_BASE_URL": "http://localhost:5000"})
    assert policy.ai_parse and policy.line_interactions and not policy.cloud_ai


def test_shared_provider_adapter_never_dispatches_even_with_a_key(monkeypatch):
    monkeypatch.setenv("NOMICA_AI_MODE", "disabled")
    monkeypatch.setenv("NOMICA_LINE_MODE", "disabled")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-key")
    def forbidden(**kwargs):
        pytest.fail("disabled adapter must not dispatch to provider")
    adapter = GeminiModelAdapter(SimpleNamespace(models=SimpleNamespace(generate_content=forbidden)), "test-model")
    with pytest.raises(RuntimeError, match="paused"):
        adapter.generate_content("synthetic input")


def test_disabled_web_parse_does_not_parse_or_persist(monkeypatch):
    app = _load_web_app(monkeypatch)
    monkeypatch.setattr(app, "OPTIONAL_ACCESS", OptionalAccess(False, False))
    def forbidden(*args, **kwargs):
        pytest.fail("disabled parse must stop before any model or event write")
    monkeypatch.setattr(app.linebot_manager.message_parser, "parse_shared", forbidden)
    db = FakeDBSession()
    monkeypatch.setattr(app, "db_session", db)
    client = app.app.test_client()
    assert client.post("/api/ai/parse", json={"text": "test"}).status_code == 401
    response = client.post("/api/ai/parse", json={"text": "test"}, headers=_auth_headers())
    assert response.status_code == 503 and response.json["code"] == "AI_DISABLED"
    assert db.commits == db.rollbacks == 0
    caps = client.get("/api/capabilities", headers=_auth_headers())
    assert caps.json["data"] == {"ai_parse": False, "line_interactions": False}
    assert caps.headers["Cache-Control"] == "no-store"


def test_disabled_line_acknowledges_only_after_signature_validation(monkeypatch):
    app = _load_web_app(monkeypatch)
    monkeypatch.setattr(app, "OPTIONAL_ACCESS", OptionalAccess(False, False))
    def forbidden(*args, **kwargs):
        pytest.fail("disabled LINE must not process an event, profile, draft or ledger")
    # A controlled SDK boundary establishes valid vs invalid signatures.
    from linebot.v3.exceptions import InvalidSignatureError
    def parse(body, signature):
        if signature != "test-valid":
            raise InvalidSignatureError("bad")
        return [object()]
    monkeypatch.setattr(app, "linebot_manager", SimpleNamespace(
        parser=SimpleNamespace(parse=parse), process_event=forbidden,
    ))
    client = app.app.test_client()
    assert client.post("/line-webhook", data="{}", headers={"X-Line-Signature": "invalid"}).status_code == 400
    response = client.post("/line-webhook", data="{}", headers={"X-Line-Signature": "test-valid"})
    assert response.status_code == 200 and "paused" in response.text
    assert app.db_session.commits == 0


def test_parser_errors_do_not_log_or_return_provider_payload(caplog):
    secret = "PRIVATE_INPUT_AND_PROVIDER_TOKEN"
    class BrokenModel:
        def generate_content(self, prompt):
            raise RuntimeError(secret)
    result = GeminiParser(BrokenModel(), "{message}").parse("synthetic text")
    assert result == {"type": "other", "error": "parser_unavailable"}
    assert secret not in caplog.text and secret not in str(result)


@pytest.mark.parametrize("payload", [[], {"text": 12}, {"text": "x" * 1001}])
def test_synthetic_parse_still_validates_input_before_parser(monkeypatch, payload):
    app = _load_web_app(monkeypatch)
    def forbidden(*args, **kwargs):
        pytest.fail("invalid input must not reach the parser")
    monkeypatch.setattr(app.linebot_manager.message_parser, "parse_shared", forbidden)
    response = app.app.test_client().post("/api/ai/parse", json=payload, headers=_auth_headers())
    assert response.status_code == 400
