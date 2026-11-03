"""S4.1 public HTTP key gate; legacy internal calls stay explicitly compatible."""
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401
from tests.test_financial_numeric_boundaries import snapshot
from tests.test_transaction_request_integrity import payload, command_count
from tests.test_twd_monthly_reports import api_client


@pytest.mark.parametrize('trip', [False, True])
@pytest.mark.parametrize('value', ['omitted', None, '', ' ', False, 0, [], {}, 'not-a-uuid'])
def test_public_create_requires_a_valid_string_key_without_any_financial_effect(
        command_db, monkeypatch, trip, value):
    engine, data = command_db
    request = payload(data, uuid4())
    if trip:
        request.update(trip_id=data['trip'], paid_by_member_id=data['am'], split_member_ids=[data['am']])
    if value == 'omitted': request.pop('client_request_id')
    else: request['client_request_id'] = value
    with Session(engine) as session:
        before = snapshot(session)
    client, headers = api_client(monkeypatch, engine, data)
    response = client.post('/api/transactions', json=request, headers=headers)
    assert response.status_code == 400
    assert response.json['success'] is False
    with Session(engine) as session:
        session.commit()
        assert snapshot(session) == before
        assert command_count(session) == 0


def test_internal_without_key_remains_compatible_and_not_claimed_idempotent(command_db):
    engine, data = command_db
    with Session(engine) as session:
        result = BudgetManager(session).add_transaction(data['a'], '2026-11-03', 'Internal legacy',
            100, 'expense', '伙食', account_id=data['cash'])
        session.commit()
        assert result[0] is True and result.transaction_id and result.replayed is False
        assert command_count(session) == 0


def test_owner_mismatch_precedes_missing_key_and_preserves_original_intent(command_db, monkeypatch):
    engine, data = command_db
    client, headers = api_client(monkeypatch, engine, data)
    headers['X-Nomica-Request-Owner'] = str(data['b'])
    request = payload(data, uuid4()); request.pop('client_request_id')
    with Session(engine) as session:
        before = snapshot(session)
    response = client.post('/api/transactions', json=request, headers=headers)
    assert response.status_code == 409
    assert response.json['code'] == 'REQUEST_OWNER_CHANGED'
    with Session(engine) as session:
        assert snapshot(session) == before
        assert command_count(session) == 0
