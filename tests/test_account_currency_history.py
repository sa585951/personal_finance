import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.schema import accounts_table, account_balance_anchors_table, account_movements_table, transactions_table
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def snapshot(session):
    return [list(session.execute(select(t).order_by(t.c.id))) for t in (
        accounts_table,account_balance_anchors_table,account_movements_table,transactions_table)]


@pytest.mark.parametrize('state',['zero_new','existing_transaction','deleted_zeroed'])
def test_currency_change_rejected_before_any_account_or_history_write(command_db,state):
    engine,data=command_db
    with Session(engine) as session:
        assets=AssetManager(session)
        target=data['bank'] if state=='zero_new' else data['cash']
        if state!='zero_new':
            m=BudgetManager(session)
            m.add_transaction(data['a'],'2026-10-01','History',100,'expense','伙食',account_id=target)
            if state=='deleted_zeroed':
                m.delete_transaction(data['a'],m.last_created_transaction_id)
                assets.create_balance_adjustment(data['a'],target,0,reason='balance_correction')
        session.commit()
        before=snapshot(session)
        with pytest.raises(ValueError,match='幣別'):
            assets.update_account(data['a'],target,currency='USD',bank_name='Must not change',balance=20)
        session.commit()
    with Session(engine) as session:
        assert snapshot(session)==before


def test_same_currency_allows_name_update(command_db):
    engine,data=command_db
    with Session(engine) as session:
        assert AssetManager(session).update_account(data['a'],data['cash'],currency='TWD',bank_name='Renamed')[0]
        session.commit()
        row=session.execute(select(accounts_table).where(accounts_table.c.id==data['cash'])).one()
        assert row.name=='Renamed' and row.currency=='TWD' and row.balance==1000


def test_other_user_cannot_relabel_account(command_db):
    engine,data=command_db
    with Session(engine) as session:
        before=snapshot(session)
        with pytest.raises(ValueError,match='權限'):
            AssetManager(session).update_account(data['b'],data['cash'],currency='USD')
        session.commit()
        assert snapshot(session)==before


def test_currency_change_http_is_clear_400_and_preserves_history(command_db,monkeypatch):
    from tests.test_twd_monthly_reports import api_client
    engine,data=command_db
    client,headers=api_client(monkeypatch,engine,data)
    import web_app
    monkeypatch.setattr(web_app,'asset_manager',AssetManager(web_app.db_session))
    with Session(engine) as session: before=snapshot(session)
    response=client.put('/api/assets/'+data['cash'],json={'currency':'USD','bank_name':'No'},headers=headers)
    assert response.status_code==400
    assert '幣別' in response.json['message'] and '另建' in response.json['message']
    with Session(engine) as session: assert snapshot(session)==before
