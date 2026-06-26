import base64
import hashlib
import hmac
import json
from types import SimpleNamespace

from linebot.v3 import WebhookParser
from linebot.v3.messaging import FlexMessage, PushMessageRequest, ReplyMessageRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from models.linebot.manager import LineBotManager
from models.linebot.response_builder import ResponseBuilder


class FakeMessagingApi:
    def __init__(self):
        self.reply_request = None
        self.push_request = None

    def reply_message(self, request):
        self.reply_request = request

    def push_message(self, request):
        self.push_request = request


def _manager_with_fake_api():
    manager = object.__new__(LineBotManager)
    manager.line_bot_api = FakeMessagingApi()
    manager.message_handler = SimpleNamespace(response_builder=ResponseBuilder())
    return manager


def test_reply_message_uses_sdk_v3_request_model():
    manager = _manager_with_fake_api()

    LineBotManager.reply_message_flex(manager, "reply-token", "測試通知")

    request = manager.line_bot_api.reply_request
    assert isinstance(request, ReplyMessageRequest)
    assert request.reply_token == "reply-token"
    assert len(request.messages) == 1
    assert isinstance(request.messages[0], FlexMessage)
    assert request.messages[0].alt_text == "通知"


def test_push_message_uses_sdk_v3_request_model():
    manager = _manager_with_fake_api()

    LineBotManager.push_message_flex(manager, "line-user-id", "測試通知")

    request = manager.line_bot_api.push_request
    assert isinstance(request, PushMessageRequest)
    assert request.to == "line-user-id"
    assert len(request.messages) == 1
    assert isinstance(request.messages[0], FlexMessage)


def test_webhook_parser_returns_sdk_v3_text_event():
    secret = "test-channel-secret"
    body = json.dumps(
        {
            "destination": "Udestination",
            "events": [
                {
                    "type": "message",
                    "message": {
                        "type": "text",
                        "id": "message-id",
                        "text": "午餐 150",
                        "quoteToken": "quote-token",
                    },
                    "webhookEventId": "webhook-event-id",
                    "deliveryContext": {"isRedelivery": False},
                    "timestamp": 1710000000000,
                    "source": {"type": "user", "userId": "Uuser"},
                    "replyToken": "reply-token",
                    "mode": "active",
                }
            ],
        },
        separators=(",", ":"),
    )
    signature = base64.b64encode(
        hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    ).decode()

    events = WebhookParser(secret).parse(body, signature)

    assert len(events) == 1
    assert isinstance(events[0], MessageEvent)
    assert isinstance(events[0].message, TextMessageContent)
    assert events[0].message.text == "午餐 150"
