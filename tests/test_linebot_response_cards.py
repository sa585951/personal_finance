from types import SimpleNamespace

from linebot.models import FlexSendMessage

from models.linebot.manager import LineBotManager
from models.linebot.themes.accounting_theme import AccountingTheme
from models.linebot.themes.operation_theme import OperationTheme
from models.linebot.response_builder import ResponseBuilder


def test_expense_success_card_includes_account_message():
    theme = AccountingTheme()

    message = theme.create_expense_success(
        {
            "category": "午餐",
            "amount": 150,
            "description": "麥當勞",
            "account_message": "已從 現金 扣款",
        }
    )

    detail_rows = message.contents.body.contents[2].contents

    assert message.alt_text == "午餐 $150 記帳成功"
    assert detail_rows[2].contents[0].text == "帳戶"
    assert detail_rows[2].contents[1].text == "已從 現金 扣款"


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
            "description": "薪資",
            "account_message": "已存入 銀行",
        }
    )

    detail_rows = message.contents.body.contents[2].contents

    assert message.alt_text == "收入 +$3,000 記錄成功"
    assert detail_rows[2].contents[0].text == "帳戶"
    assert detail_rows[2].contents[1].text == "已存入 銀行"


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
