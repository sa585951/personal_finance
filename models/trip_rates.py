"""Shared exchange rates for a trip: one rate per foreign currency, set by the trip owner.

A rate only supplies the default for expenses added afterwards. Recorded expenses keep the rate they
were saved with unless the owner explicitly re-applies a rate, which is refused once any settlement
has been recorded (those payments were agreed on the old numbers).
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from .asset_manager import SUPPORTED_CURRENCIES
from .budget_manager import DEFAULT_EXCHANGE_RATES, BudgetManager
from .schema import (
    accounts_table, categories_table, settlements_table, transaction_splits_table, transactions_table,
    trip_exchange_rate_changes_table, trip_exchange_rates_table, trip_members_table, users_table,
)
from .trip_manager import TripManager

MIN_RATE = Decimal("0.00000001")
MAX_RATE = Decimal("1000000")
HISTORY_LIMIT = 10
MONEY = Decimal("0.01")


def parse_rate(value):
    try:
        rate = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        raise ValueError("匯率格式不正確") from None
    if not rate.is_finite() or rate < MIN_RATE or rate > MAX_RATE:
        raise ValueError("匯率必須大於 0，且不超過 1,000,000")
    # The column keeps 8 decimals; refuse anything it would silently round.
    if rate != rate.quantize(MIN_RATE):
        raise ValueError("匯率最多 8 位小數")
    return rate.normalize() if rate == rate.to_integral_value() else rate


class TripRateManager:
    def __init__(self, db_session):
        self.db_session = db_session
        self.trips = TripManager(db_session)
        self.budget = BudgetManager(db_session)

    # -- reading ---------------------------------------------------------------------------

    def list_rates(self, user_id, trip_id):
        trip = self.trips._ensure_trip_access(user_id, trip_id)
        base = trip["base_currency"]
        rows = self.db_session.execute(
            select(trip_exchange_rates_table, users_table.c.display_name.label("updated_by_name"))
            .select_from(trip_exchange_rates_table.outerjoin(
                users_table, users_table.c.id == trip_exchange_rates_table.c.updated_by_user_id))
            .where(trip_exchange_rates_table.c.trip_id == trip["id"])
            .order_by(trip_exchange_rates_table.c.currency)
        ).mappings().all()
        rates = {row["currency"]: row for row in rows}
        usage = dict(self.db_session.execute(
            select(transactions_table.c.original_currency, func.count())
            .where(*self._expense_filter(trip["id"]), transactions_table.c.original_currency != base)
            .group_by(transactions_table.c.original_currency)
        ).all())
        entries = []
        for currency in sorted(SUPPORTED_CURRENCIES - {base}):
            row = rates.get(currency)
            default = DEFAULT_EXCHANGE_RATES.get((currency, base))
            entries.append({
                "currency": currency,
                "rate": format(row["rate"].normalize(), "f") if row else None,
                "default_rate": format(default, "f") if default is not None else None,
                "updated_at": row["updated_at"].isoformat() if row else None,
                "updated_by_name": row["updated_by_name"] if row else None,
                "recorded_expenses": usage.get(currency, 0),
            })
        history = self.db_session.execute(
            select(trip_exchange_rate_changes_table, users_table.c.display_name.label("changed_by_name"))
            .select_from(trip_exchange_rate_changes_table.outerjoin(
                users_table, users_table.c.id == trip_exchange_rate_changes_table.c.changed_by_user_id))
            .where(trip_exchange_rate_changes_table.c.trip_id == trip["id"])
            .order_by(trip_exchange_rate_changes_table.c.changed_at.desc()).limit(HISTORY_LIMIT)
        ).mappings().all()
        return {
            "base_currency": base,
            "is_owner": trip["owner_user_id"] == self.trips._parse_user_id(user_id),
            "locked": self._has_settlements(trip["id"]),
            "rates": entries,
            "history": [{
                "currency": row["currency"],
                "old_rate": format(row["old_rate"].normalize(), "f") if row["old_rate"] is not None else None,
                "new_rate": format(row["new_rate"].normalize(), "f"),
                "action": row["action"],
                "affected_count": row["affected_count"],
                "changed_by_name": row["changed_by_name"],
                "changed_at": row["changed_at"].isoformat(),
            } for row in history],
        }

    def _has_settlements(self, trip_id):
        return bool(self.db_session.execute(
            select(settlements_table.c.id).where(
                settlements_table.c.trip_id == trip_id, settlements_table.c.deleted_at.is_(None)).limit(1)
        ).first())

    @staticmethod
    def _expense_filter(trip_id):
        t = transactions_table
        return [t.c.trip_id == trip_id, t.c.deleted_at.is_(None), t.c.type == "expense"]

    # -- setting ---------------------------------------------------------------------------

    def _validated_currency(self, trip, currency):
        currency = str(currency or "").upper()
        if currency not in SUPPORTED_CURRENCIES or currency == trip["base_currency"]:
            raise ValueError("這個幣別不需要設定匯率")
        return currency

    def set_rate(self, user_id, trip_id, currency, rate):
        trip = self.trips._ensure_owner(user_id, trip_id)
        self.trips._lock_membership_trip(trip["id"])
        currency = self._validated_currency(trip, currency)
        new_rate = parse_rate(rate)
        table = trip_exchange_rates_table
        old = self.db_session.scalar(select(table.c.rate).where(
            table.c.trip_id == trip["id"], table.c.currency == currency))
        if old is not None and old == new_rate:
            return {"currency": currency, "rate": format(new_rate, "f"), "changed": False, "different_count": 0}
        owner = self.trips._parse_user_id(user_id)
        values = dict(rate=new_rate, updated_by_user_id=owner, updated_at=func.now())
        self.db_session.execute(insert(table).values(trip_id=trip["id"], currency=currency, **values)
                                .on_conflict_do_update(constraint="uq_trip_exchange_rates_trip_currency", set_=values))
        self._log(trip["id"], currency, old, new_rate, "set", 0, owner)
        return {"currency": currency, "rate": format(new_rate, "f"), "changed": True,
                "different_count": len(self._affected(trip, currency, new_rate))}

    def _log(self, trip_id, currency, old, new, action, affected, owner):
        self.db_session.execute(insert(trip_exchange_rate_changes_table).values(
            trip_id=trip_id, currency=currency, old_rate=old, new_rate=new, action=action,
            affected_count=affected, changed_by_user_id=owner))

    # -- re-applying to recorded expenses -----------------------------------------------------

    def _affected(self, trip, currency, rate, *, lock=False):
        t, c = transactions_table, categories_table
        query = (
            select(t, c.c.name.label("category_name"), accounts_table.c.currency.label("account_currency"))
            .select_from(t.join(c, c.c.id == t.c.category_id)
                         .outerjoin(accounts_table, accounts_table.c.id == t.c.account_id))
            .where(*self._expense_filter(trip["id"]), t.c.original_currency == currency,
                   t.c.base_currency == trip["base_currency"], t.c.exchange_rate != rate)
            .order_by(t.c.transaction_date, t.c.created_at)
        )
        # Only the expense rows are locked: the account join is read-only context.
        return self.db_session.execute(query.with_for_update(of=t) if lock else query).mappings().all()

    def _current_rate(self, trip, currency):
        rate = self.db_session.scalar(select(trip_exchange_rates_table.c.rate).where(
            trip_exchange_rates_table.c.trip_id == trip["id"], trip_exchange_rates_table.c.currency == currency))
        if rate is None:
            raise ValueError("請先設定這個幣別的旅行匯率")
        return rate

    def preview_apply(self, user_id, trip_id, currency):
        trip = self.trips._ensure_owner(user_id, trip_id)
        currency = self._validated_currency(trip, currency)
        rate = self._current_rate(trip, currency)
        rows = self._affected(trip, currency, rate)
        names = dict(self.db_session.execute(select(trip_members_table.c.id, trip_members_table.c.display_name)
                                             .where(trip_members_table.c.trip_id == trip["id"])).all())
        change = {}
        old_total = new_total = account_total = Decimal("0")
        account_count = 0
        for row in rows:
            new_converted = (row["original_amount"] * rate).quantize(MONEY)
            delta = new_converted - row["converted_amount"]
            old_total += row["converted_amount"]
            new_total += new_converted
            if row["paid_by_member_id"]:
                change[row["paid_by_member_id"]] = change.get(row["paid_by_member_id"], Decimal("0")) + delta
            for split in self.db_session.execute(select(transaction_splits_table).where(
                    transaction_splits_table.c.transaction_id == row["id"])).mappings():
                share_delta = (split["share_amount"] * rate).quantize(MONEY) - split["converted_share_amount"]
                change[split["trip_member_id"]] = change.get(split["trip_member_id"], Decimal("0")) - share_delta
            # A payer's own account in the base currency is booked at the converted amount.
            if row["account_id"] and row["account_currency"] == trip["base_currency"]:
                account_count += 1
                account_total += delta
        return {
            "currency": currency, "rate": format(rate.normalize(), "f"), "base_currency": trip["base_currency"],
            "count": len(rows), "locked": self._has_settlements(trip["id"]),
            "old_total": format(old_total, "f"), "new_total": format(new_total, "f"),
            "members": [{"member_id": str(member_id), "display_name": names.get(member_id, ""),
                         "change": format(amount.quantize(MONEY), "f")}
                        for member_id, amount in sorted(change.items(), key=lambda item: names.get(item[0], ""))
                        if amount != 0],
            "account_adjustment_count": account_count,
            "account_adjustment_total": format(account_total, "f"),
        }

    def apply_rate(self, user_id, trip_id, currency):
        """Re-save every recorded expense in this currency at the trip rate, or none of them."""
        trip = self.trips._ensure_owner(user_id, trip_id)
        self.trips._lock_membership_trip(trip["id"])
        currency = self._validated_currency(trip, currency)
        if self._has_settlements(trip["id"]):
            raise ValueError("這趟旅行已經有還款紀錄，不能再改動已記的支出匯率")
        rate = self._current_rate(trip, currency)
        rows = self._affected(trip, currency, rate, lock=True)
        for row in rows:
            self._resave(row, rate)
        owner = self.trips._parse_user_id(user_id)
        self._log(trip["id"], currency, None, rate, "apply", len(rows), owner)
        return {"currency": currency, "rate": format(rate.normalize(), "f"), "updated": len(rows)}

    def _resave(self, row, rate):
        splits = self.db_session.execute(select(transaction_splits_table).where(
            transaction_splits_table.c.transaction_id == row["id"])).mappings().all()
        custom = [s for s in splits if s["split_method"] == "custom"]
        # The edit runs as the person who recorded the expense, so their own account link stays valid.
        try:
            success, message = self._update(row, rate, splits, custom)
        except ValueError as error:
            raise ValueError(f"「{row['title']}」無法套用新匯率：{error}。整批都沒有變動。") from None
        if not success:
            raise ValueError(f"「{row['title']}」無法套用新匯率：{message}。整批都沒有變動。")

    def _update(self, row, rate, splits, custom):
        return self.budget.update_transaction(
            row["user_id"], row["id"], row["transaction_date"], row["title"], row["original_amount"], row["type"],
            row["category_name"], description=row["description"] or "",
            account_id=str(row["account_id"]) if row["account_id"] else None,
            paid_by_member_id=str(row["paid_by_member_id"]) if row["paid_by_member_id"] else None,
            merchant=row["merchant"], original_currency=row["original_currency"], exchange_rate=rate,
            timezone_name=row["timezone"],
            split_allocations=[{"trip_member_id": str(s["trip_member_id"]), "amount": str(s["share_amount"])}
                               for s in splits] if custom else None,
            split_member_ids=None if custom else [str(s["trip_member_id"]) for s in splits],
            review_status=row["review_status"],
        )
