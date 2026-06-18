from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .schema import categories_table, currencies_table


CURRENCIES = [
    {"code": "TWD", "name": "New Taiwan Dollar", "symbol": "NT$", "minor_unit": 0},
    {"code": "JPY", "name": "Japanese Yen", "symbol": "¥", "minor_unit": 0},
    {"code": "KRW", "name": "Korean Won", "symbol": "₩", "minor_unit": 0},
    {"code": "USD", "name": "US Dollar", "symbol": "$", "minor_unit": 2},
    {"code": "EUR", "name": "Euro", "symbol": "€", "minor_unit": 2},
]


EXPENSE_CATEGORIES = [
    ("food", "伙食"),
    ("transport", "交通"),
    ("lodging", "住宿"),
    ("shopping", "購物"),
    ("entertainment", "娛樂"),
    ("medical", "醫療"),
    ("work", "工作"),
    ("daily", "生活"),
    ("subscriptions", "訂閱"),
    ("fees", "手續費"),
    ("other", "其他"),
]


INCOME_CATEGORIES = [
    ("salary", "薪資"),
    ("bonus", "獎金"),
    ("interest", "利息"),
    ("gift", "禮金/贈與"),
    ("reimbursement", "報銷/補貼"),
    ("other_income", "其他收入"),
]


def seed_reference_data(connection):
    """Insert idempotent reference data used by the MVP schema."""
    currency_stmt = pg_insert(currencies_table).values(CURRENCIES)
    connection.execute(
        currency_stmt.on_conflict_do_nothing(index_elements=["code"])
    )

    categories = []
    for sort_order, (code, name) in enumerate(EXPENSE_CATEGORIES, start=1):
        categories.append(
            {
                "kind": "expense",
                "scope": "transaction",
                "code": code,
                "name": name,
                "is_system": True,
                "sort_order": sort_order,
            }
        )
    for sort_order, (code, name) in enumerate(INCOME_CATEGORIES, start=1):
        categories.append(
            {
                "kind": "income",
                "scope": "transaction",
                "code": code,
                "name": name,
                "is_system": True,
                "sort_order": sort_order,
            }
        )

    for category in categories:
        existing = connection.execute(
            select(categories_table.c.id).where(
                categories_table.c.user_id.is_(None),
                categories_table.c.parent_id.is_(None),
                categories_table.c.kind == category["kind"],
                categories_table.c.scope == category["scope"],
                categories_table.c.code == category["code"],
            )
        ).first()
        if existing is None:
            connection.execute(insert(categories_table).values(category))
