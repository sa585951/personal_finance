from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, insert, select, update

from config import DEFAULT_CURRENCY
from .schema import accounts_table, transfers_table


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

    def find_asset_by_name(self, user_id, name, currency=None):
        """根據自然語言名稱尋找指定使用者的帳戶。"""
        stmt = select(accounts_table).where(
            accounts_table.c.user_id == self._parse_user_id(user_id),
            accounts_table.c.deleted_at.is_(None),
            accounts_table.c.name.ilike(name),
        )
        if currency:
            stmt = stmt.where(accounts_table.c.currency == self._normalize_currency(currency))
        row = self.db_session.execute(stmt).first()
        return self._to_legacy_asset(dict(row._mapping)) if row else None

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

    def get_recent_transfers(self, user_id, limit=10):
        """取得最近帳戶轉帳紀錄，供資金分配列表顯示。"""
        parsed_limit = self._normalize_limit(limit)
        source_accounts = accounts_table.alias("source_accounts")
        target_accounts = accounts_table.alias("target_accounts")
        stmt = (
            select(
                transfers_table.c.id,
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
            transfer["source_amount"] = float(transfer["source_amount"])
            transfer["target_amount"] = float(transfer["target_amount"])
            transfer["transfer_date"] = transfer["transfer_date"].isoformat()
            transfers.append(transfer)
        return transfers

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
