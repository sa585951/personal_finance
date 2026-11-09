import base64
import hashlib
import hmac
import json

from models.optional_access import load_optional_access
from tests.test_ai_parse_api import _load_web_app


def test_existing_help_only_setting_routes_to_bookkeeping(monkeypatch):
    app = _load_web_app(monkeypatch)
    access = load_optional_access({"NOMICA_ENV": "production", "NOMICA_LINE_MODE": "help_only",
                                   "NOMICA_LINE_HELP_USER_IDS": "U-old-tester"})
    monkeypatch.setattr(app, "OPTIONAL_ACCESS", access)
    replies = []
    processed = []

    def process(event):
        processed.append(event.message.text)
        return "確認收支"

    monkeypatch.setattr(app.linebot_manager, "process_oral_event", process)
    monkeypatch.setattr(app.linebot_manager.line_bot_api, "reply_message", replies.append)
    client = app.app.test_client()
    assert send(client, [event("午餐 120 現金")], valid=False).status_code == 400
    assert send(client, [event("午餐 120 現金")]).status_code == 200
    assert processed == ["午餐 120 現金"]
    assert len(replies) == 1
    assert "確認收支" in str(replies[0].messages[0].to_dict())


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
