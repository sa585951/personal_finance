import re
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from tests.test_ai_parse_api import FakeDBSession, _auth_headers, _load_web_app


# The expected validation status is explicit: ownership/input failures keep
# their existing contract, while unexpected failures always return 500.
ENDPOINTS = [
    ('parse_ai_input', 500), ('get_ai_parse_events', 500),
    ('get_assets', 500), ('get_dashboard_overview', 500),
    ('get_asset_activity', 404), ('get_asset_adjustments', 404),
    ('get_recent_transfers', 500), ('get_portfolios', 500),
    ('create_portfolio', 400), ('get_portfolio', 400),
    ('update_portfolio', 400), ('delete_portfolio', 400),
    ('create_holding', 400), ('update_holding', 400), ('delete_holding', 400),
    ('create_holding_cost_entry', 400), ('update_holding_cost_entry', 400),
    ('delete_holding_cost_entry', 400), ('get_portfolio_snapshots', 400),
    ('create_portfolio_snapshot', 400), ('get_allocation_preview', 400),
    ('get_trips', 500), ('create_trip', 400), ('get_trip', 404),
    ('update_trip', 400), ('get_trip_overview', 404), ('get_trip_members', 404),
    ('add_trip_member', 400), ('delete_trip_member', 400),
    ('update_trip_member_role', 400), ('update_my_trip_monthly_report_preference', 400),
    ('leave_trip', 400), ('get_trip_invite', 404), ('create_trip_invite', 400),
    ('close_trip_invite', 400), ('accept_trip_invite', 400),
    ('get_trip_split_summary', 400), ('get_trip_split_state', 400),
    ('get_trip_settlement_suggestions', 400), ('get_trip_settlements', 400),
    ('archive_trip', 400), ('unarchive_trip', 400), ('restore_trip', 400),
    ('delete_trip', 400), ('get_budget_categories', 500),
    ('get_available_months', 500), ('get_transactions', 400),
    ('get_transaction_detail', 404), ('get_monthly_summary', 500),
    ('get_monthly_expenses', 500), ('get_asset_allocation', 500),
    ('get_income_expense_summary', 500), ('get_transactions_by_category_over_time', 500),
    ('get_overspending_warnings', 500),
]


@pytest.mark.parametrize('endpoint,validation_status', ENDPOINTS)
@pytest.mark.parametrize('kind', ['database', 'unexpected', 'validation'])
def test_api_errors_redact_private_data_and_preserve_validation(monkeypatch, caplog, endpoint, validation_status, kind):
    app = _load_web_app(monkeypatch)
    db = FakeDBSession()
    monkeypatch.setattr(app, 'db_session', db)
    secret = 'PRIVATE_SQL_PARAMETER_AND_PROVIDER_TOKEN'
    message = '此操作不符合資料規則'
    error = (IntegrityError('INSERT INTO private_data VALUES (:token)', {'token': secret}, RuntimeError(secret))
             if kind == 'database' else RuntimeError(secret) if kind == 'unexpected' else ValueError(message))
    calls = []

    class FailingManager:
        def __getattr__(self, name):
            def fail(*args, **kwargs):
                calls.append(name)
                raise error
            return fail

    manager = FailingManager()
    for target in ('asset_manager', 'budget_manager', 'trip_manager', 'asset_allocation_manager'):
        monkeypatch.setattr(app, target, manager)
    monkeypatch.setattr(app, 'linebot_manager', SimpleNamespace(
        message_parser=manager, ai_parse_event_manager=manager,
    ))
    # Resolve the registered URL so the test follows route renames, while the
    # security expectation and validation status remain independent constants.
    rule = next(rule for rule in app.app.url_map.iter_rules() if rule.endpoint == endpoint)
    path = re.sub(r'<(?:[^:>]+:)?([^>]+)>', lambda m: '2026-10' if m[1] == 'month' else 'resource-1', rule.rule)
    method = next(m for m in ('GET', 'POST', 'PATCH', 'PUT', 'DELETE') if m in rule.methods)
    payload = dict(text='Lunch 91', name='Test', start_date='2026-10-01', end_date='2026-10-02',
                   include_in_monthly_report=True, display_name='External', monthly_report_preference='include',
                   expires_in_days=30, amount=100)
    response = app.app.test_client().open(path, method=method, json=payload, headers=_auth_headers())
    assert calls, f'{endpoint} must reach the injected service boundary'
    status = validation_status if kind == 'validation' else 500
    assert response.status_code == status
    assert response.get_json() == dict(success=False, message=message if status != 500 else '操作暫時無法完成，請稍後以原資料重試')
    assert secret not in response.get_data(as_text=True) + caplog.text
    assert 'INSERT INTO' not in response.get_data(as_text=True) + caplog.text
    assert db.commits == 0
    if status == 500:
        assert db.rollbacks == 1
        assert f'operation={endpoint}' in caplog.text
        assert type(error).__name__ in caplog.text
