"""N04: original account-create intent and account/anchor/billing atomicity."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.asset_manager import AssetManager
from models.schema import (accounts_table, account_balance_anchors_table, credit_card_billing_profiles_table,
                           account_adjustments_table, financial_commands_table, account_movements_table)
from tests.test_financial_command_idempotency import command_db  # noqa: F401
from tests.test_twd_monthly_reports import api_client


def asset_client(monkeypatch, engine, data):
    client, headers = api_client(monkeypatch, engine, data)
    import web_app
    monkeypatch.setattr(web_app, 'asset_manager', AssetManager(web_app.db_session))
    return client, headers


def account_snapshot(session):
    return [list(session.execute(select(t).order_by(*t.primary_key.columns))) for t in (
        accounts_table, account_balance_anchors_table, credit_card_billing_profiles_table,
        account_adjustments_table, financial_commands_table, account_movements_table)]


def account_payload(key, **changes):
    return {"bank_name": "Request account", "account_type": "cash", "balance": 100,
            "currency": "TWD", "client_request_id": str(key), **changes}


def create(session, user, key, **changes):
    options=dict(bank_name='Request account',account_type='cash',balance=100,currency='TWD')
    options.update(changes)
    return AssetManager(session).add_account(user,client_request_id=key,**options)


def matching_accounts(session, name='Request account'):
    return session.execute(select(accounts_table).where(accounts_table.c.name==name)).all()


@pytest.mark.parametrize('account_type,balance,currency', [('cash',0,'TWD'),('bank','125.25','USD'),('credit_card',-30,'TWD')])
def test_api_same_key_creates_exactly_one_account_and_opening_anchor(command_db,monkeypatch,account_type,balance,currency):
    engine,data=command_db;key=uuid4()
    client,headers=asset_client(monkeypatch,engine,data)
    body=account_payload(key);body.update(account_type=account_type,balance=balance,currency=currency)
    first=client.post('/api/assets',json=body,headers=headers)
    body['balance'] = '-0.0000' if balance == 0 else format(Decimal(str(balance)), '.4f')
    replay=client.post('/api/assets',json=body,headers=headers)
    with Session(engine) as session:
        rows=matching_accounts(session)
        assert len(rows)==1, 'Two retries must not create duplicate accounts'
        anchors=session.execute(select(account_balance_anchors_table).where(account_balance_anchors_table.c.account_id==rows[0].id)).all()
        assert len(anchors)==1 and anchors[0].balance==Decimal(str(balance)) and anchors[0].currency==currency
    assert first.status_code==201 and replay.status_code==200
    assert first.json['data']['account_id']==replay.json['data']['account_id']==str(rows[0].id)
    assert first.json['data']['transaction_id'] is None and replay.json['replayed'] is True


@pytest.mark.parametrize('change', [dict(bank_name='Other'),dict(balance=101),dict(currency='USD'),dict(account_type='bank'),
    dict(icon_key='bank'),dict(color_key='rose'),dict(credit_card_billing={'closing_day':6,'due_day':20,'due_month_offset':1})])
def test_changed_account_intent_is_409_without_mutation(command_db,monkeypatch,change):
    engine,data=command_db;key=uuid4()
    client,headers=asset_client(monkeypatch,engine,data)
    body=account_payload(key);body.update(account_type='credit_card',credit_card_billing={'closing_day':5,'due_day':20,'due_month_offset':1})
    assert client.post('/api/assets',json=body,headers=headers).status_code==201
    with Session(engine) as session:before=account_snapshot(session)
    response=client.post('/api/assets',json={**body,**change},headers=headers)
    assert response.status_code==409
    with Session(engine) as session:assert account_snapshot(session)==before


@pytest.mark.parametrize('key',['omitted',None,'',[],{},False,'not-a-uuid'])
def test_public_account_create_requires_valid_key_and_is_zero_effect(command_db,monkeypatch,key):
    engine,data=command_db;client,headers=asset_client(monkeypatch,engine,data)
    body=account_payload(uuid4())
    if key=='omitted':body.pop('client_request_id')
    else:body['client_request_id']=key
    with Session(engine) as session:before=account_snapshot(session)
    response=client.post('/api/assets',json=body,headers=headers)
    assert response.status_code==400
    with Session(engine) as session:assert account_snapshot(session)==before


@pytest.mark.parametrize('balance',['1e1000000','NaN','1.00001','100000000000000'])
def test_unrepresentable_opening_balance_is_400_before_reservation(command_db,monkeypatch,balance):
    engine,data=command_db;client,headers=asset_client(monkeypatch,engine,data)
    with Session(engine) as session:before=account_snapshot(session)
    body=account_payload(uuid4());body['balance']=balance
    response=client.post('/api/assets',json=body,headers=headers)
    assert response.status_code==400
    with Session(engine) as session:assert account_snapshot(session)==before


def test_account_create_binds_original_owner_to_authenticated_post(command_db,monkeypatch):
    engine,data=command_db;client,headers=asset_client(monkeypatch,engine,data)
    headers['X-Nomica-Request-Owner']=str(data['b'])
    with Session(engine) as session:before=account_snapshot(session)
    response=client.post('/api/assets',json=account_payload(uuid4()),headers=headers)
    assert response.status_code==409 and response.json['code']=='REQUEST_OWNER_CHANGED'
    with Session(engine) as session:assert account_snapshot(session)==before


def test_parallel_account_retries_create_one_result_and_one_anchor(command_db):
    engine,data=command_db;key=uuid4();barrier=Barrier(4)
    def send(_):
        with Session(engine) as session:
            barrier.wait(timeout=8);result=create(session,data['a'],key);session.commit();return result
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(send,range(4)))
    assert sum(not r.replayed for r in results)==1
    assert len({r.account_id for r in results})==1
    with Session(engine) as session:
        assert len(matching_accounts(session))==1
        assert session.scalar(select(func.count()).select_from(account_balance_anchors_table).where(account_balance_anchors_table.c.account_id==results[0].account_id))==1


def test_account_anchor_billing_and_command_rollback_together(command_db,monkeypatch):
    engine,data=command_db;key=uuid4();original=AssetManager._save_credit_card_billing
    def fail(*args,**kwargs):original(*args,**kwargs);raise RuntimeError('Injected after billing')
    options=dict(account_type='credit_card',credit_card_billing={'closing_day':5,'due_day':20,'due_month_offset':1})
    with Session(engine) as session:
        before=account_snapshot(session)
        with monkeypatch.context() as patch:
            patch.setattr(AssetManager,'_save_credit_card_billing',fail)
            with pytest.raises(RuntimeError):create(session,data['a'],key,**options)
        session.commit();assert account_snapshot(session)==before
        result=create(session,data['a'],key,**options);session.commit()
        assert result[0] and not result.replayed
        assert session.scalar(select(func.count()).select_from(credit_card_billing_profiles_table))==1


@pytest.mark.parametrize('state',['edited','deleted'])
def test_replay_never_resets_new_balance_or_revives_deleted_account(command_db,state):
    engine,data=command_db;key=uuid4()
    with Session(engine) as session:
        result=create(session,data['a'],key);session.commit()
        manager=AssetManager(session)
        if state=='edited':manager.update_account(data['a'],result.account_id,bank_name='Renamed',balance=200)
        else:manager.delete_account(data['a'],result.account_id)
        session.commit();before=account_snapshot(session)
    with Session(engine) as session:
        replay=create(session,data['a'],key);session.commit()
        assert replay.replayed and replay.account_id==result.account_id
        assert account_snapshot(session)==before


def test_same_key_is_owner_scoped_and_distinct_keys_do_not_guess_by_name(command_db):
    engine,data=command_db;key=uuid4()
    with Session(engine) as session:
        results=[create(session,data['a'],key),create(session,data['b'],key),create(session,data['a'],uuid4())]
        session.commit()
        assert len({r.account_id for r in results})==3
        assert all(not r.replayed for r in results)
        assert len(matching_accounts(session))==3


def test_billing_replay_keeps_original_date_intent_after_today_changes(command_db,monkeypatch):
    engine,data=command_db;key=uuid4();year=date.today().year+2
    billing=dict(closing_day=5,due_day=20,due_month_offset=1,override_closing_date=f'{year}-01-05',override_due_date=f'{year}-02-20')
    with Session(engine) as session:
        first=create(session,data['a'],key,account_type='credit_card',credit_card_billing=billing);session.commit()
        monkeypatch.setattr(AssetManager,'_user_today',lambda *_: date(year+1,1,1))
        replay=create(session,data['a'],key,account_type='credit_card',credit_card_billing=billing);session.commit()
        assert replay.replayed and replay.account_id==first.account_id
        assert session.scalar(select(credit_card_billing_profiles_table.c.override_due_date).where(credit_card_billing_profiles_table.c.account_id==first.account_id))==date(year,2,20)


def test_internal_create_without_key_remains_two_value_compatible(command_db):
    engine,data=command_db
    with Session(engine) as session:
        success,message=AssetManager(session).add_account(data['a'],'Internal','cash',0)
        session.commit();assert success and message
        assert session.scalar(select(func.count()).select_from(financial_commands_table))==0


def test_negative_cash_opening_balance_rejects_and_releases_key(command_db, monkeypatch):
    engine, data = command_db
    client, headers = asset_client(monkeypatch, engine, data)
    body = account_payload(uuid4(), balance=-1)
    with Session(engine) as session:
        before = account_snapshot(session)
    response = client.post('/api/assets', json=body, headers=headers)
    assert response.status_code == 400
    with Session(engine) as session:
        assert account_snapshot(session) == before
    response = client.post('/api/assets', json={**body, "balance": 1}, headers=headers)
    assert response.status_code == 201
