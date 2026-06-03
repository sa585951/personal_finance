import uuid
from types import SimpleNamespace

from models.linebot.manager import LineBotManager


class FakeAIParseEventManager:
    def __init__(self):
        self.confirmed_event = None

    def confirm_event(self, user_id, event_id, result_type, result_id):
        self.confirmed_event = {
            "user_id": user_id,
            "event_id": event_id,
            "result_type": result_type,
            "result_id": result_id,
        }
        return {"status": "confirmed"}


def _fake_manager(transaction_id=None):
    manager = SimpleNamespace()
    manager.ai_parse_event_manager = FakeAIParseEventManager()
    manager.message_handler = SimpleNamespace(
        budget_manager=SimpleNamespace(last_created_transaction_id=transaction_id)
    )
    return manager


def test_linebot_confirms_parse_event_when_transaction_is_created():
    transaction_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    manager = _fake_manager(transaction_id)
    parse_event = {"id": uuid.UUID("11111111-1111-1111-1111-111111111111")}

    LineBotManager._confirm_parse_event_if_transaction_created(
        manager,
        "22222222-2222-2222-2222-222222222222",
        parse_event,
        {"type": "expense"},
    )

    assert manager.ai_parse_event_manager.confirmed_event == {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "event_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "result_type": "expense",
        "result_id": transaction_id,
    }


def test_linebot_does_not_confirm_parse_event_for_non_transaction_message():
    manager = _fake_manager(uuid.UUID("33333333-3333-3333-3333-333333333333"))

    result = LineBotManager._confirm_parse_event_if_transaction_created(
        manager,
        "22222222-2222-2222-2222-222222222222",
        {"id": uuid.UUID("11111111-1111-1111-1111-111111111111")},
        {"type": "query"},
    )

    assert result is None
    assert manager.ai_parse_event_manager.confirmed_event is None


def test_linebot_does_not_confirm_parse_event_without_created_transaction_id():
    manager = _fake_manager(transaction_id=None)

    result = LineBotManager._confirm_parse_event_if_transaction_created(
        manager,
        "22222222-2222-2222-2222-222222222222",
        {"id": uuid.UUID("11111111-1111-1111-1111-111111111111")},
        {"type": "income"},
    )

    assert result is None
    assert manager.ai_parse_event_manager.confirmed_event is None
