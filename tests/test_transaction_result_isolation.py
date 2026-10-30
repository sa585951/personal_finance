from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session,scoped_session,sessionmaker

from models.asset_manager import AssetManager
from models.ai_parse_event_manager import AIParseEventManager
from models.budget_manager import BudgetManager
from models.schema import transactions_table, ai_parse_events_table
from models.transaction_service import TransactionService
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def payload(title,key):
    return dict(date='2026-10-01',item=title,amount=10,type='expense',budget_category='伙食',client_request_id=str(key))


@pytest.mark.parametrize('replay_first',[False,True])
def test_shared_manager_returns_correct_id_and_replay_per_request(command_db,monkeypatch,replay_first):
    engine,data=command_db
    sessions=scoped_session(sessionmaker(bind=engine))
    manager=BudgetManager(sessions)
    service=TransactionService(manager)
    first=payload('First',uuid4())
    second=payload('Second',uuid4())
    if replay_first:
        service.create_transaction(data['a'],first)
        sessions.commit();sessions.remove()
    original=manager.add_transaction
    barrier=Barrier(2)
    def interleave(*args,**kwargs):
        result=original(*args,**kwargs)
        barrier.wait(timeout=5)
        return result
    monkeypatch.setattr(manager,'add_transaction',interleave)
    def create(p):
        try:
            result=service.create_transaction(data['a'],p)
            sessions.commit()
            return result
        finally: sessions.remove()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(create,first);b=pool.submit(create,second)
            results=[a.result(timeout=10),b.result(timeout=10)]
        assert results[0]['transaction_id']!=results[1]['transaction_id']
        assert [r['replayed'] for r in results]==[replay_first,False]
        with Session(engine) as s:
            for p,r in zip((first,second),results):
                row=s.execute(select(transactions_table).where(transactions_table.c.id==r['transaction_id'])).one()
                assert row.title==p['item'] and str(row.client_request_id)==p['client_request_id']
    finally: sessions.remove()


@pytest.mark.parametrize('kind',['account','budget'])
def test_nontransaction_creation_never_returns_prior_transaction_id(command_db,monkeypatch,kind):
    from tests.test_twd_monthly_reports import api_client
    engine,data=command_db
    client,headers=api_client(monkeypatch,engine,data)
    import web_app as app
    monkeypatch.setattr(app,'asset_manager',AssetManager(app.db_session))
    app.budget_manager.add_transaction(data['a'],'2026-10-01','Unrelated',10,'expense','伙食')
    events=AIParseEventManager(app.db_session)
    monkeypatch.setattr(app.linebot_manager,'ai_parse_event_manager',events)
    event=events.record_parse_event(data['a'],'web','Synthetic draft',{},'success',result_type='expense')
    app.db_session.commit()
    if kind=='account':
        path='/api/assets';body=dict(bank_name='Fresh',account_type='cash',balance=0)
    else:
        path='/api/budgets';body=dict(month='2026-10',category='伙食',amount=100)
    body.update(parse_event_id=str(event['id']),type='expense')
    response=client.post(path,json=body,headers=headers)
    assert response.status_code==201
    with Session(engine) as s:
        saved=s.execute(select(ai_parse_events_table).where(ai_parse_events_table.c.id==event['id'])).one()
        assert (response.json['data']['transaction_id'],saved.status,saved.result_id)==(None,'success',None)
