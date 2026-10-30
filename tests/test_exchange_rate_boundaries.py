"""R04 guard boundaries; no database or provider connections are needed."""
from decimal import Decimal

import pytest

from models.budget_manager import BudgetManager


@pytest.mark.parametrize('currency', ['TWD', 'JPY', 'KRW', 'USD', 'EUR'])
def test_same_currency_does_not_require_a_cross_currency_quote(currency):
    assert BudgetManager(None)._default_exchange_rate(currency, currency) == Decimal('1')


@pytest.mark.parametrize('original,base', [
    ('KRW', 'USD'), ('USD', 'KRW'), ('KRW', 'EUR'), ('EUR', 'KRW'),
])
def test_valid_seeded_currencies_without_a_quote_are_not_treated_as_equal(original, base):
    # Both currencies are supported; that alone does not supply a conversion rate.
    with pytest.raises(ValueError, match='exchange_rate'):
        BudgetManager(None)._default_exchange_rate(original, base)
