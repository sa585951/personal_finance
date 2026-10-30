from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.trip_manager import TripManager
from models.schema import transactions_table, transaction_splits_table
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def foreign_split(session, data, *, day='2026-10-01', own_share=True):
    trips = TripManager(session)
    trip = trips.create_trip(data['a'], 'USD test', '2026-10-01', '2026-11-03',
        base_currency='USD', default_currency='USD', include_in_monthly_report=True)['id']
    if not own_share:
        trips.accept_invite(data['b'], trips.create_invite(data['a'], trip)['token'])
    members = {m['user_id']: m['id'] for m in trips.list_trip_members(data['a'], trip)}
    manager = BudgetManager(session)
    manager.add_transaction(data['a'], day, 'USD share', 20, 'expense', '伙食',
        trip_id=trip, paid_by_member_id=members[str(data['a'])],
        split_member_ids=[members[str(data['a'] if own_share else data['b'])]],
        original_currency='USD', exchange_rate=1,
        split_allocations=None if own_share else [dict(trip_member_id=members[str(data['b'])], amount=20)])
    return trip, manager.last_created_transaction_id


def read_report(manager, user, kind):
    if kind == 'monthly': return manager.calculate_monthly_report_expenses(user, '2026-10')
    if kind == 'budget': return manager.get_budget_summary(user, '2026-10')
    if kind == 'history': return manager.get_transactions_by_category_over_time(user)
    return manager.get_all_transactions(user, monthly_report=True, month='2026-10',
                                        limit=1, return_pagination=True)


@pytest.mark.parametrize('kind', ['monthly', 'budget', 'history', 'projection'])
def test_foreign_base_share_rejects_twd_report_without_rewriting_data(command_db, kind):
    engine, data = command_db
    with Session(engine) as session:
        foreign_split(session, data)
        manager = BudgetManager(session)
        manager.add_transaction(data['a'], '2026-10-02', 'Newer TWD', 100, 'expense', '伙食')
        session.commit()
        before = [list(session.execute(select(t).order_by(t.c.id)))
                  for t in (transactions_table, transaction_splits_table)]
        with pytest.raises(ValueError, match='TWD'):
            read_report(manager, data['a'], kind)
        session.commit()
        assert before == [list(session.execute(select(t).order_by(t.c.id)))
                          for t in (transactions_table, transaction_splits_table)]
        # Travel and ordinary lists still expose original currencies safely.
        assert manager.get_all_transactions(data['a'], include_trips=True)


@pytest.mark.parametrize('reason', ['exclude', 'no_share', 'deleted', 'other_month'])
def test_ineligible_foreign_share_does_not_block_month(command_db, reason):
    engine, data = command_db
    with Session(engine) as session:
        trip, tid = foreign_split(session, data, own_share=reason!='no_share',
                                  day='2026-11-01' if reason=='other_month' else '2026-10-01')
        if reason == 'exclude':
            TripManager(session).update_current_member_monthly_report_preference(data['a'], trip, 'exclude')
        elif reason == 'deleted':
            BudgetManager(session).delete_transaction(data['a'], tid)
        session.commit()
        manager = BudgetManager(session)
        assert manager.calculate_monthly_report_expenses(data['a'], '2026-10')['伙食'] == Decimal('500')
        assert manager.get_all_transactions(data['a'], monthly_report=True, month='2026-10')


def test_foreign_original_currency_converted_to_twd_is_allowed(command_db):
    engine, data = command_db
    with Session(engine) as session:
        manager = BudgetManager(session)
        manager.add_transaction(data['a'], '2026-10-02', 'JPY in TWD trip', 100, 'expense', '伙食',
            trip_id=data['trip'], paid_by_member_id=data['am'], split_member_ids=[data['am']],
            original_currency='JPY', exchange_rate=Decimal('.22'))
        session.commit()
        assert manager.calculate_monthly_report_expenses(data['a'], '2026-10')['伙食'] == Decimal('522')
        rows = manager.get_all_transactions(data['a'], monthly_report=True, month='2026-10')
        assert next(r for r in rows if r['currency']=='JPY')['base_currency']=='TWD'


def api_client(monkeypatch, engine, data):
    from sqlalchemy.orm import scoped_session, sessionmaker
    from tests.test_ai_parse_api import _load_web_app, _auth_token
    app = _load_web_app(monkeypatch)
    sessions = scoped_session(sessionmaker(bind=engine))
    monkeypatch.setattr(app, 'db_session', sessions)
    monkeypatch.setattr(app, 'budget_manager', BudgetManager(sessions))
    monkeypatch.setattr(app, 'trip_manager', TripManager(sessions))
    app.auth_session_manager.sessions['aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa']['user_id'] = data['a']
    headers = {'Authorization': 'Bearer '+_auth_token(user_id=str(data['a']))}
    return app.app.test_client(), headers


@pytest.mark.parametrize('path', [
    '/api/transactions?monthly_report=true&month=2026-10&limit=1',
    '/api/dashboard/overview', '/api/budgets/summary/2026-10',
    '/api/reports/monthly_expenses?month=2026-10',
    '/api/reports/income_expense_summary?month=2026-10',
    '/api/reports/transactions_by_category_over_time',
    '/api/reports/overspending_warnings?month=2026-10',
])
def test_report_api_returns_clear_validation_error_instead_of_wrong_total(command_db, monkeypatch, path):
    engine, data = command_db
    with Session(engine) as session:
        foreign_split(session, data)
        session.commit()
    client, headers = api_client(monkeypatch, engine, data)
    response = client.get(path, headers=headers)
    assert response.status_code == 400
    assert response.json['success'] is False
    assert 'TWD' in response.json['message']
    assert 'data' not in response.json


def test_income_summary_month_filter_is_applied_before_currency_validation(command_db, monkeypatch):
    engine, data = command_db
    with Session(engine) as session:
        foreign_split(session, data, day='2026-11-01')
        session.commit()
    client, headers = api_client(monkeypatch, engine, data)
    response = client.get('/api/reports/income_expense_summary?month=2026-10', headers=headers)
    assert response.status_code == 200
    assert response.json['data']['datasets'][0]['data'] == [0, 500]
