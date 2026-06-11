from models.budget_manager import BudgetManager


def test_only_credit_card_transaction_accounts_allow_negative_balance():
    manager = BudgetManager(db_session=None)

    assert manager._account_allows_negative_balance({"type": "credit_card"}) is True
    assert manager._account_allows_negative_balance({"type": "bank"}) is False
