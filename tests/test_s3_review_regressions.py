"""Independent review regressions: extreme Decimal inputs and legacy FX precision."""
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.reconciliation_manager import ReconciliationManager
from models.schema import accounts_table, transactions_table, transaction_splits_table
from tests.test_financial_command_idempotency import command_db  # noqa: F401
from tests.test_financial_numeric_boundaries import snapshot
from tests.test_twd_monthly_reports import api_client


@pytest.mark.parametrize('value', ['1e1000000', '-1e1000000'])
def test_extreme_finite_exponent_is_a_validation_error(value):
    # Context-sensitive abs() must not turn an invalid request into Overflow/500.
    with pytest.raises(ValueError):
        BudgetManager(None)._normalize_amount(value)


@pytest.mark.parametrize('operation', ['create', 'update'])
@pytest.mark.parametrize('field', ['amount', 'exchange_rate', 'share'])
def test_extreme_exponent_api_rejects_without_financial_writes(command_db, monkeypatch, operation, field):
    engine, data = command_db
    payload = dict(date='2026-10-01', item='Extreme', amount=1, type='expense',
                   budget_category='伙食', account_id=data['cash'])
    with Session(engine) as session:
        created = BudgetManager(session).add_transaction(data['a'], '2026-10-01', 'Original', 1,
            'expense', '伙食', account_id=data['cash'])
        session.commit()
        before = snapshot(session)
    if field == 'share':
        payload.update(trip_id=data['trip'], paid_by_member_id=data['am'],
                       split_allocations=[dict(trip_member_id=data['am'], amount='1e1000000')])
        if operation == 'update':
            # Existing trip fixture, instead of changing a daily transaction's trip.
            with Session(engine) as session:
                tid = session.scalar(select(transactions_table.c.id).where(
                    transactions_table.c.trip_id == data['trip']))
            payload['amount'] = 1000
            payload.pop('account_id')
        else:
            tid = created.transaction_id
    else:
        payload[field] = '1e1000000'
        tid = created.transaction_id
    client, headers = api_client(monkeypatch, engine, data)
    response = (client.post('/api/transactions', json=payload, headers=headers) if operation == 'create'
                else client.put('/api/transactions/'+str(tid), json=payload, headers=headers))
    assert response.status_code == 400
    assert response.json['success'] is False
    with Session(engine) as session:
        assert snapshot(session) == before


def legacy_transaction(session, data, monkeypatch, mode):
    manager = BudgetManager(session)
    normalize = manager._normalize_amount
    def old_rate_validation(value, field_name='金額', numeric_type=None):
        if field_name == 'exchange_rate ':
            return Decimal(str(value))
        return normalize(value, field_name)
    options = dict(account_id=data['cash'], original_currency='USD')
    if mode != 'daily':
        options.update(trip_id=data['trip'], paid_by_member_id=data['am'])
        if mode == 'equal':
            options['split_member_ids'] = [data['am'], data['bm']]
        else:
            options['split_allocations'] = [dict(trip_member_id=data['am'], amount=60000),
                                             dict(trip_member_id=data['bm'], amount=40000)]
    manager.add_transaction(data['a'], '2026-10-01', 'Synthetic funding', 99000,
        'income', '其他收入', account_id=data['cash'])
    # Reproduce the pre-R06 validator: DB independently rounds rate to 8dp and value to 4dp.
    with monkeypatch.context() as patch:
        patch.setattr(manager, '_normalize_amount', old_rate_validation)
        created = manager.add_transaction(data['a'], '2026-10-01', 'Legacy', 100000,
            'expense', '伙食', exchange_rate='.123456789', **options)
    session.commit()
    options.pop('trip_id', None)
    return created.transaction_id, options


@pytest.mark.parametrize('mode', ['daily', 'equal', 'custom'])
@pytest.mark.parametrize('explicit_same_rate', [False, True])
def test_metadata_edit_preserves_independently_rounded_legacy_values(
        command_db, monkeypatch, mode, explicit_same_rate):
    engine, data = command_db
    with Session(engine) as session:
        tid, options = legacy_transaction(session, data, monkeypatch, mode)
        before_splits = list(session.execute(select(transaction_splits_table).where(
            transaction_splits_table.c.transaction_id == tid).order_by(transaction_splits_table.c.id)))
        row = session.execute(select(transactions_table).where(transactions_table.c.id == tid)).one()
        assert row.exchange_rate == Decimal('.12345679')
        assert row.converted_amount == Decimal('12345.6789')
        assert session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == Decimal('87654.3211')
        if explicit_same_rate:
            options['exchange_rate'] = '.12345679'
        BudgetManager(session).update_transaction(data['a'], tid, '2026-10-01', 'Renamed', 100000,
            'expense', '伙食', **options)
        session.commit()
        row = session.execute(select(transactions_table).where(transactions_table.c.id == tid)).one()
        assert row.title == 'Renamed'
        assert row.exchange_rate == Decimal('.12345679')
        assert row.converted_amount == Decimal('12345.6789')
        assert session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == Decimal('87654.3211')
        assert list(session.execute(select(transaction_splits_table).where(
            transaction_splits_table.c.transaction_id == tid).order_by(transaction_splits_table.c.id))) == before_splits
        assert ReconciliationManager(session).reconcile()['summary']['mismatched'] == 0


def test_explicit_financial_edit_of_legacy_transaction_still_recalculates(command_db, monkeypatch):
    engine, data = command_db
    with Session(engine) as session:
        tid, options = legacy_transaction(session, data, monkeypatch, 'daily')
        BudgetManager(session).update_transaction(data['a'], tid, '2026-10-01', 'New amount', 200000,
            'expense', '伙食', **options)
        session.commit()
        row = session.execute(select(transactions_table).where(transactions_table.c.id == tid)).one()
        assert row.converted_amount == Decimal('24691.3580')
        assert session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == Decimal('75308.6420')
        assert ReconciliationManager(session).reconcile()['summary']['mismatched'] == 0


@pytest.mark.parametrize('change', ['members', 'allocations', 'rate'])
def test_explicit_trip_financial_changes_are_not_mistaken_for_metadata(command_db, monkeypatch, change):
    engine, data = command_db
    with Session(engine) as session:
        tid, options = legacy_transaction(session, data, monkeypatch, 'custom')
        if change == 'members':
            options.pop('split_allocations')
            options['split_member_ids'] = [data['am']]
        elif change == 'allocations':
            options['split_allocations'] = [dict(trip_member_id=data['am'], amount=70000),
                                             dict(trip_member_id=data['bm'], amount=30000)]
        else:
            options['exchange_rate'] = '.2'
        BudgetManager(session).update_transaction(data['a'], tid, '2026-10-01', 'Financial change', 100000,
            'expense', '伙食', **options)
        session.commit()
        rows = session.execute(select(transaction_splits_table).where(
            transaction_splits_table.c.transaction_id == tid)).all()
        total = session.scalar(select(transactions_table.c.converted_amount).where(transactions_table.c.id == tid))
        assert total == Decimal('20000' if change == 'rate' else '12345.6790')
        assert sum(row.converted_share_amount for row in rows) == total
        shares = {str(row.trip_member_id): row.share_amount for row in rows}
        assert shares == ({data['am']: Decimal('100000')} if change == 'members' else
                          {data['am']: Decimal('70000' if change == 'allocations' else '60000'),
                           data['bm']: Decimal('30000' if change == 'allocations' else '40000')})
        assert ReconciliationManager(session).reconcile()['summary']['mismatched'] == 0
