import json
from decimal import Decimal
from types import SimpleNamespace

from models.linebot.manager import LineBotManager
from models.linebot.line_sdk import FlexSendMessage
from models.linebot.themes.accounting_theme import AccountingTheme
from models.linebot.themes.operation_theme import OperationTheme
from models.linebot.themes.statistics_theme import StatisticsTheme
from models.linebot.response_builder import ResponseBuilder


def test_expense_success_card_includes_account_message():
    theme = AccountingTheme()

    message = theme.create_expense_success(
        {
            "category": "午餐",
            "budget_category": "伙食",
            "amount": 150,
            "description": "麥當勞",
            "account_message": "已從 現金 扣款",
        }
    )

    detail_rows = message.contents.body.contents[2].contents

    assert message.alt_text == "午餐 $150 記帳成功"
    assert _detail_value(detail_rows, "類別") == "伙食"
    assert _detail_value(detail_rows, "帳戶") == "已從 現金 扣款"


def test_expense_success_card_omits_empty_description_row():
    theme = AccountingTheme()

    message = theme.create_expense_success(
        {
            "category": "麥當勞",
            "amount": 150,
            "description": "",
            "account_message": "已從 現金 扣款",
        }
    )

    detail_rows = message.contents.body.contents[2].contents

    assert detail_rows[0].contents[0].text == "時間"
    assert detail_rows[1].contents[0].text == "帳戶"


def test_income_success_card_includes_account_message():
    theme = AccountingTheme()

    message = theme.create_income_success(
        {
            "amount": 3000,
            "budget_category": "薪資",
            "description": "薪資",
            "account_message": "已存入 銀行",
        }
    )

    detail_rows = message.contents.body.contents[2].contents

    assert message.alt_text == "收入 +$3,000 記錄成功"
    assert _detail_value(detail_rows, "類別") == "薪資"
    assert _detail_value(detail_rows, "帳戶") == "已存入 銀行"


def test_transaction_confirmation_accepts_chinese_income_type():
    message = OperationTheme().create_transaction_confirmation(
        "收入",
        {
            "category": "薪資",
            "amount": 3000,
            "description": "六月薪資",
        },
    )

    assert message.alt_text == "確認新增收入"
    assert message.contents.header.contents[0].text == "確認新增收入"
    assert message.contents.body.contents[0].contents[1].text == "收入"
    assert message.contents.body.contents[2].contents[1].text == "+$3,000"


def test_asset_overview_supports_currency_grouped_totals():
    builder = ResponseBuilder()

    message = builder.create_asset_overview(
        {
            "TWD": {"total": 12000, "by_type": {"cash": 2000, "bank": 10000}},
            "JPY": {"total": 5000, "by_type": {"cash": 5000}},
        }
    )

    body_contents = message.contents.body.contents
    twd_section = body_contents[1]
    jpy_section = body_contents[2]

    assert message.alt_text == "資產總覽"
    assert message.contents.header.contents[1].text == "多幣別資產"
    assert twd_section.contents[0].contents[0].text == "TWD"
    assert twd_section.contents[0].contents[1].text == "12,000"
    assert twd_section.contents[1].contents[0].text == "現金"
    assert jpy_section.contents[0].contents[0].text == "JPY"


def test_error_message_is_flex_card():
    message = ResponseBuilder().create_error_message("測試錯誤")

    assert isinstance(message, FlexSendMessage)
    assert message.alt_text == "發生問題"
    assert message.contents.body.contents[0].text == "發生問題"
    assert message.contents.body.contents[1].text == "測試錯誤"


def test_line_manager_wraps_plain_text_as_flex_card():
    manager = SimpleNamespace(
        message_handler=SimpleNamespace(response_builder=ResponseBuilder())
    )

    message = LineBotManager._to_line_message(manager, "流程已取消")

    assert isinstance(message, FlexSendMessage)
    assert message.alt_text == "通知"
    assert message.contents.body.contents[1].text == "流程已取消"


def test_budget_category_selection_is_flex_card():
    message = OperationTheme().create_budget_category_selection(
        "2026-06",
        ["伙食", "交通"],
    )

    assert isinstance(message, FlexSendMessage)
    assert message.alt_text == "請選擇預算類別"
    assert message.contents.body.contents[0].text == "設定預算"


def test_help_message_lists_line_command_examples():
    message = ResponseBuilder().create_help_message()
    message_payload = json.loads(message.as_json_string())
    text_values = []

    def collect_text_values(value):
        if isinstance(value, dict):
            if "text" in value:
                text_values.append(value["text"])
            for nested_value in value.values():
                collect_text_values(nested_value)
        elif isinstance(value, list):
            for nested_value in value:
                collect_text_values(nested_value)

    collect_text_values(message_payload)

    assert isinstance(message, FlexSendMessage)
    assert message.alt_text == "LINE 可用功能"
    assert "- 午餐麥當勞 150 用現金" in text_values
    assert "- 晚餐 680 用國泰信用卡" in text_values
    assert "- 薪資 50000 存入銀行" in text_values
    assert "- 咖啡 5 美元 用美金現金" in text_values
    assert "帳戶連動提示" in text_values
    assert "旅行帳本請開啟 Web 使用；LINE 目前用於快速記帳與查詢。" in text_values
    assert "我的資產" in text_values
    assert "我要轉帳" in text_values


def test_monthly_summary_formats_decimal_amounts_for_line_display():
    message = StatisticsTheme().create_monthly_summary(
        "2026-06",
        Decimal("450.2200"),
        1,
        [
            {
                "date": "2026-06-26",
                "budget_category": "伙食",
                "amount": Decimal("450.2200"),
            }
        ],
        [{"category": "伙食", "count": 1, "total": Decimal("450.2200")}],
    )

    payload = json.loads(message.as_json_string())
    payload_text = json.dumps(payload, ensure_ascii=False)

    assert message.alt_text == "2026-06 支出統計 $450.22"
    assert "$450.2200" not in payload_text
    assert "$450.22" in payload_text


def test_unrecognized_input_message_guides_user_to_examples():
    message = ResponseBuilder().create_unrecognized_input_message()
    message_payload = json.loads(message.as_json_string())
    payload_text = json.dumps(message_payload, ensure_ascii=False)

    assert isinstance(message, FlexSendMessage)
    assert message.alt_text == "無法解析輸入"
    assert "目前看不出這是一筆記錄" in payload_text
    assert "午餐麥當勞 150" in payload_text
    assert "查看幫助" in payload_text


def _detail_value(detail_rows, label):
    for row in detail_rows:
        if row.contents[0].text == label:
            return row.contents[1].text
    return None
