import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, insert, or_, select, update

from config import DEFAULT_CURRENCY
from .schema import accounts_table, categories_table, transactions_table, transfers_table


ACCOUNT_TYPE_ALIASES = {
    "cash": "cash",
    "現金": "cash",
    "bank": "bank",
    "銀行": "bank",
    "活存": "bank",
    "定存": "bank",
    "credit_card": "credit_card",
    "信用卡": "credit_card",
    "e_wallet": "e_wallet",
    "電子錢包": "e_wallet",
    "prepaid_card": "prepaid_card",
    "external": "external",
    "investment": "investment",
    "投資": "investment",
    "券商": "investment",
    "定期定額": "investment",
    "other": "other",
    "其他": "other",
}

SUPPORTED_CURRENCIES = {"TWD", "JPY", "KRW", "USD", "EUR"}
ACCOUNT_TYPE_LABELS = {
    "cash": "現金",
    "bank": "銀行",
    "credit_card": "信用卡",
    "e_wallet": "電子錢包",
    "prepaid_card": "預付卡",
    "external": "外部帳戶",
    "investment": "投資",
    "other": "其他",
}
GENERIC_ACCOUNT_WORDS = [
    "信用卡",
    "銀行",
    "帳戶",
    "活存",
    "定存",
    "現金",
    "電子錢包",
    "錢包",
    "預付卡",
    "投資",
    "券商",
    "卡",
]


