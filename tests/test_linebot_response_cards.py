from models.linebot.themes.accounting_theme import AccountingTheme


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
