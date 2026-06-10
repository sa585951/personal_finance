from models.ai_parse_service import AIParseService
from models.linebot.message_parser import MessageParser


class FakeGeminiResponse:
    def __init__(self, text):
        self.text = text


class FakeGeminiModel:
    def __init__(self, response_text):
        self.response_text = response_text
        self.last_prompt = None

    def generate_content(self, prompt):
        self.last_prompt = prompt
        return FakeGeminiResponse(self.response_text)


def test_quick_parser_result_is_normalized_and_keeps_legacy_format():
    service = AIParseService(
        gemini_model=FakeGeminiModel("{}"),
        prompt_template="訊息：{message}",
    )

    result = service.parse("新增支出")

    assert result["intent"] == "start_flow"
    assert result["source"] == "quick"
    assert result["legacy"] == {"type": "start_add_expense"}
    assert result["flow"] == {"name": "add_expense", "payload": {}}
    assert result["transaction"] is None
    assert service.parse_legacy("新增支出") == {"type": "start_add_expense"}


def test_gemini_transaction_result_is_normalized_for_shared_clients():
    fake_model = FakeGeminiModel(
        """
        ```json
        {
          "type": "expense",
          "budget_category": "伙食",
          "category": "午餐",
          "description": "麥當勞",
          "amount": 150,
          "target_asset": "現金"
        }
        ```
        """
    )
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("午餐吃麥當勞 150 元，用現金")

    assert result["intent"] == "create_transaction"
    assert result["source"] == "gemini"
    assert result["legacy"]["type"] == "expense"
    assert result["transaction"] == {
        "type": "expense",
        "title": "午餐",
        "budget_category": "伙食",
        "amount": "150",
        "description": "麥當勞",
        "account_hint": "現金",
        "currency": None,
        "date": None,
        "merchant": None,
    }
    assert result["missing_fields"] == []
    assert "午餐吃麥當勞 150 元，用現金" in fake_model.last_prompt


def test_expense_keyword_with_amount_uses_gemini_instead_of_query_shortcut():
    fake_model = FakeGeminiModel(
        """
        {
          "type": "expense",
          "budget_category": "其他",
          "category": "記帳",
          "description": "支出",
          "amount": 100,
          "target_asset": null
        }
        """
    )
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("支出 100")

    assert result["intent"] == "create_transaction"
    assert result["source"] == "gemini"
    assert result["transaction"]["amount"] == "100"
    assert "支出 100" in fake_model.last_prompt


def test_expense_query_without_amount_still_uses_query_shortcut():
    service = AIParseService(
        gemini_model=FakeGeminiModel("{}"),
        prompt_template="訊息：{message}",
    )

    result = service.parse("查詢本月支出")

    assert result["intent"] == "query_transactions"
    assert result["source"] == "quick"


def test_local_fallback_parses_basic_expense_when_gemini_fails():
    fake_model = FakeGeminiModel('{"type":"other","error":"API key not valid"}')
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("早餐麥當勞 150 元，用現金")

    assert result["intent"] == "create_transaction"
    assert result["source"] == "local_fallback"
    assert result["legacy"]["fallback_reason"] == "gemini_error"
    assert result["transaction"] == {
        "type": "expense",
        "title": "早餐",
        "budget_category": "伙食",
        "amount": "150",
        "description": "早餐麥當勞",
        "account_hint": "現金",
        "currency": None,
        "date": None,
        "merchant": None,
    }


def test_message_parser_keeps_existing_line_parse_contract():
    parser = MessageParser(
        gemini_model=FakeGeminiModel('{"type":"other"}'),
        prompt_template="訊息：{message}",
    )

    assert parser.parse("新增收入") == {"type": "start_add_income"}

    shared_result = parser.parse_shared("新增收入")
    assert shared_result["intent"] == "start_flow"
    assert shared_result["flow"]["name"] == "add_income"


def test_other_result_is_normalized_without_errors():
    service = AIParseService(
        gemini_model=FakeGeminiModel("{}"),
        prompt_template="訊息：{message}",
    )

    result = service.parse("幫助")

    assert result["intent"] == "other"
    assert result["source"] == "quick"
    assert result["legacy"] == {"type": "other"}
    assert result["missing_fields"] == []
    assert result["errors"] == []
