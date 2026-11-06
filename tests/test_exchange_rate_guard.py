"""R04: a missing cross-currency rate must not silently post at parity."""
from decimal import Decimal

import pytest
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.schema import (
    accounts_table, account_movements_table, transactions_table, transaction_splits_table, currencies_table,
)
from tests.test_financial_command_idempotency import command_db  # noqa: F401


@pytest.fixture
def fx_db(command_db):
    engine, data = command_db
    # Test-only currency: valid in the DB but absent from the default-rate table.
    with engine.begin() as connection:
        connection.execute(insert(currencies_table).values(
            code='GBP', name='Synthetic GBP fixture', symbol='GBP', minor_unit=2))
    return engine, data


def snapshot(session):
    return [list(session.execute(select(table).order_by(table.c.id))) for table in (
        accounts_table, account_movements_table, transactions_table, transaction_splits_table,
    )]


@pytest.mark.parametrize('operation', ['create', 'update'])
def test_missing_cross_currency_rate_rejects_without_financial_changes(fx_db, operation):
    engine, data = fx_db
    with Session(engine) as session:
        manager = BudgetManager(session)
        if operation == 'update':
            manager.add_transaction(data['a'], '2026-10-01', 'Original', 10, 'expense',
                                    '伙食', account_id=data['cash'])
            transaction_id = manager.last_created_transaction_id
            session.commit()
        before = snapshot(session)
        with pytest.raises(ValueError, match='exchange_rate'):
            if operation == 'create':
                manager.add_transaction(data['a'], '2026-10-01', 'GBP', 10, 'expense',
                                        '伙食', account_id=data['cash'], original_currency='GBP')
            else:
                manager.update_transaction(data['a'], transaction_id, '2026-10-01', 'GBP',
                    10, 'expense', '伙食', account_id=data['cash'], original_currency='GBP')
        # Do not let rollback mask partial writes on a validation error.
        assert snapshot(session) == before
        session.commit()
    with Session(engine) as session:
        assert snapshot(session) == before


@pytest.mark.parametrize('currency,rate,stored_rate,converted,balance', [
    ('TWD', None, '1', '10', '990'),
    ('USD', None, '32', '320', '680'),
    ('GBP', '40', '40', '400', '600'),
])
def test_supported_or_explicit_rate_preserves_posted_amounts(
        fx_db, currency, rate, stored_rate, converted, balance):
    engine, data = fx_db
    with Session(engine) as session:
        manager = BudgetManager(session)
        manager.add_transaction(data['a'], '2026-10-01', 'FX', 10, 'expense', '伙食',
            account_id=data['cash'], original_currency=currency, exchange_rate=rate)
        transaction_id = manager.last_created_transaction_id
        session.commit()
    with Session(engine) as session:
        transaction = session.execute(select(transactions_table).where(
            transactions_table.c.id == transaction_id)).one()
        assert transaction.original_currency == currency
        assert transaction.base_currency == 'TWD'
        assert transaction.exchange_rate == Decimal(stored_rate)
        assert transaction.converted_amount == Decimal(converted)
        assert session.scalar(select(accounts_table.c.balance).where(
            accounts_table.c.id == data['cash'])) == Decimal(balance)
        movement = session.execute(select(account_movements_table).where(
            account_movements_table.c.source_id == transaction_id)).one()
        assert movement.amount_delta == -Decimal(converted)
