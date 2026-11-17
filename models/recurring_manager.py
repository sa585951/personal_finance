"""Fixed monthly income and expenses.

A rule describes something that repeats on a day of every month. It never writes to the
ledger by itself. When the person opens the app, months that are due (up to three months
back, so a long absence does not bury them) become *pending occurrences*; confirming one
creates the real transaction through the normal create path, skipping one records that
month as skipped. Pending occurrences hold their own copy of the details, so editing a
rule only changes months that have not been generated yet, and deleting a rule removes
whatever was still waiting.
"""
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import DEFAULT_CURRENCY
from .schema import (
    accounts_table, categories_table, recurring_occurrences_table as occurrences,
    recurring_rules_table as rules,
)

TIMEZONE = ZoneInfo("Asia/Taipei")
BACKFILL_MONTHS = 3
MAX_AMOUNT = Decimal("999999999")
TYPES = ("expense", "income")


class RecurringError(ValueError):
    """A request the person can fix (bad amount, unknown account, already handled)."""


def today_in_taipei():
    return datetime.now(TIMEZONE).date()


def _month_start(value, offset=0):
    index = value.year * 12 + value.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def due_date_for(month_start, day_of_month):
    """The chosen day, or the last day of a shorter month (31 -> Feb 28/29)."""
    return month_start.replace(day=min(day_of_month, monthrange(month_start.year, month_start.month)[1]))


def _uuid(value, label):
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise RecurringError(f"{label} 格式不正確") from None


