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
    def find_asset_by_name(self, *args, **kwargs):
        return None


class FakeResponseBuilder:
    def __init__(self):
        self.last_expense_data = None

    def create_expense_success(self, data):
        self.last_expense_data = data
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
