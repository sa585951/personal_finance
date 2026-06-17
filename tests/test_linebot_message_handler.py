from models.linebot.message_handler import MessageHandler


class FakeBudgetManager:
    def __init__(self):
        self.last_payload = None

    def add_transaction(
        self,
        user_id,
        date,
        item,
        amount,
        transaction_type,
        budget_category,
        description="",
        **kwargs,
    ):
        self.last_payload = {
            "user_id": user_id,
            "date": date,
            "item": item,
            "amount": amount,
            "transaction_type": transaction_type,
            "budget_category": budget_category,
            "description": description,
            **kwargs,
        }
        return True, "交易新增成功"


class FakeAssetManager:
    def __init__(self, asset=None):
        self.asset = asset
        self.adjust_calls = []

    def find_asset_by_name(self, *args, **kwargs):
        return self.asset

    def adjust_asset_balance(self, *args, **kwargs):
        self.adjust_calls.append((args, kwargs))
        raise AssertionError("LINE handler should let BudgetManager update linked account balances")


class FakeResponseBuilder:
    def __init__(self):
        self.last_expense_data = None
        self.last_income_data = None

    def create_expense_success(self, data):
        self.last_expense_data = data
        return data

    def create_income_success(self, data):
        self.last_income_data = data
        return data


def test_line_expense_uses_parsed_transaction_date():
    handler = object.__new__(MessageHandler)
    handler.budget_manager = FakeBudgetManager()
    handler.asset_manager = FakeAssetManager()
    handler.response_builder = FakeResponseBuilder()

    response = handler._handle_expense(
        {
            "category": "晚餐",
            "amount": 150,
            "budget_category": "伙食",
            "description": "麥當勞",
            "date": "2026-06-16",
            "currency": None,
            "target_asset": None,
        },
        "user-1",
    )

    assert handler.budget_manager.last_payload["date"] == "2026-06-16"
    assert response["date"] == "2026-06-16"


def test_line_expense_links_account_on_transaction_without_manual_balance_adjustment():
    asset = {
        "account_key": "account-1",
        "bank_name": "國泰信用卡",
        "currency": "TWD",
    }
    handler = object.__new__(MessageHandler)
    handler.budget_manager = FakeBudgetManager()
    handler.asset_manager = FakeAssetManager(asset)
    handler.response_builder = FakeResponseBuilder()

    response = handler._handle_expense(
        {
            "category": "晚餐",
            "amount": 680,
            "budget_category": "伙食",
            "description": "",
            "date": "2026-06-18",
            "currency": None,
            "target_asset": "國泰信用卡",
        },
        "user-1",
    )

    assert handler.budget_manager.last_payload["account_id"] == "account-1"
    assert handler.budget_manager.last_payload["original_currency"] == "TWD"
    assert handler.asset_manager.adjust_calls == []
    assert response["account_message"] == "已從 國泰信用卡 扣款"


def test_line_income_links_account_on_transaction_without_manual_balance_adjustment():
    asset = {
        "account_key": "account-2",
        "bank_name": "玉山銀行",
        "currency": "TWD",
    }
    handler = object.__new__(MessageHandler)
    handler.budget_manager = FakeBudgetManager()
    handler.asset_manager = FakeAssetManager(asset)
    handler.response_builder = FakeResponseBuilder()

    response = handler._handle_income(
        {
            "category": "薪資",
            "amount": 50000,
            "budget_category": "收入",
            "description": "",
            "date": "2026-06-18",
            "currency": None,
            "target_asset": "玉山銀行",
        },
        "user-1",
    )

    assert handler.budget_manager.last_payload["account_id"] == "account-2"
    assert handler.budget_manager.last_payload["original_currency"] == "TWD"
    assert handler.asset_manager.adjust_calls == []
    assert response["account_message"] == "已存入 玉山銀行"
