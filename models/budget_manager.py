from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, insert, or_, select, update

from config import DEFAULT_CURRENCY
from .schema import (
    accounts_table,
    budgets_table,
    categories_table,
    settlements_table,
    transaction_splits_table,
    transactions_table,
    trip_members_table,
    trips_table,
    users_table,
)
from .trip_manager import TripManager


CATEGORY_ALIASES = {
    "收入": "other_income",
    "伙食": "food",
    "交通": "transport",
    "住宿": "lodging",
    "購物": "shopping",
    "娛樂": "entertainment",
    "醫療": "medical",
    "生活": "daily",
    "訂閱": "subscriptions",
    "手續費": "fees",
    "其他": "other",
}

MINOR_UNITS = {
    "TWD": 0,
    "JPY": 0,
    "KRW": 0,
    "USD": 2,
    "EUR": 2,
}

DEFAULT_EXCHANGE_RATES = {
    ("JPY", "TWD"): Decimal("0.22"),
    ("KRW", "TWD"): Decimal("0.023"),
    ("USD", "TWD"): Decimal("32"),
    ("EUR", "TWD"): Decimal("35"),
    ("TWD", "JPY"): Decimal("4.55"),
    ("TWD", "KRW"): Decimal("43.5"),
    ("TWD", "USD"): Decimal("0.031"),
    ("TWD", "EUR"): Decimal("0.029"),
    ("USD", "JPY"): Decimal("145"),
    ("JPY", "USD"): Decimal("0.0069"),
    ("EUR", "JPY"): Decimal("158"),
    ("JPY", "EUR"): Decimal("0.0063"),
    ("USD", "EUR"): Decimal("0.92"),
    ("EUR", "USD"): Decimal("1.09"),
    ("KRW", "JPY"): Decimal("0.11"),
    ("JPY", "KRW"): Decimal("9.1"),
}


