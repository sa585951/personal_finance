"""S4.1: request intent survives edits, retries and legacy-key migration."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.idempotency import IdempotencyConflict
from models.transaction_service import TransactionService
from models.schema import financial_commands_table, transactions_table, accounts_table, account_movements_table
from tests.test_financial_command_idempotency import command_db  # noqa: F401
from tests.test_financial_numeric_boundaries import snapshot
from tests.test_twd_monthly_reports import api_client


def payload(data, key):
    return dict(date='2026-10-01', item='Original intent', amount=100, type='expense',
                budget_category='伙食', account_id=data['cash'], client_request_id=str(key))


def create(session, data, key, **changes):
    return TransactionService(BudgetManager(session)).create_transaction(data['a'], {**payload(data,key), **changes})


def command_count(session):
    return session.scalar(select(func.count()).select_from(financial_commands_table).where(
        financial_commands_table.c.operation == 'transaction.create'))


@pytest.mark.parametrize('mutation', [dict(amount=101), dict(item='Other'), dict(description='Other'),
    dict(original_currency='USD',exchange_rate=1), dict(account_id=None), dict(review_status='pending'),
    dict(date='2026-10-02'), dict(timezone='UTC')])
def test_same_key_changed_intent_is_409_without_writes(command_db, monkeypatch, mutation):
    engine, data = command_db
    key = uuid4()
    with Session(engine) as session:
        create(session, data, key);session.commit();before = snapshot(session)
    client, headers = api_client(monkeypatch, engine, data)
    response = client.post('/api/transactions', json={**payload(data,key), **mutation}, headers=headers)
    assert response.status_code == 409
    with Session(engine) as session:
        assert snapshot(session) == before
        assert command_count(session) == 1


@pytest.mark.parametrize('state', ['unchanged', 'edited', 'deleted'])
def test_legacy_key_without_fingerprint_is_409_with_existing_id(command_db, monkeypatch, state):
    engine, data = command_db
    key = uuid4()
    with Session(engine) as session:
        result = create(session,data,key)
        # Simulate a pre-upgrade row: key exists, but there is no original command fingerprint.
        session.execute(delete(financial_commands_table))
        if state == 'edited':
            BudgetManager(session).update_transaction(data['a'],result['transaction_id'],'2026-10-01','Edited',50,
                'expense','伙食',account_id=data['cash'])
        elif state == 'deleted':
            BudgetManager(session).delete_transaction(data['a'],result['transaction_id'])
        session.commit();before=snapshot(session)
    client,headers=api_client(monkeypatch,engine,data)
    response=client.post('/api/transactions',json=payload(data,key),headers=headers)
    assert response.status_code == 409
    assert response.json['data']['transaction_id'] == str(result['transaction_id'])
    assert response.json['code'] == 'LEGACY_REQUEST_UNVERIFIABLE'
    with Session(engine) as session:
        assert snapshot(session)==before
        assert command_count(session)==0


@pytest.mark.parametrize('state',['edited','deleted'])
def test_original_intent_replays_after_transaction_changes(command_db,state):
    engine,data=command_db;key=uuid4()
    with Session(engine) as session:
        first=create(session,data,key);session.commit()
        if state=='edited':
            BudgetManager(session).update_transaction(data['a'],first['transaction_id'],'2026-10-01','Edited',50,
                'expense','伙食',account_id=data['cash'])
        else:
            BudgetManager(session).delete_transaction(data['a'],first['transaction_id'])
        session.commit();before=snapshot(session)
    with Session(engine) as session:
        replay=create(session,data,key,amount='100.0000');session.commit()
        assert replay['transaction_id']==first['transaction_id'] and replay['replayed']
        assert snapshot(session)==before
        assert command_count(session)==1
        with pytest.raises(IdempotencyConflict):create(session,data,key,amount=50)
        session.commit()
        assert snapshot(session)==before


def test_concurrent_retries_persist_one_command_and_one_effect(command_db):
    engine,data=command_db;key=uuid4();barrier=Barrier(4)
    def send(_):
        with Session(engine) as session:
            barrier.wait(timeout=8);result=create(session,data,key);session.commit();return result
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(send,range(4)))
    assert sum(not result['replayed'] for result in results)==1
    assert len({str(result['transaction_id']) for result in results})==1
    with Session(engine) as session:
        assert command_count(session)==1
        assert session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id==data['cash']))==900
        assert session.scalar(select(func.count()).select_from(account_movements_table))==1


def test_failure_rolls_back_command_with_ledger_and_allows_same_key_retry(command_db,monkeypatch):
    engine,data=command_db;key=uuid4();original=BudgetManager._apply_account_balance_delta
    def fail_after_write(*args,**kwargs):
        original(*args,**kwargs);raise RuntimeError('injected after movement')
    with Session(engine) as session:
        before=snapshot(session)
        with monkeypatch.context() as patch:
            patch.setattr(BudgetManager,'_apply_account_balance_delta',fail_after_write)
            with pytest.raises(RuntimeError):create(session,data,key)
        session.commit()
        assert snapshot(session)==before and command_count(session)==0
        result=create(session,data,key);session.commit()
        assert not result['replayed'] and command_count(session)==1
        assert session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id==data['cash']))==900


def test_same_key_isolated_by_user(command_db):
    engine,data=command_db;key=uuid4()
    with Session(engine) as session:
        first=create(session,data,key)
        second=TransactionService(BudgetManager(session)).create_transaction(data['b'],
            {**payload(data,key),'account_id':data['b_cash']})
        session.commit()
        assert first['transaction_id']!=second['transaction_id']
        assert not first['replayed'] and not second['replayed']
        assert command_count(session)==2


@pytest.mark.parametrize('trip',[False,True])
def test_replay_does_not_reinterpret_missing_rate_or_trip_defaults(command_db,monkeypatch,trip):
    engine,data=command_db;key=uuid4()
    options={'trip_id':data['trip'],'paid_by_member_id':data['am'],'split_member_ids':[data['am'],data['bm']]} if trip else {'original_currency':'USD'}
    with Session(engine) as session:
        first=create(session,data,key,amount=10,**options);session.commit();before=snapshot(session)
        def unexpected(*args,**kwargs):raise AssertionError('Replay re-evaluated changing defaults')
        monkeypatch.setattr(BudgetManager,'_default_exchange_rate',unexpected)
        monkeypatch.setattr(BudgetManager,'_resolve_trip_transaction_context',unexpected)
        replay=create(session,data,key,amount=10,**options);session.commit()
        assert replay['transaction_id']==first['transaction_id'] and replay['replayed']
        assert snapshot(session)==before and command_count(session)==1


def test_trip_split_order_is_canonical_but_changed_allocation_is_rejected(command_db):
    engine,data=command_db;key=uuid4()
    options=dict(trip_id=data['trip'],paid_by_member_id=data['am'],
                 split_allocations=[dict(trip_member_id=data['am'],amount=60),dict(trip_member_id=data['bm'],amount=40)])
    with Session(engine) as session:
        first=create(session,data,key,**options);session.commit()
        options['split_allocations'].reverse()
        replay=create(session,data,key,**options);session.commit()
        assert replay['replayed'] and replay['transaction_id']==first['transaction_id']
        before=snapshot(session)
        options['split_allocations'][0]['amount']=50
        options['split_allocations'][1]['amount']=50
        with pytest.raises(IdempotencyConflict):create(session,data,key,**options)
        session.commit();assert snapshot(session)==before


@pytest.mark.parametrize('change', ['trip_id', 'paid_by_member_id', 'split_member_ids'])
def test_changed_trip_context_or_split_members_are_conflicts(command_db, change):
    engine,data=command_db;key=uuid4()
    options=dict(trip_id=data['trip'],paid_by_member_id=data['am'],split_member_ids=[data['am'],data['bm']])
    with Session(engine) as session:
        first=create(session,data,key,**options);session.commit();before=snapshot(session)
        changed={**options,change: (None if change=='trip_id' else data['bm'] if change=='paid_by_member_id' else [data['am']])}
        with pytest.raises(IdempotencyConflict):create(session,data,key,**changed)
        session.commit();assert snapshot(session)==before
        options['split_member_ids'].reverse()
        replay=create(session,data,key,**options);session.commit()
        assert replay['replayed'] and replay['transaction_id']==first['transaction_id']


@pytest.mark.parametrize('actor', ['a', 'b'])
def test_expected_owner_mismatch_rejects_before_any_financial_write(command_db, monkeypatch, actor):
    engine, data = command_db
    auth_data = {**data, 'a': data[actor]}
    client, headers = api_client(monkeypatch, engine, auth_data)
    other = data['b' if actor == 'a' else 'a']
    headers['X-Nomica-Request-Owner'] = str(other)
    with Session(engine) as session:
        before = snapshot(session)
    request = payload(data, uuid4()); request['account_id'] = None
    response = client.post('/api/transactions', json=request, headers=headers)
    assert response.status_code == 409
    assert response.json['code'] == 'REQUEST_OWNER_CHANGED'
    with Session(engine) as session:
        assert snapshot(session) == before
        assert command_count(session) == 0


def test_matching_expected_owner_allows_original_request_replay(command_db, monkeypatch):
    engine, data = command_db
    client, headers = api_client(monkeypatch, engine, data)
    headers['X-Nomica-Request-Owner'] = str(data['a'])
    request = payload(data, uuid4())
    first = client.post('/api/transactions', json=request, headers=headers)
    replay = client.post('/api/transactions', json=request, headers=headers)
    assert first.status_code == 201 and replay.status_code == 200
    assert replay.json['replayed'] is True
    assert first.json['data']['transaction_id'] == replay.json['data']['transaction_id']
    with Session(engine) as session:
        assert command_count(session) == 1
