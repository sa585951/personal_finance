from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from models.ai_parse_event_manager import AIParseEventManager


class CapturingAIParseEventManager(AIParseEventManager):
    def __init__(self):
        super().__init__(db_session=None)
        self.last_record = None

    def record_parse_event(self, **kwargs):
        self.last_record = kwargs
        return kwargs


def test_record_from_parse_result_marks_success_for_valid_parse():
    manager = CapturingAIParseEventManager()
    parse_result = {
        "intent": "create_transaction",
        "raw_text": "早餐 100",
        "transaction": {"type": "expense"},
        "errors": [],
    }

    record = manager.record_from_parse_result(uuid4(), "line_bot", parse_result)

    assert record["source"] == "line_bot"
    assert record["raw_input"] == "早餐 100"
    assert record["status"] == "success"
    assert record["result_type"] == "expense"
    assert record["error_message"] is None


def test_record_from_parse_result_marks_failed_when_errors_exist():
    manager = CapturingAIParseEventManager()
    parse_result = {
        "intent": "other",
        "raw_text": "早餐",
        "transaction": None,
        "errors": ["無法識別金額"],
    }

    record = manager.record_from_parse_result(uuid4(), "web", parse_result)

    assert record["status"] == "failed"
    assert record["result_type"] == "other"
    assert record["error_message"] == "無法識別金額"


def test_to_jsonable_converts_non_json_native_values():
    manager = AIParseEventManager(db_session=None)
    user_id = uuid4()
    value = {
        "id": user_id,
        "amount": Decimal("120.50"),
        "date": date(2027, 3, 1),
        "created_at": datetime(2027, 3, 1, 12, 30, tzinfo=timezone.utc),
        "items": (Decimal("1.5"), user_id),
    }

    result = manager._to_jsonable(value)

    assert result == {
        "id": str(user_id),
        "amount": "120.50",
        "date": "2027-03-01",
        "created_at": "2027-03-01 12:30:00+00:00",
        "items": ["1.5", str(user_id)],
    }