class AssetManager:
    """管理付款帳戶。

    API 目前仍沿用 assets 命名，底層已切換到新版 accounts schema。
    """

    def __init__(self, db_session):
        self.db_session = db_session

    def _normalize_account_type(self, account_type):
        return ACCOUNT_TYPE_ALIASES.get(str(account_type).strip(), "other")

    def _normalize_currency(self, currency):
        normalized_currency = str(currency or DEFAULT_CURRENCY).strip().upper()
        if normalized_currency not in SUPPORTED_CURRENCIES:
            raise ValueError("不支援的帳戶幣別")
        return normalized_currency

    def _allows_negative_balance(self, account_or_type):
        account_type = account_or_type.get("type") if isinstance(account_or_type, dict) else account_or_type
        return account_type == "credit_card"

    def _parse_uuid(self, value, field_name="account_id"):
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} 格式不正確") from exc

    def _parse_user_id(self, user_id):
        return self._parse_uuid(user_id, "user_id")

    def _get_account(self, user_id, account_id):
        stmt = select(accounts_table).where(
            accounts_table.c.user_id == self._parse_user_id(user_id),
            accounts_table.c.id == self._parse_uuid(account_id),
            accounts_table.c.deleted_at.is_(None),
        )
        row = self.db_session.execute(stmt).first()
        return dict(row._mapping) if row else None

    def _to_legacy_asset(self, account):
        """暫時轉成前端既有 assets 格式，等前端改名後可移除。"""
        account_id = str(account["id"])
        balance = account["balance"]
        return {
            "id": account_id,
            "account_key": account_id,
            "bank_name": account["name"],
            "account_type": account["type"],
            "balance": float(balance) if balance is not None else 0,
            "currency": account["currency"],
            "track_balance": account["track_balance"],
            "is_active": account["is_active"],
            "last_update": account["updated_at"].isoformat() if account["updated_at"] else None,
            "user_id": str(account["user_id"]),
        }

    def get_all_assets(self, user_id):
        """取得指定使用者的所有未刪除帳戶。"""
        stmt = (
            select(accounts_table)
            .where(
                accounts_table.c.user_id == self._parse_user_id(user_id),
                accounts_table.c.deleted_at.is_(None),
            )
            .order_by(accounts_table.c.created_at)
        )
        result = self.db_session.execute(stmt)
        assets = {}
        for row in result:
            asset = self._to_legacy_asset(dict(row._mapping))
            assets[asset["account_key"]] = asset
        return assets

    def find_asset_by_name(self, user_id, name, currency=None, context_text=None):
        """根據自然語言名稱尋找指定使用者的帳戶。

        多帳戶情境下避免用「信用卡」這類泛稱直接抓第一筆；只有有明確名稱、
        關鍵字或唯一類型帳戶時才回傳，避免 LINE 記帳扣到錯誤帳戶。
        """
        normalized_hint = self._normalize_account_search_text(name)
        if not normalized_hint:
            return None

        stmt = select(accounts_table).where(
            accounts_table.c.user_id == self._parse_user_id(user_id),
            accounts_table.c.deleted_at.is_(None),
        )
        if currency:
            stmt = stmt.where(accounts_table.c.currency == self._normalize_currency(currency))
        rows = [dict(row._mapping) for row in self.db_session.execute(stmt)]
        if not rows:
            return None

        scored_accounts = [
            (self._score_account_match(account, normalized_hint, context_text), account)
            for account in rows
        ]
        scored_accounts = [
            (score, account)
            for score, account in scored_accounts
            if score > 0
        ]
        if not scored_accounts:
            return None

        scored_accounts.sort(key=lambda item: item[0], reverse=True)
        top_score, top_account = scored_accounts[0]
        if len(scored_accounts) > 1 and scored_accounts[1][0] == top_score:
            return None
        return self._to_legacy_asset(top_account)

    def _score_account_match(self, account, normalized_hint, context_text=None):
        normalized_name = self._normalize_account_search_text(account["name"])
        if not normalized_name:
            return 0

        type_hint = self._detect_account_type_hint(normalized_hint)
        meaningful_hint = self._meaningful_account_token(normalized_hint)
        normalized_context = self._normalize_account_search_text(context_text)

        score = 0
        if meaningful_hint:
            if normalized_name == normalized_hint:
                score += 120
            elif normalized_hint in normalized_name:
                score += 90
            elif normalized_name in normalized_hint:
                score += 80

            if meaningful_hint in normalized_name:
                score += 70

        if normalized_context and normalized_name in normalized_context:
            score += 65

        if type_hint and account["type"] == type_hint:
            score += 20

        if not meaningful_hint and type_hint and account["type"] != type_hint:
            return 0
        if not meaningful_hint and type_hint and account["type"] == type_hint:
            return score or 10
        return score

    def _normalize_account_search_text(self, value):
        normalized = str(value or "").strip().lower()
        normalized = re.sub(r"\s+", "", normalized)
        return normalized

    def _meaningful_account_token(self, normalized_value):
        token = normalized_value
        for word in GENERIC_ACCOUNT_WORDS:
            token = token.replace(word.lower(), "")
        return token

    def _detect_account_type_hint(self, normalized_value):
        for account_type, label in ACCOUNT_TYPE_LABELS.items():
            normalized_label = self._normalize_account_search_text(label)
            if normalized_label and normalized_label in normalized_value:
                return account_type
        if "刷卡" in normalized_value:
            return "credit_card"
        return None

    def add_account(self, user_id, bank_name, account_type, balance, currency=None):
        """新增帳戶。"""
        normalized_type = self._normalize_account_type(account_type)
        account_balance = Decimal(str(balance))
        if account_balance < 0 and not self._allows_negative_balance(normalized_type):
            return False, "餘額不能為負數"

        stmt = insert(accounts_table).values(
            user_id=self._parse_user_id(user_id),
            name=bank_name,
            type=normalized_type,
            currency=self._normalize_currency(currency),
            track_balance=True,
            balance=account_balance,
        )
        self.db_session.execute(stmt)
        return True, "成功新增帳戶"

    def adjust_asset_balance(self, user_id, account_key, amount_change):
        """調整指定帳戶餘額。"""
        account = self._get_account(user_id, account_key)
        if not account:
            raise ValueError("找不到此帳戶或權限不足")
        if not account["track_balance"]:
            raise ValueError("此帳戶未啟用餘額追蹤")

        new_balance = Decimal(str(account["balance"])) + Decimal(str(amount_change))
        if new_balance < 0 and not self._allows_negative_balance(account):
            raise ValueError("餘額不能為負數")

        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == account["id"])
            .values(balance=new_balance, updated_at=datetime.now(timezone.utc))
        )
        return True, "餘額調整成功"

    def update_balance(self, user_id, account_key, new_balance):
        """更新指定帳戶餘額。"""
        account = self._get_account(user_id, account_key)
        if not account:
            raise ValueError("找不到此帳戶或權限不足")
        if not account["track_balance"]:
            raise ValueError("此帳戶未啟用餘額追蹤")

        parsed_balance = Decimal(str(new_balance))
        if parsed_balance < 0 and not self._allows_negative_balance(account):
            return False, "餘額不能為負數"

        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == account["id"])
            .values(balance=parsed_balance, updated_at=datetime.now(timezone.utc))
        )
        return True, "餘額更新成功"

    def update_account(self, user_id, account_key, **changes):
        """更新帳戶基本資料。"""
        account = self._get_account(user_id, account_key)
        if not account:
            raise ValueError("找不到此帳戶或權限不足")

        values = {}
        if "bank_name" in changes:
            bank_name = str(changes.get("bank_name") or "").strip()
            if not bank_name:
                return False, "帳戶名稱不能為空"
            if len(bank_name) > 100:
                return False, "帳戶名稱不能超過100字"
            values["name"] = bank_name

        if "account_type" in changes:
            values["type"] = self._normalize_account_type(changes.get("account_type"))

        if "currency" in changes:
            values["currency"] = self._normalize_currency(changes.get("currency"))

        balance_value = changes.get("balance", changes.get("new_balance"))
        if "balance" in changes or "new_balance" in changes:
            if not account["track_balance"]:
                raise ValueError("此帳戶未啟用餘額追蹤")
            parsed_balance = Decimal(str(balance_value))
            effective_type = values.get("type", account["type"])
            if parsed_balance < 0 and not self._allows_negative_balance(effective_type):
                return False, "餘額不能為負數"
            values["balance"] = parsed_balance

        if not values:
            return False, "沒有可更新的欄位"

        values["updated_at"] = datetime.now(timezone.utc)
        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == account["id"])
            .values(**values)
        )
        return True, "帳戶更新成功"

    def delete_account(self, user_id, account_key):
        """兩段式刪除帳戶。"""
        account = self._get_account(user_id, account_key)
        if not account:
            raise ValueError("找不到要刪除的帳戶或權限不足")

        now = datetime.now(timezone.utc)
        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == account["id"])
            .values(
                is_active=False,
                deleted_at=now,
                purge_after=now + timedelta(days=30),
                updated_at=now,
            )
        )
        return True, "成功刪除帳戶"

    def transfer(self, user_id, source_key, dest_key, amount, note=None):
        """處理同幣別帳戶間轉帳。"""
        transfer_amount = Decimal(str(amount))
        if transfer_amount <= 0:
            return False, "轉帳金額必須大於0"

        source_account = self._get_account(user_id, source_key)
        target_account = self._get_account(user_id, dest_key)
        if not source_account:
            raise ValueError("來源帳戶不存在或權限不足")
        if not target_account:
            raise ValueError("目標帳戶不存在或權限不足")
        if not source_account["track_balance"] or not target_account["track_balance"]:
            raise ValueError("轉帳帳戶必須啟用餘額追蹤")
        if source_account["currency"] != target_account["currency"]:
            raise ValueError("目前前端轉帳只支援同幣別帳戶")

        source_balance = Decimal(str(source_account["balance"]))
        target_balance = Decimal(str(target_account["balance"]))
        if source_balance < transfer_amount and not self._allows_negative_balance(source_account):
            raise ValueError("來源帳戶餘額不足")

        now = datetime.now(timezone.utc)
        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == source_account["id"])
            .values(balance=source_balance - transfer_amount, updated_at=now)
        )
        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == target_account["id"])
            .values(balance=target_balance + transfer_amount, updated_at=now)
        )
        self.db_session.execute(
            insert(transfers_table).values(
                user_id=self._parse_user_id(user_id),
                source_account_id=source_account["id"],
                target_account_id=target_account["id"],
                source_amount=transfer_amount,
                source_currency=source_account["currency"],
                target_amount=transfer_amount,
                target_currency=target_account["currency"],
                target_per_source_rate=Decimal("1"),
                transfer_date=now.date(),
                note=self._normalize_transfer_note(note),
            )
        )
        return True, "轉帳成功"

    def update_transfer(self, user_id, transfer_id, source_key, dest_key, amount, note=None):
        """編輯既有同幣別轉帳，會同步回復舊餘額並套用新餘額。"""
        transfer = self._get_transfer(user_id, transfer_id)
        if not transfer:
            raise ValueError("找不到此轉帳紀錄或權限不足")

        transfer_amount = Decimal(str(amount))
        if transfer_amount <= 0:
            return False, "轉帳金額必須大於0"

        source_account = self._get_account(user_id, source_key)
        target_account = self._get_account(user_id, dest_key)
        if not source_account:
            raise ValueError("來源帳戶不存在或權限不足")
        if not target_account:
            raise ValueError("目標帳戶不存在或權限不足")
        if source_account["id"] == target_account["id"]:
            return False, "轉出和轉入帳戶不能是同一個"
        if not source_account["track_balance"] or not target_account["track_balance"]:
            raise ValueError("轉帳帳戶必須啟用餘額追蹤")
        if source_account["currency"] != target_account["currency"]:
            raise ValueError("目前前端轉帳只支援同幣別帳戶")

        now = datetime.now(timezone.utc)
        self._reverse_transfer_effect(user_id, transfer, now)

        refreshed_source = self._get_account(user_id, source_key)
        refreshed_target = self._get_account(user_id, dest_key)
        self._apply_transfer_effect(refreshed_source, refreshed_target, transfer_amount, now)

        self.db_session.execute(
            update(transfers_table)
            .where(transfers_table.c.id == transfer["id"])
            .values(
                source_account_id=refreshed_source["id"],
                target_account_id=refreshed_target["id"],
                source_amount=transfer_amount,
                source_currency=refreshed_source["currency"],
                target_amount=transfer_amount,
                target_currency=refreshed_target["currency"],
                target_per_source_rate=Decimal("1"),
                note=self._normalize_transfer_note(note),
                updated_at=now,
            )
        )
        return True, "轉帳已更新"

    def delete_transfer(self, user_id, transfer_id):
        """軟刪除轉帳並回復該筆轉帳造成的餘額變動。"""
        transfer = self._get_transfer(user_id, transfer_id)
        if not transfer:
            raise ValueError("找不到此轉帳紀錄或權限不足")

        now = datetime.now(timezone.utc)
        self._reverse_transfer_effect(user_id, transfer, now)
        self.db_session.execute(
            update(transfers_table)
            .where(transfers_table.c.id == transfer["id"])
            .values(
                deleted_at=now,
                purge_after=now + timedelta(days=30),
                updated_at=now,
            )
        )
        return True, "轉帳已刪除"

    def _get_transfer(self, user_id, transfer_id):
        stmt = select(transfers_table).where(
            transfers_table.c.user_id == self._parse_user_id(user_id),
            transfers_table.c.id == self._parse_uuid(transfer_id, "transfer_id"),
            transfers_table.c.deleted_at.is_(None),
        )
        row = self.db_session.execute(stmt).first()
        return dict(row._mapping) if row else None

    def _reverse_transfer_effect(self, user_id, transfer, now):
        source_account = self._get_account(user_id, transfer["source_account_id"])
        target_account = self._get_account(user_id, transfer["target_account_id"])
        if not source_account or not target_account:
            raise ValueError("轉帳帳戶不存在或已刪除，無法編輯此轉帳")

        source_balance = Decimal(str(source_account["balance"]))
        target_balance = Decimal(str(target_account["balance"]))
        old_source_amount = Decimal(str(transfer["source_amount"]))
        old_target_amount = Decimal(str(transfer["target_amount"]))
        restored_target_balance = target_balance - old_target_amount
        if restored_target_balance < 0 and not self._allows_negative_balance(target_account):
            raise ValueError("轉入帳戶餘額不足，無法回復此轉帳")

        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == source_account["id"])
            .values(balance=source_balance + old_source_amount, updated_at=now)
        )
        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == target_account["id"])
            .values(balance=restored_target_balance, updated_at=now)
        )

    def _apply_transfer_effect(self, source_account, target_account, transfer_amount, now):
        source_balance = Decimal(str(source_account["balance"]))
        target_balance = Decimal(str(target_account["balance"]))
        if source_balance < transfer_amount and not self._allows_negative_balance(source_account):
            raise ValueError("來源帳戶餘額不足")

        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == source_account["id"])
            .values(balance=source_balance - transfer_amount, updated_at=now)
        )
        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == target_account["id"])
            .values(balance=target_balance + transfer_amount, updated_at=now)
        )

    def get_recent_transfers(self, user_id, limit=10):
        """取得最近帳戶轉帳紀錄，供資金分配列表顯示。"""
        parsed_limit = self._normalize_limit(limit)
        source_accounts = accounts_table.alias("source_accounts")
        target_accounts = accounts_table.alias("target_accounts")
        stmt = (
            select(
                transfers_table.c.id,
                transfers_table.c.source_account_id,
                transfers_table.c.target_account_id,
                transfers_table.c.source_amount,
                transfers_table.c.source_currency,
                transfers_table.c.target_amount,
                transfers_table.c.target_currency,
                transfers_table.c.transfer_date,
                transfers_table.c.note,
                source_accounts.c.name.label("source_name"),
                source_accounts.c.type.label("source_type"),
                target_accounts.c.name.label("target_name"),
                target_accounts.c.type.label("target_type"),
            )
            .join(source_accounts, transfers_table.c.source_account_id == source_accounts.c.id)
            .join(target_accounts, transfers_table.c.target_account_id == target_accounts.c.id)
            .where(
                transfers_table.c.user_id == self._parse_user_id(user_id),
                transfers_table.c.deleted_at.is_(None),
            )
            .order_by(desc(transfers_table.c.transfer_date), desc(transfers_table.c.created_at))
            .limit(parsed_limit)
        )

        transfers = []
        for row in self.db_session.execute(stmt):
            transfer = dict(row._mapping)
            transfer["id"] = str(transfer["id"])
            transfer["source_account_id"] = str(transfer["source_account_id"])
            transfer["target_account_id"] = str(transfer["target_account_id"])
            transfer["source_amount"] = float(transfer["source_amount"])
            transfer["target_amount"] = float(transfer["target_amount"])
            transfer["transfer_date"] = transfer["transfer_date"].isoformat()
            transfers.append(transfer)
        return transfers

    def get_account_activity(self, user_id, account_key, limit=10, page=1, activity_filter="all"):
        """取得單一帳戶近期收支與轉帳活動。"""
        normalized_filter = (activity_filter or "all").strip().lower()
        if normalized_filter not in {"all", "income", "expense", "transfer"}:
            raise ValueError("無效的活動篩選條件")

        account = self._get_account(user_id, account_key)
        if not account:
            raise ValueError("找不到此帳戶或權限不足")

        parsed_user_id = self._parse_user_id(user_id)
        parsed_limit = self._normalize_limit(limit)
        parsed_page = self._normalize_page(page)
        fetch_limit = parsed_limit * (parsed_page + 1)
        page_start = (parsed_page - 1) * parsed_limit
        page_end = page_start + parsed_limit
        account_id = account["id"]

        transaction_filters = [
            transactions_table.c.user_id == parsed_user_id,
            transactions_table.c.account_id == account_id,
            transactions_table.c.deleted_at.is_(None),
        ]
        if normalized_filter in {"income", "expense"}:
            transaction_filters.append(transactions_table.c.type == normalized_filter)

        transaction_stmt = (
            select(
                transactions_table.c.id,
                transactions_table.c.transaction_date.label("activity_date"),
                transactions_table.c.created_at,
                transactions_table.c.type.label("transaction_type"),
                transactions_table.c.title,
                transactions_table.c.merchant,
                transactions_table.c.description,
                transactions_table.c.original_amount.label("amount"),
                transactions_table.c.original_currency.label("currency"),
                transactions_table.c.trip_id,
                transactions_table.c.user_id,
                transactions_table.c.created_by_user_id,
                categories_table.c.name.label("budget_category"),
            )
            .join(categories_table, transactions_table.c.category_id == categories_table.c.id)
            .where(*transaction_filters)
            .order_by(desc(transactions_table.c.transaction_date), desc(transactions_table.c.created_at))
            .limit(fetch_limit)
        )

        source_accounts = accounts_table.alias("source_accounts")
        target_accounts = accounts_table.alias("target_accounts")
        transfer_stmt = (
            select(
                transfers_table.c.id,
                transfers_table.c.source_account_id,
                transfers_table.c.target_account_id,
                transfers_table.c.source_amount,
                transfers_table.c.source_currency,
                transfers_table.c.target_amount,
                transfers_table.c.target_currency,
                transfers_table.c.transfer_date.label("activity_date"),
                transfers_table.c.created_at,
                transfers_table.c.note,
                source_accounts.c.name.label("source_name"),
                target_accounts.c.name.label("target_name"),
            )
            .join(source_accounts, transfers_table.c.source_account_id == source_accounts.c.id)
            .join(target_accounts, transfers_table.c.target_account_id == target_accounts.c.id)
            .where(
                transfers_table.c.user_id == parsed_user_id,
                transfers_table.c.deleted_at.is_(None),
                or_(
                    transfers_table.c.source_account_id == account_id,
                    transfers_table.c.target_account_id == account_id,
                ),
            )
            .order_by(desc(transfers_table.c.transfer_date), desc(transfers_table.c.created_at))
            .limit(fetch_limit)
        )

        activities = []
        if normalized_filter != "transfer":
            for row in self.db_session.execute(transaction_stmt):
                transaction = dict(row._mapping)
                can_manage = False
                if not transaction["trip_id"]:
                    can_manage = transaction["user_id"] == parsed_user_id
                activities.append({
                    "id": str(transaction["id"]),
                    "type": "transaction",
                    "transaction_type": transaction["transaction_type"],
                    "title": transaction["title"],
                    "merchant": transaction["merchant"],
                    "description": transaction["description"],
                    "amount": float(transaction["amount"]),
                    "currency": transaction["currency"],
                    "date": transaction["activity_date"].isoformat(),
                    "created_at": transaction["created_at"].isoformat() if transaction["created_at"] else None,
                    "budget_category": transaction["budget_category"],
                    "trip_id": str(transaction["trip_id"]) if transaction["trip_id"] else None,
                    "can_edit": can_manage,
                    "can_delete": can_manage,
                })

        if normalized_filter not in {"income", "expense"}:
            for row in self.db_session.execute(transfer_stmt):
                transfer = dict(row._mapping)
                direction = "out" if transfer["source_account_id"] == account_id else "in"
                amount = transfer["source_amount"] if direction == "out" else transfer["target_amount"]
                currency = transfer["source_currency"] if direction == "out" else transfer["target_currency"]
                activities.append({
                    "id": str(transfer["id"]),
                    "type": "transfer",
                    "direction": direction,
                    "source_account_id": str(transfer["source_account_id"]),
                    "target_account_id": str(transfer["target_account_id"]),
                    "source_amount": float(transfer["source_amount"]),
                    "source_currency": transfer["source_currency"],
                    "target_amount": float(transfer["target_amount"]),
                    "target_currency": transfer["target_currency"],
                    "source_name": transfer["source_name"],
                    "target_name": transfer["target_name"],
                    "amount": float(amount),
                    "currency": currency,
                    "date": transfer["activity_date"].isoformat(),
                    "created_at": transfer["created_at"].isoformat() if transfer["created_at"] else None,
                    "note": transfer["note"],
                })

        sorted_activities = sorted(
            activities,
            key=lambda activity: (activity["date"], activity.get("created_at") or ""),
            reverse=True,
        )
        page_items = sorted_activities[page_start:page_end]
        has_next = len(sorted_activities) > page_end

        return {
            "items": page_items,
            "pagination": {
                "page": parsed_page,
                "limit": parsed_limit,
                "has_next": has_next,
                "has_prev": parsed_page > 1,
                "filter": normalized_filter,
            },
        }

    def _normalize_transfer_note(self, note):
        normalized = str(note or "").strip()
        if len(normalized) > 100:
            normalized = normalized[:100]
        return normalized or None

    def _normalize_limit(self, limit):
        try:
            parsed_limit = int(limit)
        except (TypeError, ValueError):
            parsed_limit = 10
        return min(max(parsed_limit, 1), 50)

    def _normalize_page(self, page):
        try:
            parsed_page = int(page)
        except (TypeError, ValueError):
            parsed_page = 1
        return max(parsed_page, 1)

    def calculate_totals(self, user_id):
        """依幣別計算帳戶總額，不直接混加不同幣別。"""
        totals = {}
        stmt = select(accounts_table).where(
            accounts_table.c.user_id == self._parse_user_id(user_id),
            accounts_table.c.deleted_at.is_(None),
            accounts_table.c.track_balance.is_(True),
        )

        for row in self.db_session.execute(stmt):
            account = dict(row._mapping)
            currency = account["currency"]
            balance = float(account["balance"] or 0)
            account_type = account["type"]
            totals.setdefault(currency, {"total": 0, "by_type": {}})
            totals[currency]["total"] += balance
            totals[currency]["by_type"][account_type] = totals[currency]["by_type"].get(account_type, 0) + balance
        return totals
