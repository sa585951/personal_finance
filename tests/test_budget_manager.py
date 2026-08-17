from decimal import Decimal

import pytest

from models.budget_manager import BudgetManager


def test_only_credit_card_transaction_accounts_allow_negative_balance():
    manager = BudgetManager(db_session=None)

    assert manager._account_allows_negative_balance({"type": "credit_card"}) is True
    assert manager._account_allows_negative_balance({"type": "bank"}) is False


@pytest.mark.parametrize(
    ("transaction_type", "expected_delta"),
    [
        ("expense", Decimal("-1000")),
        ("income", Decimal("1000")),
        ("transfer", Decimal("0")),
        ("adjustment", Decimal("0")),
    ],
)
def test_finance_contract_transaction_account_movement_signs(transaction_type, expected_delta):
    manager = BudgetManager(db_session=None)

    assert manager._balance_delta_for_transaction(transaction_type, Decimal("1000")) == expected_delta
