from datetime import datetime
from zoneinfo import ZoneInfo


class TransactionService:
    """交易用例層，讓 Web API、LINE 與未來 App 共用同一組交易操作入口。"""

    DEFAULT_TRANSACTION_TIMEZONE = "Asia/Taipei"

    def __init__(self, budget_manager, asset_manager=None):
        self.budget_manager = budget_manager
        self.asset_manager = asset_manager

    def create_transaction(self, user_id, payload):
        success, message = self.budget_manager.add_transaction(
            user_id,
            payload["date"],
            payload["item"],
            payload["amount"],
            payload["type"],
            payload["budget_category"],
            payload.get("description", ""),
            account_id=payload.get("account_id"),
            trip_id=payload.get("trip_id"),
            paid_by_member_id=payload.get("paid_by_member_id"),
            merchant=payload.get("merchant"),
            original_currency=payload.get("original_currency"),
            exchange_rate=payload.get("exchange_rate"),
            timezone_name=payload.get("timezone", self.DEFAULT_TRANSACTION_TIMEZONE),
            split_member_ids=payload.get("split_member_ids"),
            split_allocations=payload.get("split_allocations"),
            review_status=payload.get("review_status", "confirmed"),
            client_request_id=payload.get("client_request_id"),
        )
        return {
            "success": success,
            "message": message,
            "transaction_id": getattr(self.budget_manager, "last_created_transaction_id", None),
            "replayed": getattr(self.budget_manager, "last_create_replayed", False),
        }

    def update_transaction(self, user_id, transaction_id, payload):
        success, message = self.budget_manager.update_transaction(
            user_id,
            transaction_id,
            payload["date"],
            payload["item"],
            payload["amount"],
            payload["type"],
            payload["budget_category"],
            payload.get("description", ""),
            account_id=payload.get("account_id"),
            paid_by_member_id=payload.get("paid_by_member_id"),
            merchant=payload.get("merchant"),
            original_currency=payload.get("original_currency"),
            exchange_rate=payload.get("exchange_rate"),
            timezone_name=payload.get("timezone", self.DEFAULT_TRANSACTION_TIMEZONE),
            split_member_ids=payload.get("split_member_ids"),
            split_allocations=payload.get("split_allocations"),
            review_status=payload.get("review_status", "confirmed"),
        )
        return {"success": success, "message": message}

    def delete_transaction(self, user_id, transaction_id):
        success, message = self.budget_manager.delete_transaction(user_id, transaction_id)
        return {"success": success, "message": message}

    def create_from_parsed_transaction(self, user_id, parsed_data, raw_message=""):
        transaction_type = parsed_data["type"]
        target_asset_name = parsed_data.get("target_asset")
        asset = self._find_asset(user_id, target_asset_name, parsed_data, raw_message)
        transaction_date = self._transaction_date(parsed_data)

        result = self.create_transaction(
            user_id,
            {
                "date": transaction_date,
                "item": parsed_data["category"],
                "amount": parsed_data["amount"],
                "type": transaction_type,
                "budget_category": parsed_data["budget_category"],
                "description": parsed_data.get("description", ""),
                "account_id": asset["account_key"] if asset else None,
                "original_currency": parsed_data.get("currency") or (asset["currency"] if asset else None),
            },
        )

        account_message = self._account_message(transaction_type, target_asset_name, asset)
        return {
            **result,
            "data": {
                "category": parsed_data.get("category"),
                "budget_category": parsed_data.get("budget_category"),
                "amount": parsed_data.get("amount"),
                "description": parsed_data.get("description") or "",
                "date": transaction_date,
                "account_message": account_message,
            },
        }

    def _find_asset(self, user_id, target_asset_name, parsed_data, raw_message):
        if not target_asset_name or not self.asset_manager:
            return None
        return self.asset_manager.find_asset_by_name(
            user_id,
            target_asset_name,
            currency=parsed_data.get("currency"),
            context_text=raw_message,
        )

    def _account_message(self, transaction_type, target_asset_name, asset):
        if not target_asset_name:
            return None
        if not asset:
            return f"找不到名為 {target_asset_name} 的資產"
        if transaction_type == "income":
            return f"已存入 {asset['bank_name']}"
        return f"已從 {asset['bank_name']} 扣款"

    def _transaction_date(self, parsed_data):
        parsed_date = parsed_data.get("date")
        if parsed_date:
            return parsed_date
        timezone_name = parsed_data.get("timezone") or self.DEFAULT_TRANSACTION_TIMEZONE
        return datetime.now(ZoneInfo(timezone_name)).strftime("%Y-%m-%d")
