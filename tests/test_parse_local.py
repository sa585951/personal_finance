"""Web speak-to-record runs on local rules only and never reaches a model provider."""
from models.ai_parse_service import AIParseService


class ExplodingModel:
    def generate_content(self, prompt):
        raise AssertionError("parse_local must never call the model")


def _service():
    return AIParseService(ExplodingModel(), "{message}")


def test_common_sentence_becomes_expense_draft():
    result = _service().parse_local("昨天跟同事吃午餐 刷國泰卡 120")
    transaction = result["transaction"]
    assert transaction["type"] == "expense"
    assert transaction["amount"] == "120"
    assert transaction["budget_category"] == "伙食"
    assert transaction["account_hint"]


def test_income_sentence():
    transaction = _service().parse_local("薪水入帳 62000")["transaction"]
    assert transaction["type"] == "income"
    assert transaction["amount"] == "62000"


def test_sentence_without_amount_has_no_usable_transaction():
    result = _service().parse_local("今天去看電影")
    assert not result["transaction"] or "amount" in result["missing_fields"]