def _amount(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise RecurringError("金額格式不正確") from None
    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
        raise RecurringError("金額必須大於 0")
    return amount.quantize(Decimal("0.0001"))


def _date(value, label):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise RecurringError(f"{label}格式不正確（YYYY-MM-DD）") from None


class RecurringManager:
    def __init__(self, db_session, transaction_service):
        self.db_session = db_session
        self.transactions = transaction_service

    # --- rules ------------------------------------------------------------
    def list_rules(self, user_id, today=None):
        today = today or today_in_taipei()
        owner = _uuid(user_id, "使用者")
        rows = self.db_session.execute(
            select(rules, accounts_table.c.name.label("account_name"))
            .outerjoin(accounts_table, rules.c.account_id == accounts_table.c.id)
            .where(rules.c.user_id == owner).order_by(rules.c.created_at)
        ).mappings().all()
        return [self._rule_view(row, today) for row in rows]

    def create_rule(self, user_id, data, today=None):
        today = today or today_in_taipei()
        owner = _uuid(user_id, "使用者")
        values = self._clean(owner, data, today)
        rule_id = self.db_session.execute(
            rules.insert().values(user_id=owner, **values).returning(rules.c.id)
        ).scalar_one()
        return str(rule_id)

    def update_rule(self, user_id, rule_id, data, today=None):
        """Edits the rule only; occurrences that already exist keep their details."""
        today = today or today_in_taipei()
        owner = _uuid(user_id, "使用者")
        current = self._owned_rule(owner, rule_id)
        merged = {**{key: current[key] for key in (
            "title", "type", "budget_category", "amount", "account_id", "day_of_month",
            "start_date", "end_date", "description", "is_active")}, **data}
        if "account_id" not in data:
            merged["account_id"] = str(current["account_id"]) if current["account_id"] else None
        values = self._clean(owner, merged, today)
        self.db_session.execute(
            update(rules).where(rules.c.id == current["id"]).values(updated_at=datetime.now(TIMEZONE), **values)
        )

    def delete_rule(self, user_id, rule_id):
        """Hard delete: pending and skipped months disappear with it. Transactions the person
        already confirmed stay in the ledger untouched."""
        owner = _uuid(user_id, "使用者")
        current = self._owned_rule(owner, rule_id)
        self.db_session.execute(delete(rules).where(rules.c.id == current["id"]))

    def delete_all_for_user(self, user_id):
        self.db_session.execute(delete(rules).where(rules.c.user_id == _uuid(user_id, "使用者")))

    # --- generation -------------------------------------------------------
    def generate_due(self, user_id, today=None):
        """Create pending occurrences for due months in the last three. Safe to call on every
        visit and from several devices at once: (rule, month) is unique."""
        today = today or today_in_taipei()
        owner = _uuid(user_id, "使用者")
        active = self.db_session.execute(
            select(rules).where(rules.c.user_id == owner, rules.c.is_active.is_(True))
        ).mappings().all()
        created = 0
        for rule in active:
            for back in range(BACKFILL_MONTHS):
                month = _month_start(today, -back)
                due = due_date_for(month, rule["day_of_month"])
                if due > today or due < rule["start_date"]:
                    continue
                if rule["end_date"] is not None and due > rule["end_date"]:
                    continue
                result = self.db_session.execute(
                    pg_insert(occurrences).values(
                        rule_id=rule["id"], user_id=owner, month=month, due_date=due,
                        title=rule["title"], type=rule["type"], budget_category=rule["budget_category"],
                        amount=rule["amount"], account_id=rule["account_id"], description=rule["description"],
                    ).on_conflict_do_nothing(constraint="uq_recurring_occurrences_rule_month")
                )
                created += result.rowcount
        return created

    def list_pending(self, user_id):
        owner = _uuid(user_id, "使用者")
        rows = self.db_session.execute(
            select(occurrences, accounts_table.c.name.label("account_name"))
            .outerjoin(accounts_table, occurrences.c.account_id == accounts_table.c.id)
            .where(occurrences.c.user_id == owner, occurrences.c.status == "pending")
            .order_by(occurrences.c.due_date, occurrences.c.created_at)
        ).mappings().all()
        return [{
            "id": str(row["id"]), "rule_id": str(row["rule_id"]), "title": row["title"], "type": row["type"],
            "budget_category": row["budget_category"], "amount": float(row["amount"]),
            "due_date": row["due_date"].isoformat(), "account_id": str(row["account_id"]) if row["account_id"] else None,
            "account_name": row["account_name"] or "",
        } for row in rows]

    # --- confirming -------------------------------------------------------
    def confirm(self, user_id, occurrence_id, amount=None, transaction_date=None):
        owner = _uuid(user_id, "使用者")
        occurrence = self._pending_occurrence(owner, occurrence_id)
        final_amount = _amount(amount) if amount not in (None, "") else occurrence["amount"]
        final_date = _date(transaction_date, "日期") if transaction_date else occurrence["due_date"]
        created = self.transactions.create_transaction(owner, {
            "date": final_date.isoformat(),
            "item": occurrence["title"],
            "amount": format(final_amount, "f"),
            "type": occurrence["type"],
            "budget_category": occurrence["budget_category"],
            "description": occurrence["description"],
            "account_id": str(occurrence["account_id"]) if occurrence["account_id"] else None,
            # The occurrence id makes a double tap or a retry create the transaction once.
            "client_request_id": str(occurrence["id"]),
        })
        if not created["success"]:
            raise RecurringError(created["message"] or "無法建立這筆紀錄")
        self.db_session.execute(
            update(occurrences).where(occurrences.c.id == occurrence["id"])
            .values(status="confirmed", transaction_id=created["transaction_id"], updated_at=datetime.now(TIMEZONE))
        )
        return str(created["transaction_id"])

    def update_pending_amount(self, user_id, occurrence_id, amount):
        """Change this month's amount without booking it; the person confirms separately."""
        owner = _uuid(user_id, "使用者")
        occurrence = self._pending_occurrence(owner, occurrence_id)
        self.db_session.execute(
            update(occurrences).where(occurrences.c.id == occurrence["id"])
            .values(amount=_amount(amount), updated_at=datetime.now(TIMEZONE))
        )

    def skip(self, user_id, occurrence_id):
        owner = _uuid(user_id, "使用者")
        occurrence = self._pending_occurrence(owner, occurrence_id)
        self.db_session.execute(
            update(occurrences).where(occurrences.c.id == occurrence["id"])
            .values(status="skipped", updated_at=datetime.now(TIMEZONE))
        )

    # --- internals --------------------------------------------------------
    def _pending_occurrence(self, owner, occurrence_id):
        row = self.db_session.execute(
            select(occurrences).where(occurrences.c.id == _uuid(occurrence_id, "固定收支"),
                                      occurrences.c.user_id == owner).with_for_update()
        ).mappings().first()
        if not row:
            raise RecurringError("找不到這筆固定收支")
        if row["status"] != "pending":
            raise RecurringError("這筆已經處理過了")
        return row

    def _owned_rule(self, owner, rule_id):
        row = self.db_session.execute(
            select(rules).where(rules.c.id == _uuid(rule_id, "固定收支"), rules.c.user_id == owner).with_for_update()
        ).mappings().first()
        if not row:
            raise RecurringError("找不到這筆固定收支")
        return row

    def _clean(self, owner, data, today):
        title = str(data.get("title") or "").strip()
        if not title or len(title) > 100:
            raise RecurringError("請輸入 1～100 字的項目名稱")
        kind = data.get("type")
        if kind not in TYPES:
            raise RecurringError("類型必須是支出或收入")
        category = str(data.get("budget_category") or "").strip()
        if not category or not self._category_exists(owner, category, kind):
            raise RecurringError("找不到這個分類")
        try:
            day = int(data.get("day_of_month"))
        except (TypeError, ValueError):
            raise RecurringError("每月幾號必須是 1～31") from None
        if not 1 <= day <= 31:
            raise RecurringError("每月幾號必須是 1～31")
        start = _date(data["start_date"], "開始日") if data.get("start_date") else today
        end = _date(data["end_date"], "結束日") if data.get("end_date") else None
        if end is not None and end < start:
            raise RecurringError("結束日不能早於開始日")
        description = str(data.get("description") or "").strip()
        if len(description) > 200:
            raise RecurringError("備註最多 200 字")
        return dict(
            title=title, type=kind, budget_category=category, amount=_amount(data.get("amount")),
            account_id=self._account(owner, data.get("account_id")), day_of_month=day,
            start_date=start, end_date=end, description=description,
            is_active=bool(data.get("is_active", True)),
        )

    def _category_exists(self, owner, name, kind):
        return self.db_session.execute(
            select(categories_table.c.id).where(
                categories_table.c.name == name, categories_table.c.deleted_at.is_(None),
                categories_table.c.scope == "transaction", categories_table.c.kind.in_((kind, "both")),
                or_(categories_table.c.user_id.is_(None), categories_table.c.user_id == owner),
            ).limit(1)
        ).first() is not None

    def _account(self, owner, account_id):
        if not account_id:
            return None
        account = self.db_session.execute(
            select(accounts_table.c.id, accounts_table.c.currency).where(
                accounts_table.c.id == _uuid(account_id, "帳戶"), accounts_table.c.user_id == owner,
                accounts_table.c.deleted_at.is_(None))
        ).first()
        if not account:
            raise RecurringError("找不到這個帳戶")
        if account.currency != DEFAULT_CURRENCY:
            raise RecurringError(f"固定收支目前只支援 {DEFAULT_CURRENCY} 帳戶")
        return account.id

    def _rule_view(self, row, today):
        return {
            "id": str(row["id"]), "title": row["title"], "type": row["type"],
            "budget_category": row["budget_category"], "amount": float(row["amount"]),
            "account_id": str(row["account_id"]) if row["account_id"] else None,
            "account_name": row["account_name"] or "", "day_of_month": row["day_of_month"],
            "start_date": row["start_date"].isoformat(),
            "end_date": row["end_date"].isoformat() if row["end_date"] else None,
            "description": row["description"], "is_active": row["is_active"],
            "next_due": self._next_due(row, today),
        }

    @staticmethod
    def _next_due(rule, today):
        if not rule["is_active"]:
            return None
        for ahead in range(0, 26):
            due = due_date_for(_month_start(today, ahead), rule["day_of_month"])
            if due < today or due < rule["start_date"]:
                continue
            if rule["end_date"] is not None and due > rule["end_date"]:
                return None
            return due.isoformat()
        return None