class BudgetManager:
    """管理交易與預算。

    外部 API 目前仍保留舊欄位名稱，內部已改用新版 MVP schema。
    """

    def __init__(self, db_session):
        self.db_session = db_session

    def _parse_user_id(self, user_id):
        try:
            return UUID(str(user_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("user_id 格式不正確") from exc

    def _parse_date(self, value):
        if isinstance(value, date):
            return value
        return datetime.strptime(value, "%Y-%m-%d").date()

    def _month_range(self, month):
        start = datetime.strptime(month, "%Y-%m").date().replace(day=1)
        end = start.replace(day=monthrange(start.year, start.month)[1])
        return start, end

    def _normalize_amount(self, amount, field_name="金額"):
        parsed_amount = Decimal(str(amount))
        if parsed_amount <= 0:
            raise ValueError(f"{field_name}必須大於0")
        return parsed_amount

    def _parse_optional_uuid(self, value, field_name):
        if value in {None, ""}:
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} 格式不正確") from exc

    def _get_category_id(self, user_id, category_name, transaction_type):
        kind = "income" if transaction_type == "income" else "expense"
        normalized_code = CATEGORY_ALIASES.get(category_name, category_name)

        stmt = select(categories_table.c.id).where(
            categories_table.c.deleted_at.is_(None),
            categories_table.c.scope == "transaction",
            categories_table.c.kind.in_([kind, "both"]),
            or_(
                categories_table.c.user_id.is_(None),
                categories_table.c.user_id == user_id,
            ),
            or_(
                categories_table.c.code == normalized_code,
                categories_table.c.name == category_name,
            ),
        ).order_by(categories_table.c.user_id.isnot(None).desc())
        category_id = self.db_session.execute(stmt).scalar_one_or_none()
        if category_id:
            return category_id

        fallback_code = "other_income" if kind == "income" else "other"
        fallback_stmt = select(categories_table.c.id).where(
            categories_table.c.user_id.is_(None),
            categories_table.c.scope == "transaction",
            categories_table.c.kind == kind,
            categories_table.c.code == fallback_code,
        )
        fallback_id = self.db_session.execute(fallback_stmt).scalar_one_or_none()
        if not fallback_id:
            raise ValueError("找不到可用的交易類別，請確認 seed data 已建立")
        return fallback_id

    def _get_account_for_balance_update(self, user_id, account_id):
        parsed_account_id = self._parse_optional_uuid(account_id, "account_id")
        if not parsed_account_id:
            return None

        row = self.db_session.execute(
            select(accounts_table).where(
                accounts_table.c.id == parsed_account_id,
                accounts_table.c.user_id == user_id,
                accounts_table.c.deleted_at.is_(None),
            )
        ).first()
        if not row:
            raise ValueError("找不到付款帳戶或權限不足")
        return dict(row._mapping)

    def _resolve_account_delta_amount(self, account, original_amount, original_currency, converted_amount, base_currency):
        if account["currency"] == original_currency:
            return original_amount
        if account["currency"] == base_currency:
            return converted_amount
        raise ValueError("付款帳戶幣別必須與交易原幣或換算本幣相同")

    def _apply_account_balance_delta(self, account, delta):
        if not account or not account["track_balance"]:
            return

        new_balance = Decimal(str(account["balance"] or 0)) + Decimal(str(delta))
        if new_balance < 0:
            raise ValueError("帳戶餘額不足")

        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == account["id"])
            .values(balance=new_balance, updated_at=datetime.now(timezone.utc))
        )

    def _balance_delta_for_transaction(self, transaction_type, amount):
        if transaction_type == "expense":
            return -amount
        if transaction_type == "income":
            return amount
        return Decimal("0")

    def _default_exchange_rate(self, original_currency, base_currency):
        if original_currency == base_currency:
            return Decimal("1")
        return DEFAULT_EXCHANGE_RATES.get((original_currency, base_currency), Decimal("1"))

    def _monthly_report_scope(self):
        return or_(
            transactions_table.c.trip_id.is_(None),
            trips_table.c.include_in_monthly_report.is_(True),
        )

    def _accessible_trip_ids_for_user(self, user_id):
        return select(trip_members_table.c.trip_id).where(
            trip_members_table.c.user_id == user_id,
            trip_members_table.c.status == "active",
            trip_members_table.c.deleted_at.is_(None),
        )

    def _get_current_trip_member(self, user_id, trip_id):
        row = self.db_session.execute(
            select(trip_members_table).where(
                trip_members_table.c.trip_id == trip_id,
                trip_members_table.c.user_id == user_id,
                trip_members_table.c.status == "active",
                trip_members_table.c.deleted_at.is_(None),
            )
        ).first()
        return dict(row._mapping) if row else None

    def _can_manage_transaction(self, user_id, transaction):
        if not transaction["trip_id"]:
            return transaction["user_id"] == user_id

        trip = TripManager(self.db_session).get_trip(user_id, transaction["trip_id"])
        current_member = next((member for member in trip["members"] if member.get("user_id") == str(user_id)), None)
        if not current_member:
            return False
        if current_member["role"] == "owner":
            return True
        return current_member["role"] == "editor" and transaction["created_by_user_id"] == user_id

    def _can_create_trip_transaction(self, user_id, trip):
        current_member = next((member for member in trip["members"] if member.get("user_id") == str(user_id)), None)
        return bool(current_member and current_member["role"] in {"owner", "editor"})

    def get_all_transactions(
        self,
        user_id,
        trip_id=None,
        include_trips=False,
        monthly_report=False,
        limit=None,
        trip=None,
        current_trip_member=None,
    ):
        """獲取指定使用者的所有交易紀錄。"""
        parsed_user_id = self._parse_user_id(user_id)
        parsed_trip_id = self._parse_optional_uuid(trip_id, "trip_id")
        parsed_limit = None
        if limit is not None:
            try:
                parsed_limit = max(1, min(int(limit), 200))
            except (TypeError, ValueError):
                parsed_limit = None
        creator_users = users_table.alias("creator_users")
        stmt = (
            select(
                transactions_table.c.id,
                transactions_table.c.user_id,
                transactions_table.c.created_by_user_id,
                creator_users.c.display_name.label("created_by_display_name"),
                transactions_table.c.updated_by_user_id,
                transactions_table.c.deleted_by_user_id,
                transactions_table.c.review_status,
                transactions_table.c.transaction_date.label("date"),
                transactions_table.c.type,
                transactions_table.c.title.label("category"),
                categories_table.c.name.label("budget_category"),
                transactions_table.c.original_amount.label("amount"),
                transactions_table.c.description,
                transactions_table.c.merchant,
                transactions_table.c.original_currency.label("currency"),
                transactions_table.c.exchange_rate,
                transactions_table.c.converted_amount,
                transactions_table.c.base_currency,
                transactions_table.c.trip_id,
                transactions_table.c.paid_by_member_id,
                transactions_table.c.account_id,
                accounts_table.c.name.label("account_name"),
                accounts_table.c.currency.label("account_currency"),
            )
            .join(categories_table, transactions_table.c.category_id == categories_table.c.id)
            .join(creator_users, transactions_table.c.created_by_user_id == creator_users.c.id)
            .outerjoin(
                accounts_table,
                and_(
                    transactions_table.c.account_id == accounts_table.c.id,
                    accounts_table.c.user_id == parsed_user_id,
                ),
            )
            .where(transactions_table.c.deleted_at.is_(None))
            .order_by(transactions_table.c.transaction_date.desc(), transactions_table.c.created_at.desc())
        )
        if parsed_trip_id:
            if trip is None:
                TripManager(self.db_session).get_trip(parsed_user_id, parsed_trip_id)
            if current_trip_member is None:
                current_trip_member = self._get_current_trip_member(parsed_user_id, parsed_trip_id)
            stmt = stmt.where(transactions_table.c.trip_id == parsed_trip_id)
        elif monthly_report:
            member_trip_ids = self._accessible_trip_ids_for_user(parsed_user_id)
            stmt = (
                stmt.outerjoin(trips_table, transactions_table.c.trip_id == trips_table.c.id)
                .where(
                    or_(
                        and_(
                            transactions_table.c.trip_id.is_(None),
                            transactions_table.c.user_id == parsed_user_id,
                        ),
                        and_(
                            trips_table.c.include_in_monthly_report.is_(True),
                            or_(
                                trips_table.c.owner_user_id == parsed_user_id,
                                trips_table.c.id.in_(member_trip_ids),
                            ),
                        ),
                    )
                )
            )
        elif include_trips:
            member_trip_ids = self._accessible_trip_ids_for_user(parsed_user_id)
            stmt = (
                stmt.outerjoin(trips_table, transactions_table.c.trip_id == trips_table.c.id)
                .where(
                    or_(
                        and_(
                            transactions_table.c.trip_id.is_(None),
                            transactions_table.c.user_id == parsed_user_id,
                        ),
                        or_(
                            trips_table.c.owner_user_id == parsed_user_id,
                            trips_table.c.id.in_(member_trip_ids),
                        ),
                    )
                )
            )
        elif not include_trips:
            stmt = stmt.where(
                transactions_table.c.trip_id.is_(None),
                transactions_table.c.user_id == parsed_user_id,
            )
        if parsed_limit:
            stmt = stmt.limit(parsed_limit)

        result = self.db_session.execute(stmt)

        transactions = []
        for row in result:
            transaction = dict(row._mapping)
            transaction["id"] = str(transaction["id"])
            if parsed_trip_id and current_trip_member:
                can_manage = (
                    current_trip_member["role"] == "owner"
                    or (
                        current_trip_member["role"] == "editor"
                        and transaction["created_by_user_id"] == parsed_user_id
                    )
                )
            else:
                try:
                    can_manage = self._can_manage_transaction(parsed_user_id, transaction)
                except ValueError:
                    can_manage = False
            transaction["user_id"] = str(transaction["user_id"])
            transaction["created_by_user_id"] = str(transaction["created_by_user_id"])
            transaction["updated_by_user_id"] = str(transaction["updated_by_user_id"]) if transaction["updated_by_user_id"] else None
            transaction["deleted_by_user_id"] = str(transaction["deleted_by_user_id"]) if transaction["deleted_by_user_id"] else None
            transaction["date"] = transaction["date"].strftime("%Y-%m-%d")
            transaction["amount"] = float(transaction["amount"])
            transaction["exchange_rate"] = float(transaction["exchange_rate"])
            transaction["converted_amount"] = float(transaction["converted_amount"])
            transaction["trip_id"] = str(transaction["trip_id"]) if transaction["trip_id"] else None
            transaction["paid_by_member_id"] = (
                str(transaction["paid_by_member_id"]) if transaction["paid_by_member_id"] else None
            )
            transaction["account_id"] = str(transaction["account_id"]) if transaction["account_id"] else None
            transaction["can_edit"] = can_manage
            transaction["can_delete"] = can_manage
            transactions.append(transaction)
        return transactions

    def get_transaction_detail(self, user_id, transaction_id):
        """取得單筆交易明細與分帳資料。"""
        parsed_user_id = self._parse_user_id(user_id)
        parsed_transaction_id = self._parse_optional_uuid(transaction_id, "transaction_id")
        creator_users = users_table.alias("creator_users")
        row = self.db_session.execute(
            select(
                transactions_table.c.id,
                transactions_table.c.user_id,
                transactions_table.c.created_by_user_id,
                creator_users.c.display_name.label("created_by_display_name"),
                transactions_table.c.updated_by_user_id,
                transactions_table.c.deleted_by_user_id,
                transactions_table.c.trip_id,
                transactions_table.c.account_id,
                transactions_table.c.paid_by_member_id,
                transactions_table.c.transaction_date,
                transactions_table.c.transaction_time,
                transactions_table.c.timezone,
                transactions_table.c.type,
                transactions_table.c.merchant,
                transactions_table.c.title,
                transactions_table.c.description,
                transactions_table.c.original_amount,
                transactions_table.c.original_currency,
                transactions_table.c.exchange_rate,
                transactions_table.c.converted_amount,
                transactions_table.c.base_currency,
                transactions_table.c.review_status,
                categories_table.c.name.label("category_name"),
            )
            .join(categories_table, transactions_table.c.category_id == categories_table.c.id)
            .join(creator_users, transactions_table.c.created_by_user_id == creator_users.c.id)
            .where(
                transactions_table.c.id == parsed_transaction_id,
                transactions_table.c.deleted_at.is_(None),
            )
        ).first()
        if not row:
            raise ValueError("找不到交易或權限不足")

        transaction = dict(row._mapping)
        if transaction["user_id"] != parsed_user_id:
            if not transaction["trip_id"]:
                raise ValueError("找不到交易或權限不足")
            TripManager(self.db_session).get_trip(parsed_user_id, transaction["trip_id"])
        can_manage = self._can_manage_transaction(parsed_user_id, transaction)

        paid_by_member = None
        if transaction["paid_by_member_id"]:
            paid_by_member_row = self.db_session.execute(
                select(trip_members_table.c.id, trip_members_table.c.display_name).where(
                    trip_members_table.c.id == transaction["paid_by_member_id"]
                )
            ).first()
            if paid_by_member_row:
                paid_by_member = {
                    "id": str(paid_by_member_row.id),
                    "display_name": paid_by_member_row.display_name,
                }

        split_rows = self.db_session.execute(
            select(
                transaction_splits_table.c.id,
                transaction_splits_table.c.trip_member_id,
                trip_members_table.c.display_name,
                transaction_splits_table.c.split_method,
                transaction_splits_table.c.share_amount,
                transaction_splits_table.c.share_currency,
                transaction_splits_table.c.exchange_rate,
                transaction_splits_table.c.converted_share_amount,
                transaction_splits_table.c.base_currency,
            )
            .join(trip_members_table, transaction_splits_table.c.trip_member_id == trip_members_table.c.id)
            .where(transaction_splits_table.c.transaction_id == parsed_transaction_id)
            .order_by(trip_members_table.c.created_at)
        )
        splits = [
            {
                "id": str(split.id),
                "trip_member_id": str(split.trip_member_id),
                "display_name": split.display_name,
                "split_method": split.split_method,
                "share_amount": float(split.share_amount),
                "share_currency": split.share_currency,
                "exchange_rate": float(split.exchange_rate),
                "converted_share_amount": float(split.converted_share_amount),
                "base_currency": split.base_currency,
            }
            for split in split_rows
        ]

        return {
            "id": str(transaction["id"]),
            "user_id": str(transaction["user_id"]),
            "created_by_user_id": str(transaction["created_by_user_id"]),
            "created_by_display_name": transaction["created_by_display_name"],
            "updated_by_user_id": str(transaction["updated_by_user_id"]) if transaction["updated_by_user_id"] else None,
            "deleted_by_user_id": str(transaction["deleted_by_user_id"]) if transaction["deleted_by_user_id"] else None,
            "trip_id": str(transaction["trip_id"]) if transaction["trip_id"] else None,
            "account_id": str(transaction["account_id"]) if transaction["account_id"] else None,
            "paid_by_member_id": str(transaction["paid_by_member_id"]) if transaction["paid_by_member_id"] else None,
            "paid_by_member": paid_by_member,
            "date": transaction["transaction_date"].strftime("%Y-%m-%d"),
            "time": transaction["transaction_time"].isoformat() if transaction["transaction_time"] else None,
            "timezone": transaction["timezone"],
            "type": transaction["type"],
            "merchant": transaction["merchant"],
            "category": transaction["title"],
            "budget_category": transaction["category_name"],
            "description": transaction["description"],
            "amount": float(transaction["original_amount"]),
            "currency": transaction["original_currency"],
            "exchange_rate": float(transaction["exchange_rate"]),
            "converted_amount": float(transaction["converted_amount"]),
            "base_currency": transaction["base_currency"],
            "review_status": transaction["review_status"],
            "splits": splits,
            "can_edit": can_manage,
            "can_delete": can_manage,
        }

    def _resolve_trip_transaction_context(self, user_id, trip_id, paid_by_member_id):
        parsed_trip_id = self._parse_optional_uuid(trip_id, "trip_id")
        parsed_paid_by_member_id = self._parse_optional_uuid(paid_by_member_id, "paid_by_member_id")
        if not parsed_trip_id:
            if parsed_paid_by_member_id:
                raise ValueError("paid_by_member_id 必須搭配 trip_id")
            return None, None, None

        trip_manager = TripManager(self.db_session)
        trip = trip_manager.get_trip(user_id, parsed_trip_id)
        members = trip["members"]
        if parsed_paid_by_member_id:
            payer = next((member for member in members if member["id"] == str(parsed_paid_by_member_id)), None)
            if not payer:
                raise ValueError("付款旅伴不屬於此旅行")
        else:
            payer = next((member for member in members if member["user_id"] == str(self._parse_user_id(user_id))), None)
            if not payer:
                raise ValueError("找不到目前使用者在此旅行中的 member")
            parsed_paid_by_member_id = UUID(payer["id"])

        return parsed_trip_id, parsed_paid_by_member_id, trip

    def add_transaction(
        self,
        user_id,
        date,
        item,
        amount,
        transaction_type,
        budget_category,
        description="",
        account_id=None,
        trip_id=None,
        paid_by_member_id=None,
        merchant=None,
        original_currency=None,
        exchange_rate=None,
        timezone_name="Asia/Taipei",
        split_member_ids=None,
        split_allocations=None,
        review_status="confirmed",
    ):
        """新增一筆交易紀錄。"""
        self.last_created_transaction_id = None
        parsed_user_id = self._parse_user_id(user_id)
        parsed_amount = self._normalize_amount(amount)
        if transaction_type not in {"expense", "income"}:
            raise ValueError("交易類型僅支援 expense 或 income")
        if review_status not in {"pending", "confirmed"}:
            raise ValueError("review_status 僅支援 pending 或 confirmed")

        transaction_date = self._parse_date(date)
        category_id = self._get_category_id(parsed_user_id, budget_category, transaction_type)
        parsed_trip_id, parsed_paid_by_member_id, trip = self._resolve_trip_transaction_context(
            parsed_user_id,
            trip_id,
            paid_by_member_id,
        )
        if parsed_trip_id and not self._can_create_trip_transaction(parsed_user_id, trip):
            raise ValueError("目前角色不可新增旅行交易")
        transaction_currency = original_currency or (trip["default_currency"] if trip else DEFAULT_CURRENCY)
        base_currency = trip["base_currency"] if trip else DEFAULT_CURRENCY
        parsed_exchange_rate = Decimal(
            str(
                exchange_rate
                if exchange_rate is not None
                else self._default_exchange_rate(transaction_currency, base_currency)
            )
        )
        if parsed_exchange_rate <= 0:
            raise ValueError("exchange_rate 必須大於0")
        converted_amount = parsed_amount * parsed_exchange_rate
        if parsed_trip_id and account_id:
            payer = next(
                (member for member in trip["members"] if member["id"] == str(parsed_paid_by_member_id)),
                None,
            )
            if not payer or payer.get("user_id") != str(parsed_user_id):
                raise ValueError("只有自己付款時才可連動自己的帳戶")

        transaction_id = uuid4()

        with self.db_session.begin_nested():
            account = self._get_account_for_balance_update(parsed_user_id, account_id)
            parsed_account_id = account["id"] if account else None
            if account:
                account_amount = self._resolve_account_delta_amount(
                    account,
                    parsed_amount,
                    transaction_currency,
                    converted_amount,
                    base_currency,
                )
                self._apply_account_balance_delta(
                    account,
                    self._balance_delta_for_transaction(transaction_type, account_amount),
                )

            stmt = insert(transactions_table).values(
                id=transaction_id,
                user_id=parsed_user_id,
                created_by_user_id=parsed_user_id,
                updated_by_user_id=parsed_user_id,
                trip_id=parsed_trip_id,
                account_id=parsed_account_id,
                category_id=category_id,
                paid_by_member_id=parsed_paid_by_member_id,
                transaction_date=transaction_date,
                timezone=timezone_name,
                type=transaction_type,
                merchant=merchant,
                title=item,
                description=description,
                original_amount=parsed_amount,
                original_currency=transaction_currency,
                exchange_rate=parsed_exchange_rate,
                converted_amount=converted_amount,
                base_currency=base_currency,
                review_status=review_status,
            )
            self.db_session.execute(stmt)

            if parsed_trip_id and transaction_type == "expense":
                if split_allocations:
                    self.add_custom_splits(
                        transaction_id=transaction_id,
                        trip_id=parsed_trip_id,
                        split_allocations=split_allocations,
                        original_amount=parsed_amount,
                        original_currency=transaction_currency,
                        exchange_rate=parsed_exchange_rate,
                        base_currency=base_currency,
                    )
                elif split_member_ids:
                    self.add_equal_splits(
                        transaction_id=transaction_id,
                        trip_id=parsed_trip_id,
                        payer_member_id=parsed_paid_by_member_id,
                        split_member_ids=split_member_ids,
                        original_amount=parsed_amount,
                        original_currency=transaction_currency,
                        exchange_rate=parsed_exchange_rate,
                        base_currency=base_currency,
                    )

            self.last_created_transaction_id = transaction_id

        return True, "交易新增成功"

    def update_transaction(
        self,
        user_id,
        transaction_id,
        date,
        item,
        amount,
        transaction_type,
        budget_category,
        description="",
        account_id=None,
        paid_by_member_id=None,
        merchant=None,
        original_currency=None,
        exchange_rate=None,
        timezone_name="Asia/Taipei",
        split_member_ids=None,
        split_allocations=None,
        review_status="confirmed",
    ):
        """更新交易內容，並同步重算帳戶餘額與旅行分帳。"""
        parsed_user_id = self._parse_user_id(user_id)
        parsed_transaction_id = self._parse_optional_uuid(transaction_id, "transaction_id")
        parsed_amount = self._normalize_amount(amount)
        if transaction_type not in {"expense", "income"}:
            raise ValueError("交易類型僅支援 expense 或 income")
        if review_status not in {"pending", "confirmed"}:
            raise ValueError("review_status 僅支援 pending 或 confirmed")

        existing_row = self.db_session.execute(
            select(transactions_table).where(
                transactions_table.c.id == parsed_transaction_id,
                transactions_table.c.deleted_at.is_(None),
            )
        ).first()
        if not existing_row:
            raise ValueError("找不到要更新的交易或權限不足")

        existing = dict(existing_row._mapping)
        if not self._can_manage_transaction(parsed_user_id, existing):
            raise ValueError("目前角色不可編輯此交易")
        category_id = self._get_category_id(parsed_user_id, budget_category, transaction_type)
        parsed_trip_id = existing["trip_id"]
        parsed_paid_by_member_id, trip = None, None
        if parsed_trip_id:
            _, parsed_paid_by_member_id, trip = self._resolve_trip_transaction_context(
                parsed_user_id,
                parsed_trip_id,
                paid_by_member_id,
            )
        elif paid_by_member_id:
            raise ValueError("paid_by_member_id 必須搭配 trip_id")

        transaction_currency = original_currency or existing["original_currency"]
        base_currency = trip["base_currency"] if trip else existing["base_currency"]
        parsed_exchange_rate = Decimal(
            str(
                exchange_rate
                if exchange_rate is not None
                else self._default_exchange_rate(transaction_currency, base_currency)
            )
        )
        if parsed_exchange_rate <= 0:
            raise ValueError("exchange_rate 必須大於0")
        converted_amount = parsed_amount * parsed_exchange_rate

        if parsed_trip_id and account_id:
            payer = next(
                (member for member in trip["members"] if member["id"] == str(parsed_paid_by_member_id)),
                None,
            )
            if not payer or payer.get("user_id") != str(parsed_user_id):
                raise ValueError("只有自己付款時才可連動自己的帳戶")

        with self.db_session.begin_nested():
            old_account = self._get_account_for_balance_update(parsed_user_id, existing["account_id"])
            if old_account:
                old_account_amount = self._resolve_account_delta_amount(
                    old_account,
                    Decimal(str(existing["original_amount"])),
                    existing["original_currency"],
                    Decimal(str(existing["converted_amount"])),
                    existing["base_currency"],
                )
                self._apply_account_balance_delta(
                    old_account,
                    -self._balance_delta_for_transaction(existing["type"], old_account_amount),
                )

            new_account = self._get_account_for_balance_update(parsed_user_id, account_id)
            parsed_account_id = new_account["id"] if new_account else None
            if new_account:
                account_amount = self._resolve_account_delta_amount(
                    new_account,
                    parsed_amount,
                    transaction_currency,
                    converted_amount,
                    base_currency,
                )
                self._apply_account_balance_delta(
                    new_account,
                    self._balance_delta_for_transaction(transaction_type, account_amount),
                )

            self.db_session.execute(
                update(transactions_table)
                .where(transactions_table.c.id == parsed_transaction_id)
                .values(
                    account_id=parsed_account_id,
                    category_id=category_id,
                    paid_by_member_id=parsed_paid_by_member_id,
                    updated_by_user_id=parsed_user_id,
                    transaction_date=self._parse_date(date),
                    timezone=timezone_name,
                    type=transaction_type,
                    merchant=merchant,
                    title=item,
                    description=description,
                    original_amount=parsed_amount,
                    original_currency=transaction_currency,
                    exchange_rate=parsed_exchange_rate,
                    converted_amount=converted_amount,
                    base_currency=base_currency,
                    review_status=review_status,
                    updated_at=datetime.now(timezone.utc),
                )
            )

            self.db_session.execute(
                delete(transaction_splits_table).where(
                    transaction_splits_table.c.transaction_id == parsed_transaction_id
                )
            )
            if parsed_trip_id and transaction_type == "expense":
                if split_allocations:
                    self.add_custom_splits(
                        transaction_id=parsed_transaction_id,
                        trip_id=parsed_trip_id,
                        split_allocations=split_allocations,
                        original_amount=parsed_amount,
                        original_currency=transaction_currency,
                        exchange_rate=parsed_exchange_rate,
                        base_currency=base_currency,
                    )
                elif split_member_ids:
                    self.add_equal_splits(
                        transaction_id=parsed_transaction_id,
                        trip_id=parsed_trip_id,
                        payer_member_id=parsed_paid_by_member_id,
                        split_member_ids=split_member_ids,
                        original_amount=parsed_amount,
                        original_currency=transaction_currency,
                        exchange_rate=parsed_exchange_rate,
                        base_currency=base_currency,
                    )

        return True, "交易更新成功"

    def add_equal_splits(
        self,
        transaction_id,
        trip_id,
        payer_member_id,
        split_member_ids,
        original_amount,
        original_currency,
        exchange_rate,
        base_currency,
    ):
        """建立旅行交易的平均分帳。

        金額除不盡時，最小單位餘數會加到付款人身上。
        """
        member_ids = [self._parse_optional_uuid(member_id, "split_member_id") for member_id in split_member_ids]
        member_ids = list(dict.fromkeys(member_id for member_id in member_ids if member_id))
        if not member_ids:
            raise ValueError("split_member_ids 不可為空")
        if payer_member_id not in member_ids:
            member_ids.insert(0, payer_member_id)

        member_rows = self.db_session.execute(
            select(trip_members_table.c.id).where(
                trip_members_table.c.trip_id == trip_id,
                trip_members_table.c.id.in_(member_ids),
                trip_members_table.c.status == "active",
                trip_members_table.c.deleted_at.is_(None),
            )
        ).all()
        valid_member_ids = {row.id for row in member_rows}
        if valid_member_ids != set(member_ids):
            raise ValueError("分帳成員必須都屬於此旅行且狀態為 active")

        minor_unit = MINOR_UNITS.get(original_currency, 0)
        scale = Decimal("1").scaleb(-minor_unit)
        total_decimal_units = original_amount / scale
        if total_decimal_units != total_decimal_units.to_integral_value():
            raise ValueError("交易金額小數位超過幣別允許位數")
        total_units = int(total_decimal_units)
        base_share_units = total_units // len(member_ids)
        remainder_units = total_units % len(member_ids)

        split_rows = []
        for member_id in member_ids:
            share_units = base_share_units
            if member_id == payer_member_id:
                share_units += remainder_units
            share_amount = Decimal(share_units) * scale
            split_rows.append(
                {
                    "transaction_id": transaction_id,
                    "trip_member_id": member_id,
                    "split_method": "equal",
                    "share_amount": share_amount,
                    "share_currency": original_currency,
                    "exchange_rate": exchange_rate,
                    "converted_share_amount": share_amount * exchange_rate,
                    "base_currency": base_currency,
                }
            )

        self.db_session.execute(insert(transaction_splits_table), split_rows)

    def add_custom_splits(
        self,
        transaction_id,
        trip_id,
        split_allocations,
        original_amount,
        original_currency,
        exchange_rate,
        base_currency,
    ):
        """建立旅行交易的自訂分帳，輸入金額使用交易原幣。"""
        allocations = []
        for allocation in split_allocations:
            member_id = self._parse_optional_uuid(allocation.get("trip_member_id"), "trip_member_id")
            share_amount = Decimal(str(allocation.get("amount", "0")))
            if share_amount < 0:
                raise ValueError("分攤金額不可為負數")
            allocations.append({"member_id": member_id, "share_amount": share_amount})

        allocations = [allocation for allocation in allocations if allocation["member_id"] and allocation["share_amount"] > 0]
        if not allocations:
            raise ValueError("自訂分帳至少需要一位成員有分攤金額")

        member_ids = [allocation["member_id"] for allocation in allocations]
        if len(set(member_ids)) != len(member_ids):
            raise ValueError("自訂分帳成員不可重複")

        member_rows = self.db_session.execute(
            select(trip_members_table.c.id).where(
                trip_members_table.c.trip_id == trip_id,
                trip_members_table.c.id.in_(member_ids),
                trip_members_table.c.status == "active",
                trip_members_table.c.deleted_at.is_(None),
            )
        ).all()
        valid_member_ids = {row.id for row in member_rows}
        if valid_member_ids != set(member_ids):
            raise ValueError("分帳成員必須都屬於此旅行且狀態為 active")

        minor_unit = MINOR_UNITS.get(original_currency, 0)
        scale = Decimal("1").scaleb(-minor_unit)
        expected_units = self._amount_to_minor_units(original_amount, scale, "交易金額")
        allocation_units = [
            {
                "member_id": allocation["member_id"],
                "units": self._amount_to_minor_units(allocation["share_amount"], scale, "分攤金額"),
            }
            for allocation in allocations
        ]
        actual_units = sum(allocation["units"] for allocation in allocation_units)
        if actual_units != expected_units:
            diff_amount = Decimal(expected_units - actual_units) * scale
            raise ValueError(f"自訂分帳合計必須等於交易金額，目前差額為 {diff_amount}")

        split_rows = []
        for allocation in allocation_units:
            share_amount = Decimal(allocation["units"]) * scale
            split_rows.append(
                {
                    "transaction_id": transaction_id,
                    "trip_member_id": allocation["member_id"],
                    "split_method": "custom",
                    "share_amount": share_amount,
                    "share_currency": original_currency,
                    "exchange_rate": exchange_rate,
                    "converted_share_amount": share_amount * exchange_rate,
                    "base_currency": base_currency,
                }
            )

        self.db_session.execute(insert(transaction_splits_table), split_rows)

    def _amount_to_minor_units(self, amount, scale, field_name):
        decimal_units = amount / scale
        if decimal_units != decimal_units.to_integral_value():
            raise ValueError(f"{field_name}小數位超過幣別允許位數")
        return int(decimal_units)

    def get_trip_split_summary(self, user_id, trip_id, trip=None):
        """取得旅行分帳摘要。

        paid_amount 代表該成員付款總額，share_amount 代表該成員應分攤額，
        net_amount = paid_amount - share_amount。正數代表目前多付，負數代表少付。
        """
        parsed_user_id = self._parse_user_id(user_id)
        parsed_trip_id = self._parse_optional_uuid(trip_id, "trip_id")
        trip = trip if trip is not None else TripManager(self.db_session).get_trip(parsed_user_id, parsed_trip_id)

        summary = {
            member["id"]: {
                "member_id": member["id"],
                "display_name": member["display_name"],
                "paid_amount": Decimal("0"),
                "share_amount": Decimal("0"),
                "net_amount": Decimal("0"),
                "currency": trip["base_currency"],
            }
            for member in trip["members"]
        }

        payment_rows = self.db_session.execute(
            select(
                transactions_table.c.paid_by_member_id,
                func.sum(transactions_table.c.converted_amount).label("paid_amount"),
            )
            .where(
                transactions_table.c.trip_id == parsed_trip_id,
                transactions_table.c.type == "expense",
                transactions_table.c.deleted_at.is_(None),
                transactions_table.c.paid_by_member_id.isnot(None),
            )
            .group_by(transactions_table.c.paid_by_member_id)
        )
        for row in payment_rows:
            member_id = str(row.paid_by_member_id)
            if member_id in summary:
                summary[member_id]["paid_amount"] = row.paid_amount or Decimal("0")

        share_rows = self.db_session.execute(
            select(
                transaction_splits_table.c.trip_member_id,
                func.sum(transaction_splits_table.c.converted_share_amount).label("share_amount"),
            )
            .join(transactions_table, transaction_splits_table.c.transaction_id == transactions_table.c.id)
            .where(
                transactions_table.c.trip_id == parsed_trip_id,
                transactions_table.c.deleted_at.is_(None),
            )
            .group_by(transaction_splits_table.c.trip_member_id)
        )
        for row in share_rows:
            member_id = str(row.trip_member_id)
            if member_id in summary:
                summary[member_id]["share_amount"] = row.share_amount or Decimal("0")

        settlement_rows = self.db_session.execute(
            select(
                settlements_table.c.from_member_id,
                settlements_table.c.to_member_id,
                func.sum(settlements_table.c.amount).label("amount"),
            )
            .where(
                settlements_table.c.trip_id == parsed_trip_id,
                settlements_table.c.status == "confirmed",
                settlements_table.c.deleted_at.is_(None),
            )
            .group_by(settlements_table.c.from_member_id, settlements_table.c.to_member_id)
        )
        for row in settlement_rows:
            from_member_id = str(row.from_member_id)
            to_member_id = str(row.to_member_id)
            amount = row.amount or Decimal("0")
            if from_member_id in summary:
                summary[from_member_id]["net_amount"] += amount
            if to_member_id in summary:
                summary[to_member_id]["net_amount"] -= amount

        result = []
        for member_summary in summary.values():
            member_summary["net_amount"] += member_summary["paid_amount"] - member_summary["share_amount"]
            result.append(
                {
                    "member_id": member_summary["member_id"],
                    "display_name": member_summary["display_name"],
                    "paid_amount": float(member_summary["paid_amount"]),
                    "share_amount": float(member_summary["share_amount"]),
                    "net_amount": float(member_summary["net_amount"]),
                    "currency": member_summary["currency"],
                }
            )

        return sorted(result, key=lambda item: item["display_name"])

    def get_trip_settlement_suggestions(self, user_id, trip_id, summary=None):
        """依分帳淨額計算誰應該付誰多少，不寫入付款紀錄。"""
        parsed_user_id = self._parse_user_id(user_id)
        parsed_trip_id = self._parse_optional_uuid(trip_id, "trip_id")
        trip = TripManager(self.db_session).get_trip(parsed_user_id, parsed_trip_id)
        current_member = next((member for member in trip["members"] if member.get("user_id") == str(parsed_user_id)), None)
        summary = summary if summary is not None else self.get_trip_split_summary(user_id, trip_id)
        if not summary:
            return []

        currency = summary[0]["currency"]
        creditors = [
            {
                "member_id": item["member_id"],
                "display_name": item["display_name"],
                "amount": Decimal(str(item["net_amount"])),
            }
            for item in summary
            if Decimal(str(item["net_amount"])) > 0
        ]
        debtors = [
            {
                "member_id": item["member_id"],
                "display_name": item["display_name"],
                "amount": -Decimal(str(item["net_amount"])),
            }
            for item in summary
            if Decimal(str(item["net_amount"])) < 0
        ]

        suggestions = []
        debtor_index = 0
        creditor_index = 0
        while debtor_index < len(debtors) and creditor_index < len(creditors):
            debtor = debtors[debtor_index]
            creditor = creditors[creditor_index]
            amount = min(debtor["amount"], creditor["amount"])
            if amount > 0:
                suggestions.append(
                    {
                        "from_member_id": debtor["member_id"],
                        "from_display_name": debtor["display_name"],
                        "to_member_id": creditor["member_id"],
                        "to_display_name": creditor["display_name"],
                        "amount": float(amount),
                        "currency": currency,
                        "can_confirm": bool(
                            current_member
                            and (
                                current_member["role"] == "owner"
                                or current_member["id"] == debtor["member_id"]
                            )
                        ),
                    }
                )

            debtor["amount"] -= amount
            creditor["amount"] -= amount
            if debtor["amount"] == 0:
                debtor_index += 1
            if creditor["amount"] == 0:
                creditor_index += 1

        return suggestions

    def get_trip_settlements(self, user_id, trip_id):
        """列出旅行已確認的結算紀錄。"""
        parsed_user_id = self._parse_user_id(user_id)
        parsed_trip_id = self._parse_optional_uuid(trip_id, "trip_id")
        trip = TripManager(self.db_session).get_trip(parsed_user_id, parsed_trip_id)
        current_member = next((member for member in trip["members"] if member.get("user_id") == str(parsed_user_id)), None)

        rows = self.db_session.execute(
            select(
                settlements_table.c.id,
                settlements_table.c.from_member_id,
                settlements_table.c.to_member_id,
                settlements_table.c.amount,
                settlements_table.c.currency,
                settlements_table.c.note,
                settlements_table.c.settled_at,
                settlements_table.c.recorded_by_user_id,
                trip_members_table.c.display_name.label("from_display_name"),
            )
            .join(trip_members_table, settlements_table.c.from_member_id == trip_members_table.c.id)
            .where(
                settlements_table.c.trip_id == parsed_trip_id,
                settlements_table.c.status == "confirmed",
                settlements_table.c.deleted_at.is_(None),
            )
            .order_by(settlements_table.c.settled_at.desc(), settlements_table.c.created_at.desc())
        ).all()

        to_member_names = {
            row.id: row.display_name
            for row in self.db_session.execute(
                select(trip_members_table.c.id, trip_members_table.c.display_name).where(
                    trip_members_table.c.trip_id == parsed_trip_id,
                    trip_members_table.c.deleted_at.is_(None),
                )
            )
        }

        settlements = []
        for row in rows:
            settlements.append(
                {
                    "id": str(row.id),
                    "from_member_id": str(row.from_member_id),
                    "from_display_name": row.from_display_name,
                    "to_member_id": str(row.to_member_id),
                    "to_display_name": to_member_names.get(row.to_member_id, "未知成員"),
                    "amount": float(row.amount),
                    "currency": row.currency,
                    "note": row.note,
                    "settled_at": row.settled_at.isoformat() if row.settled_at else None,
                    "can_void": bool(
                        current_member
                        and (
                            current_member["role"] == "owner"
                            or row.recorded_by_user_id == parsed_user_id
                        )
                    ),
                }
            )
        return settlements

    def add_trip_settlement(self, user_id, trip_id, from_member_id, to_member_id, amount, note=None):
        """確認一筆旅行分帳還款，不異動任何付款帳戶餘額。"""
        parsed_user_id = self._parse_user_id(user_id)
        parsed_trip_id = self._parse_optional_uuid(trip_id, "trip_id")
        parsed_from_member_id = self._parse_optional_uuid(from_member_id, "from_member_id")
        parsed_to_member_id = self._parse_optional_uuid(to_member_id, "to_member_id")
        settlement_amount = self._normalize_amount(amount, "結算金額")

        if parsed_from_member_id == parsed_to_member_id:
            raise ValueError("付款人與收款人不可相同")

        trip = TripManager(self.db_session).get_trip(parsed_user_id, parsed_trip_id)
        member_ids = {UUID(member["id"]) for member in trip["members"]}
        if parsed_from_member_id not in member_ids or parsed_to_member_id not in member_ids:
            raise ValueError("結算成員不屬於此旅行")
        current_member = next((member for member in trip["members"] if member.get("user_id") == str(parsed_user_id)), None)
        can_confirm = current_member and (
            current_member["role"] == "owner" or current_member["id"] == str(parsed_from_member_id)
        )
        if not can_confirm:
            raise ValueError("只有旅行 owner 或付款方本人可以確認這筆結算")

        current_suggestion = next(
            (
                suggestion
                for suggestion in self.get_trip_settlement_suggestions(parsed_user_id, parsed_trip_id)
                if suggestion["from_member_id"] == str(parsed_from_member_id)
                and suggestion["to_member_id"] == str(parsed_to_member_id)
            ),
            None,
        )
        if not current_suggestion:
            raise ValueError("目前沒有這筆待結算建議")
        if settlement_amount > Decimal(str(current_suggestion["amount"])):
            raise ValueError("結算金額不可超過目前建議金額")

        self.db_session.execute(
            insert(settlements_table).values(
                trip_id=parsed_trip_id,
                from_member_id=parsed_from_member_id,
                to_member_id=parsed_to_member_id,
                recorded_by_user_id=parsed_user_id,
                amount=settlement_amount,
                currency=trip["base_currency"],
                status="confirmed",
                note=note,
                settled_at=datetime.now(timezone.utc),
            )
        )
        return True, "結算已確認"

    def delete_trip_settlement(self, user_id, trip_id, settlement_id):
        """撤銷一筆旅行結算紀錄。"""
        parsed_user_id = self._parse_user_id(user_id)
        parsed_trip_id = self._parse_optional_uuid(trip_id, "trip_id")
        parsed_settlement_id = self._parse_optional_uuid(settlement_id, "settlement_id")
        trip = TripManager(self.db_session).get_trip(parsed_user_id, parsed_trip_id)
        current_member = next((member for member in trip["members"] if member.get("user_id") == str(parsed_user_id)), None)

        settlement_row = self.db_session.execute(
            select(settlements_table.c.recorded_by_user_id).where(
                settlements_table.c.id == parsed_settlement_id,
                settlements_table.c.trip_id == parsed_trip_id,
                settlements_table.c.status == "confirmed",
                settlements_table.c.deleted_at.is_(None),
            )
        ).first()
        if not settlement_row:
            raise ValueError("找不到要撤銷的結算紀錄")
        can_void = current_member and (
            current_member["role"] == "owner" or settlement_row.recorded_by_user_id == parsed_user_id
        )
        if not can_void:
            raise ValueError("只有旅行 owner 或結算記錄者可以撤銷這筆結算")

        now = datetime.now(timezone.utc)
        result = self.db_session.execute(
            update(settlements_table)
            .where(
                settlements_table.c.id == parsed_settlement_id,
                settlements_table.c.trip_id == parsed_trip_id,
                settlements_table.c.status == "confirmed",
                settlements_table.c.deleted_at.is_(None),
            )
            .values(status="voided", deleted_at=now, purge_after=now + timedelta(days=30), updated_at=now)
        )
        if result.rowcount == 0:
            raise ValueError("找不到要撤銷的結算紀錄")
        return True, "結算已撤銷"

    def delete_transaction(self, user_id, transaction_id):
        """兩段式刪除一筆交易。"""
        parsed_user_id = self._parse_user_id(user_id)
        try:
            parsed_transaction_id = UUID(str(transaction_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("transaction_id 格式不正確") from exc

        transaction = self.db_session.execute(
            select(
                transactions_table.c.id,
                transactions_table.c.user_id,
                transactions_table.c.created_by_user_id,
                transactions_table.c.trip_id,
                transactions_table.c.account_id,
                transactions_table.c.type,
                transactions_table.c.original_amount,
                transactions_table.c.original_currency,
                transactions_table.c.converted_amount,
                transactions_table.c.base_currency,
            ).where(
                transactions_table.c.id == parsed_transaction_id,
                transactions_table.c.deleted_at.is_(None),
            )
        ).first()
        if not transaction:
            raise ValueError("找不到要刪除的交易或權限不足")

        transaction_data = dict(transaction._mapping)
        if not self._can_manage_transaction(parsed_user_id, transaction_data):
            raise ValueError("目前角色不可刪除此交易")

        account = self._get_account_for_balance_update(parsed_user_id, transaction_data["account_id"])
        if account:
            account_amount = self._resolve_account_delta_amount(
                account,
                Decimal(str(transaction_data["original_amount"])),
                transaction_data["original_currency"],
                Decimal(str(transaction_data["converted_amount"])),
                transaction_data["base_currency"],
            )
            self._apply_account_balance_delta(
                account,
                -self._balance_delta_for_transaction(transaction_data["type"], account_amount),
            )

        now = datetime.now(timezone.utc)
        stmt = (
            update(transactions_table)
            .where(
                transactions_table.c.id == parsed_transaction_id,
                transactions_table.c.deleted_at.is_(None),
            )
            .values(
                deleted_by_user_id=parsed_user_id,
                deleted_at=now,
                purge_after=now + timedelta(days=30),
                updated_at=now,
            )
        )
        result = self.db_session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError("找不到要刪除的交易或權限不足")
        return True, "交易刪除成功"

    def get_all_transaction_months(self, user_id):
        """從交易與預算中提取所有唯一月份。"""
        parsed_user_id = self._parse_user_id(user_id)
        transaction_month = func.to_char(transactions_table.c.transaction_date, "YYYY-MM")
        budget_month = func.to_char(budgets_table.c.period_start, "YYYY-MM")

        transaction_months = self.db_session.execute(
            select(transaction_month).where(
                transactions_table.c.user_id == parsed_user_id,
                transactions_table.c.trip_id.is_(None),
                transactions_table.c.deleted_at.is_(None),
            )
        )
        budget_months = self.db_session.execute(
            select(budget_month).where(
                budgets_table.c.user_id == parsed_user_id,
                budgets_table.c.scope == "monthly",
                budgets_table.c.trip_id.is_(None),
                budgets_table.c.deleted_at.is_(None),
            )
        )
        months = {row[0] for row in transaction_months} | {row[0] for row in budget_months}
        return sorted(months, reverse=True)

    def set_budget(self, user_id, month, category, amount, notes=""):
        """設定某位使用者在某月某類別的預算。"""
        parsed_user_id = self._parse_user_id(user_id)
        parsed_amount = self._normalize_amount(amount, "預算金額")
        period_start, period_end = self._month_range(month)
        category_id = self._get_category_id(parsed_user_id, category, "expense")

        existing_stmt = select(budgets_table.c.id).where(
            budgets_table.c.user_id == parsed_user_id,
            budgets_table.c.scope == "monthly",
            budgets_table.c.trip_id.is_(None),
            budgets_table.c.category_id == category_id,
            budgets_table.c.period_start == period_start,
            budgets_table.c.period_end == period_end,
            budgets_table.c.deleted_at.is_(None),
        )
        budget_id = self.db_session.execute(existing_stmt).scalar_one_or_none()
        if budget_id:
            self.db_session.execute(
                update(budgets_table)
                .where(budgets_table.c.id == budget_id)
                .values(amount=parsed_amount, notes=notes, updated_at=datetime.now(timezone.utc))
            )
        else:
            self.db_session.execute(
                insert(budgets_table).values(
                    user_id=parsed_user_id,
                    scope="monthly",
                    period_start=period_start,
                    period_end=period_end,
                    category_id=category_id,
                    amount=parsed_amount,
                    currency=DEFAULT_CURRENCY,
                    notes=notes,
                )
            )

        return True, "預算設定成功"

    def delete_budget(self, user_id, month, category):
        """兩段式刪除某位使用者在某月某類別的預算。"""
        parsed_user_id = self._parse_user_id(user_id)
        period_start, period_end = self._month_range(month)
        category_id = self._get_category_id(parsed_user_id, category, "expense")
        now = datetime.now(timezone.utc)

        stmt = (
            update(budgets_table)
            .where(
                budgets_table.c.user_id == parsed_user_id,
                budgets_table.c.scope == "monthly",
                budgets_table.c.trip_id.is_(None),
                budgets_table.c.category_id == category_id,
                budgets_table.c.period_start == period_start,
                budgets_table.c.period_end == period_end,
                budgets_table.c.deleted_at.is_(None),
            )
            .values(deleted_at=now, purge_after=now + timedelta(days=30), updated_at=now)
        )
        result = self.db_session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError("找不到要刪除的預算或權限不足")
        return True, "預算刪除成功"

    def get_all_budget_categories(self, user_id, include_meta=False):
        """獲取可用交易類別。"""
        parsed_user_id = self._parse_user_id(user_id)
        columns = [
            categories_table.c.name,
            categories_table.c.kind,
            categories_table.c.code,
        ] if include_meta else [categories_table.c.name]
        stmt = (
            select(*columns)
            .where(
                categories_table.c.deleted_at.is_(None),
                categories_table.c.scope == "transaction",
                categories_table.c.kind.in_(["expense", "income", "both"]),
                or_(categories_table.c.user_id.is_(None), categories_table.c.user_id == parsed_user_id),
            )
            .order_by(categories_table.c.kind, categories_table.c.sort_order, categories_table.c.name)
        )
        if include_meta:
            return [
                {"name": row.name, "kind": row.kind, "code": row.code}
                for row in self.db_session.execute(stmt)
            ]
        return [row[0] for row in self.db_session.execute(stmt)]

    def calculate_monthly_expenses(self, user_id, year_month):
        """彙總指定使用者在某月的日常支出，用於預算消耗。"""
        parsed_user_id = self._parse_user_id(user_id)
        period_start, period_end = self._month_range(year_month)
        stmt = (
            select(categories_table.c.name, func.sum(transactions_table.c.converted_amount).label("total_spent"))
            .join(categories_table, transactions_table.c.category_id == categories_table.c.id)
            .where(
                transactions_table.c.user_id == parsed_user_id,
                transactions_table.c.trip_id.is_(None),
                transactions_table.c.type == "expense",
                transactions_table.c.deleted_at.is_(None),
                transactions_table.c.transaction_date >= period_start,
                transactions_table.c.transaction_date <= period_end,
            )
            .group_by(categories_table.c.name)
        )
        result = self.db_session.execute(stmt)
        return {row.name: row.total_spent for row in result}

    def calculate_monthly_report_expenses(self, user_id, year_month):
        """彙總月報支出：日常支出 + 勾選併入月報的旅行支出。"""
        parsed_user_id = self._parse_user_id(user_id)
        period_start, period_end = self._month_range(year_month)
        stmt = (
            select(categories_table.c.name, func.sum(transactions_table.c.converted_amount).label("total_spent"))
            .join(categories_table, transactions_table.c.category_id == categories_table.c.id)
            .outerjoin(trips_table, transactions_table.c.trip_id == trips_table.c.id)
            .where(
                transactions_table.c.user_id == parsed_user_id,
                transactions_table.c.type == "expense",
                transactions_table.c.deleted_at.is_(None),
                transactions_table.c.transaction_date >= period_start,
                transactions_table.c.transaction_date <= period_end,
                self._monthly_report_scope(),
            )
            .group_by(categories_table.c.name)
        )
        result = self.db_session.execute(stmt)
        return {row.name: row.total_spent for row in result}

    def get_budget_summary(self, user_id, month):
        """取得某月預算、已花費、剩餘金額。"""
        parsed_user_id = self._parse_user_id(user_id)
        period_start, period_end = self._month_range(month)
        budget_stmt = (
            select(categories_table.c.name, budgets_table.c.amount, budgets_table.c.notes)
            .join(categories_table, budgets_table.c.category_id == categories_table.c.id)
            .where(
                budgets_table.c.user_id == parsed_user_id,
                budgets_table.c.scope == "monthly",
                budgets_table.c.trip_id.is_(None),
                budgets_table.c.period_start == period_start,
                budgets_table.c.period_end == period_end,
                budgets_table.c.deleted_at.is_(None),
            )
        )
        budgets = {
            row.name: {"budget": row.amount, "notes": row.notes}
            for row in self.db_session.execute(budget_stmt)
        }
        expenses = self.calculate_monthly_expenses(parsed_user_id, month)

        response_data = []
        for category in sorted(set(expenses.keys()) | set(budgets.keys())):
            spent = expenses.get(category, Decimal("0"))
            budget = budgets.get(category, {}).get("budget")
            remaining = budget - spent if budget is not None else None
            response_data.append(
                {
                    "category": category,
                    "spent": float(spent),
                    "budget": float(budget) if budget is not None else None,
                    "remaining": float(remaining) if remaining is not None else None,
                    "notes": budgets.get(category, {}).get("notes"),
                }
            )
        return response_data

    def get_transactions_by_category_over_time(self, user_id, interval="month"):
        """按時間間隔和類別彙總月報支出數據。"""
        parsed_user_id = self._parse_user_id(user_id)
        time_format = "YYYY-MM" if interval == "month" else "YYYY"
        time_period = func.to_char(transactions_table.c.transaction_date, time_format).label("time_period")

        stmt = (
            select(
                time_period,
                categories_table.c.name.label("category"),
                func.sum(transactions_table.c.converted_amount).label("total_spent"),
            )
            .join(categories_table, transactions_table.c.category_id == categories_table.c.id)
            .outerjoin(trips_table, transactions_table.c.trip_id == trips_table.c.id)
            .where(
                transactions_table.c.user_id == parsed_user_id,
                transactions_table.c.type == "expense",
                transactions_table.c.deleted_at.is_(None),
                self._monthly_report_scope(),
            )
            .group_by(time_period, categories_table.c.name)
            .order_by(time_period.asc(), categories_table.c.name.asc())
        )

        data = {}
        for row in self.db_session.execute(stmt):
            period, category, spent = row.time_period, row.category, float(row.total_spent)
            data.setdefault(period, {})[category] = spent

        if not data:
            return {"labels": [], "datasets": []}

        labels = sorted(data.keys())
        all_categories = sorted({cat for period_data in data.values() for cat in period_data})
        colors = ["#42A5F5", "#66BB6A", "#FFA726", "#26A69A", "#BDBDBD", "#7986CB", "#C0CA33", "#FF7043", "#8D6E63", "#EC407A"]
        datasets = [
            {
                "label": category,
                "data": [data[label].get(category, 0) for label in labels],
                "backgroundColor": colors[i % len(colors)],
            }
            for i, category in enumerate(all_categories)
        ]
        return {"labels": labels, "datasets": datasets}

    def check_over_warnings(self, user_id, month=None):
        """檢查指定使用者的超支警告。"""
        months = [month] if month else self.get_all_transaction_months(user_id)
        warnings = []
        for target_month in months:
            for item in self.get_budget_summary(user_id, target_month):
                if item["budget"] is not None and item["spent"] > item["budget"]:
                    warnings.append(
                        {
                            "month": target_month,
                            "category": item["category"],
                            "budget": item["budget"],
                            "spent": item["spent"],
                            "overspend": item["spent"] - item["budget"],
                        }
                    )
        return warnings
