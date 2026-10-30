from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.reconciliation_manager import ReconciliationManager
from models.schema import accounts_table, transactions_table, transaction_splits_table
from tests.test_exchange_rate_guard import fx_db, command_db  # noqa: F401


def assert_posting(session, tid, data, rate, converted, balance):
    row = session.execute(select(transactions_table).where(transactions_table.c.id==tid)).one()
    assert row.exchange_rate == Decimal(rate)
    assert row.converted_amount == Decimal(converted)
    assert session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id==data['cash'])) == Decimal(balance)
    assert ReconciliationManager(session).reconcile()['summary']['mismatched'] == 0


@pytest.mark.parametrize('currency,rate,converted,balance', [
    ('USD', '31.5', '315', '685'), ('GBP', '40', '400', '600'),
])
@pytest.mark.parametrize('pass_currency', [False, True])
def test_metadata_edit_keeps_historical_rate_and_net_balance(fx_db, currency, rate, converted, balance, pass_currency):
    engine, data = fx_db
    with Session(engine) as session:
        m = BudgetManager(session)
        m.add_transaction(data['a'], '2026-10-01', 'Original', 10, 'expense', '伙食',
            account_id=data['cash'], original_currency=currency, exchange_rate=rate)
        tid = m.last_created_transaction_id
        session.commit()
        m.update_transaction(data['a'], tid, '2026-10-01', 'Rename', 10, 'expense', '伙食',
            account_id=data['cash'], original_currency=currency if pass_currency else None)
        session.commit()
    with Session(engine) as session:
        assert_posting(session, tid, data, rate, converted, balance)


@pytest.mark.parametrize('changes,rate,converted,balance', [
    ({'amount':20}, '31.5', '630', '370'),
    ({'exchange_rate':'30'}, '30', '300', '700'),
    ({'original_currency':'EUR'}, '35', '350', '650'),
])
def test_amount_or_explicit_currency_intent_uses_correct_rate(fx_db, changes, rate, converted, balance):
    engine, data = fx_db
    with Session(engine) as session:
        m = BudgetManager(session)
        m.add_transaction(data['a'], '2026-10-01', 'Original', 10, 'expense', '伙食',
            account_id=data['cash'], original_currency='USD', exchange_rate='31.5')
        tid = m.last_created_transaction_id
        session.commit()
        options = dict(amount=10, account_id=data['cash'])
        options.update(changes)
        m.update_transaction(data['a'], tid, '2026-10-01', 'Edit',
                             transaction_type='expense', budget_category='伙食', **options)
        session.commit()
    with Session(engine) as session:
        assert_posting(session, tid, data, rate, converted, balance)


def test_trip_metadata_edit_preserves_split_rate_and_account_effect(fx_db):
    engine, data = fx_db
    with Session(engine) as session:
        m = BudgetManager(session)
        options = dict(account_id=data['cash'], paid_by_member_id=data['am'],
                       split_member_ids=[data['am'],data['bm']], original_currency='JPY')
        m.add_transaction(data['a'], '2026-10-01', 'Trip', 100, 'expense', '伙食',
                          trip_id=data['trip'], exchange_rate='.25', **options)
        tid = m.last_created_transaction_id
        session.commit()
        m.update_transaction(data['a'], tid, '2026-10-01', 'Trip renamed', 100,
                              'expense', '伙食', **options)
        session.commit()
    with Session(engine) as session:
        assert_posting(session, tid, data, '.25', '25', '975')
        rows = session.execute(select(transaction_splits_table).where(
            transaction_splits_table.c.transaction_id==tid)).all()
        assert len(rows)==2
        assert all(r.exchange_rate==Decimal('.25') and r.converted_share_amount==Decimal('12.5') for r in rows)
