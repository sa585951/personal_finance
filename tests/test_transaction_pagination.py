import uuid
from datetime import date, datetime, timezone

import pytest

from models.budget_manager import BudgetManager


def test_transaction_cursor_round_trip():
    transaction_date = date(2026, 8, 19)
    created_at = datetime(2026, 8, 19, 8, 30, 15, tzinfo=timezone.utc)
    transaction_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    cursor = BudgetManager._encode_transaction_cursor(
        transaction_date,
        created_at,
        transaction_id,
    )

    assert BudgetManager._decode_transaction_cursor(cursor) == (
        transaction_date,
        created_at,
        transaction_id,
    )


@pytest.mark.parametrize("cursor", ["not-base64", "e30", ""])
def test_transaction_cursor_rejects_invalid_value(cursor):
    with pytest.raises(ValueError, match="cursor 格式不正確"):
        BudgetManager._decode_transaction_cursor(cursor)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"transaction_type": "transfer"}, "type 僅支援 expense 或 income"),
        ({"month": "2026/08"}, "month 格式必須為 YYYY-MM"),
        ({"limit": 0}, "limit 必須介於 1 到 50"),
        ({"limit": 51}, "limit 必須介於 1 到 50"),
    ],
)
def test_transaction_pagination_rejects_invalid_filters(kwargs, message):
    manager = BudgetManager(db_session=None)

    with pytest.raises(ValueError, match=message):
        manager.get_all_transactions(
            "11111111-1111-1111-1111-111111111111",
            **kwargs,
        )
