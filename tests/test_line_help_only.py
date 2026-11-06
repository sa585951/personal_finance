import base64
import hashlib
import hmac
import json

import pytest

from models.optional_access import load_optional_access
from tests.test_ai_parse_api import _load_web_app


def policy():
    return load_optional_access({
        "NOMICA_ENV": "production",
        "NOMICA_LINE_MODE": "help_only",
        "NOMICA_LINE_HELP_USER_IDS": " U-tester , U-other ",
    })


def test_help_only_requires_an_explicit_allowlist():
    with pytest.raises(ValueError, match="NOMICA_LINE_HELP_USER_IDS"):
        load_optional_access({"NOMICA_LINE_MODE": "help_only", "NOMICA_LINE_HELP_USER_IDS": " , "})


def test_help_only_does_not_enable_chat_writes_or_ai():
    access = policy()
    assert access.line_help_user_ids == frozenset({"U-tester", "U-other"})
    assert not access.line_interactions and not access.ai_parse and not access.cloud_ai


@pytest.fixture
def help_bot(monkeypatch):
    app = _load_web_app(monkeypatch)
    monkeypatch.setattr(app, "OPTIONAL_ACCESS", policy())
    replies = []

    def forbid(*args, **kwargs):
        pytest.fail("help-only webhook entered the chat write path")

    monkeypatch.setattr(app.linebot_manager, "process_event", forbid)
    monkeypatch.setattr(app.linebot_manager.line_bot_api, "reply_message", replies.append)
    yield app.app.test_client(), replies
    assert app.db_session.commits == app.db_session.rollbacks == 0


def send(client, events, *, valid=True):
    body = json.dumps({"destination": "U-bot", "events": events}).encode()
    key = b"line-message-secret" if valid else b"wrong-secret"
    signature = base64.b64encode(hmac.digest(key, body, hashlib.sha256)).decode()
    return client.post("/line-webhook", data=body, headers={"X-Line-Signature": signature})


def event(text="幫助", source=None):
    return {
        "type": "message",
        "mode": "active",
        "timestamp": 1,
        "webhookEventId": "synthetic-event",
        "deliveryContext": {"isRedelivery": False},
        "source": source or {"type": "user", "userId": "U-tester"},
        "replyToken": "synthetic-reply-token",
        "message": {"id": "123", "type": "text", "text": text, "quoteToken": "synthetic-quote-token"},
    }


def test_signed_help_replies_only_to_allowed_direct_message(help_bot):
    client, replies = help_bot
    events = [
        event("午餐 100"),
        event(source={"type": "user", "userId": "U-unlisted"}),
        event(source={"type": "group", "groupId": "C-group", "userId": "U-tester"}),
        {**event(), "type": "postback", "postback": {"data": "nomica.confirm:synthetic"}},
        {**event(), "mode": "standby"},
        {**event(" 幫助 "), "replyToken": "allowed-reply-token"},
    ]
    assert send(client, events).status_code == 200
    assert len(replies) == 1
    assert replies[0].reply_token == "allowed-reply-token"
    assert replies[0].messages[0].type == "text"
    assert "Web" in replies[0].messages[0].text


def test_empty_and_invalid_deliveries_never_reply(help_bot):
    client, replies = help_bot
    assert send(client, []).status_code == 200
    assert send(client, [event()], valid=False).status_code == 400
    assert replies == []
