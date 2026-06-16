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
          "category": "麥當勞",
          "description": "",
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
        "currency": "TWD",
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
    assert result["transaction"]["description"] == ""
    assert "支出 100" in fake_model.last_prompt


def test_gemini_missing_description_does_not_fall_back_to_raw_text():
    fake_model = FakeGeminiModel(
        """
        {
          "type": "expense",
          "budget_category": "交通",
          "category": "計程車",
          "amount": 250,
          "target_asset": null
        }
        """
    )
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("搭計程車回家花了 250")

    assert result["intent"] == "create_transaction"
    assert result["transaction"]["title"] == "計程車"
    assert result["transaction"]["description"] == ""


def test_gemini_raw_text_description_is_treated_as_empty_note():
    fake_model = FakeGeminiModel(
        """
        {
          "type": "expense",
          "budget_category": "伙食",
          "category": "早餐",
          "description": "早餐 100",
          "amount": 100,
          "target_asset": null
        }
        """
    )
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("早餐 100")

    assert result["transaction"]["description"] == ""


def test_standard_expense_sentence_splits_item_and_note():
    fake_model = FakeGeminiModel(
        """
        {
          "type": "expense",
          "budget_category": "伙食",
          "category": "麥當勞",
          "description": "",
          "amount": 150,
          "target_asset": null
        }
        """
    )
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("午餐麥當勞 150")

    assert result["transaction"]["type"] == "expense"
    assert result["transaction"]["title"] == "午餐"
    assert result["transaction"]["budget_category"] == "伙食"
    assert result["transaction"]["amount"] == "150"
    assert result["transaction"]["description"] == "麥當勞"


def test_loose_expense_sentence_keeps_leading_item_when_words_are_reordered():
    fake_model = FakeGeminiModel(
        """
        {
          "type": "expense",
          "budget_category": "伙食",
          "category": "麥當勞",
          "description": "",
          "amount": 120,
          "target_asset": "現金"
        }
        """
    )
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("午餐 120 麥當勞 現金")

    assert result["transaction"]["title"] == "午餐"
    assert result["transaction"]["amount"] == "120"
    assert result["transaction"]["description"] == "麥當勞"
    assert result["transaction"]["account_hint"] == "現金"


def test_standard_account_expense_keeps_account_hint_and_empty_note():
    fake_model = FakeGeminiModel(
        """
        {
          "type": "expense",
          "budget_category": "伙食",
          "category": "晚餐",
          "description": "",
          "amount": 680,
          "target_asset": null
        }
        """
    )
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("晚餐 680 用國泰信用卡")

    assert result["transaction"]["title"] == "晚餐"
    assert result["transaction"]["description"] == ""
    assert result["transaction"]["account_hint"] == "國泰信用卡"


def test_standard_income_sentence_keeps_income_item_and_account_hint():
    fake_model = FakeGeminiModel(
        """
        {
          "type": "income",
          "budget_category": "收入",
          "category": "收入",
          "description": "薪資 50000 存入銀行",
          "amount": 50000,
          "target_asset": null
        }
        """
    )
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("薪資 50000 存入銀行")

    assert result["transaction"]["type"] == "income"
    assert result["transaction"]["title"] == "薪資"
    assert result["transaction"]["budget_category"] == "收入"
    assert result["transaction"]["amount"] == "50000"
    assert result["transaction"]["description"] == ""
    assert result["transaction"]["account_hint"] == "銀行"


def test_standard_foreign_currency_expense_keeps_currency_and_account_hint():
    fake_model = FakeGeminiModel(
        """
        {
          "type": "expense",
          "budget_category": "伙食",
          "category": "拉麵",
          "description": "",
          "amount": 1200,
          "target_asset": null
        }
        """
    )
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("拉麵 1200 日幣 用日幣現金")

    assert result["transaction"]["title"] == "拉麵"
    assert result["transaction"]["description"] == ""
    assert result["transaction"]["amount"] == "1200"
    assert result["transaction"]["currency"] == "JPY"
    assert result["transaction"]["account_hint"] == "日幣現金"


def test_expense_query_without_amount_still_uses_query_shortcut():
    service = AIParseService(
        gemini_model=FakeGeminiModel("{}"),
        prompt_template="訊息：{message}",
    )

    result = service.parse("查詢本月支出")

    assert result["intent"] == "query_transactions"
    assert result["source"] == "quick"


def test_goal_keywords_are_temporarily_disabled_in_quick_parser():
    service = AIParseService(
        gemini_model=FakeGeminiModel("{}"),
        prompt_template="訊息：{message}",
    )

    result = service.parse("我的財務目標")

    assert result["intent"] == "other"
    assert result["source"] == "quick"
    assert result["legacy"] == {"type": "other"}


def test_legacy_goal_button_payloads_are_temporarily_disabled():
    service = AIParseService(
        gemini_model=FakeGeminiModel("{}"),
        prompt_template="訊息：{message}",
    )

    result = service.parse("編輯目標:abc123")

    assert result["intent"] == "other"
    assert result["source"] == "quick"
    assert result["legacy"] == {"type": "other"}
    assert result["flow"] is None


def test_gemini_goal_start_result_is_not_normalized_as_active_flow():
    service = AIParseService(
        gemini_model=FakeGeminiModel('{"type":"start_add_goal"}'),
        prompt_template="訊息：{message}",
    )

    result = service.parse("存 1000")

    assert result["intent"] == "other"
    assert result["source"] == "gemini"
    assert result["legacy"] == {"type": "start_add_goal"}
    assert result["flow"] is None


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
        "description": "麥當勞",
        "account_hint": "現金",
        "currency": "TWD",
        "date": None,
        "merchant": None,
    }


def test_local_fallback_extracts_currency_hint():
    fake_model = FakeGeminiModel('{"type":"other","error":"API key not valid"}')
    service = AIParseService(
        gemini_model=fake_model,
        prompt_template="訊息：{message}",
    )

    result = service.parse("永豐日幣活存扣拉麵 1200 日圓")

    assert result["transaction"]["amount"] == "1200"
    assert result["transaction"]["currency"] == "JPY"


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
