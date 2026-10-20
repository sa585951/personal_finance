from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from models.asset_manager import AssetManager
from models.schema import accounts_table, account_movements_table, financial_commands_table, transfers_table
from tests.test_ai_parse_api import FakeDBSession, _auth_headers, _load_web_app
from tests.test_financial_command_idempotency import command_db


TRANSACTION = dict(date='2026-10-01', item='Lunch', amount=91, type='expense', budget_category='伙食')
TRANSFER = dict(source_id='cash', dest_id='bank', amount=100, client_request_id=str(uuid4()))
CASES = [
    ('POST', '/api/assets', dict(bank_name='cash', account_type='cash', balance=100), 'asset_manager', 'add_account', 400),
    ('PUT', '/api/assets/cash', dict(bank_name='Cash'), 'asset_manager', 'update_account', 400),
    ('POST', '/api/assets/cash/adjustments', dict(new_balance=100, reason='test'), 'asset_manager', 'create_balance_adjustment', 400),
    ('DELETE', '/api/assets/cash', {}, 'asset_manager', 'delete_account', 404),
    ('POST', '/api/transfer', TRANSFER, 'asset_manager', 'create_transfer', 400),
    ('PUT', '/api/transfers/transfer-1', TRANSFER, 'asset_manager', 'update_transfer', 400),
    ('DELETE', '/api/transfers/transfer-1', {}, 'asset_manager', 'delete_transfer', 400),
    ('POST', '/api/trips/trip-1/settlements', dict(from_member_id='b', to_member_id='a', amount=100, client_request_id=str(uuid4())), 'budget_manager', 'create_trip_settlement', 400),
    ('PATCH', '/api/trips/trip-1/settlements/s1', dict(amount=100, settled_on='2026-10-02'), 'budget_manager', 'update_trip_settlement', 400),
    ('POST', '/api/trips/trip-1/settlements/s1/account-entry', dict(account_id='cash'), 'settlement_account_entry_manager', 'create_entry', 400),
    ('DELETE', '/api/trips/trip-1/settlements/s1/account-entry', {}, 'settlement_account_entry_manager', 'reverse_entry', 400),
    ('DELETE', '/api/trips/trip-1/settlements/s1', {}, 'budget_manager', 'delete_trip_settlement', 400),
    ('POST', '/api/budgets', dict(month='2026-10', category='伙食', amount=100), 'budget_manager', 'set_budget', 400),
    ('DELETE', '/api/budgets/2026-10/food', {}, 'budget_manager', 'delete_budget', 404),
    ('POST', '/api/transactions', TRANSACTION, 'transaction_service', 'create_transaction', 400),
    ('PUT', '/api/transactions/transaction-1', TRANSACTION, 'transaction_service', 'update_transaction', 400),
    ('DELETE', '/api/transactions/transaction-1', {}, 'transaction_service', 'delete_transaction', 404),
]


@pytest.mark.parametrize('method,path,payload,target,operation,validation_status', CASES)
@pytest.mark.parametrize('kind', ['database', 'unexpected', 'validation'])
def test_financial_write_errors_rollback_and_redact(monkeypatch, caplog, method, path, payload, target, operation, validation_status, kind):
    app = _load_web_app(monkeypatch)
    db = FakeDBSession()
    monkeypatch.setattr(app, 'db_session', db)
    secret = 'PRIVATE_FINANCIAL_PARAMETER'
    error = (IntegrityError('INSERT INTO private_ledger VALUES (:secret)', {'secret': secret}, RuntimeError('constraint '+secret))
             if kind == 'database' else RuntimeError(secret) if kind == 'unexpected' else ValueError('此操作不符合帳務規則'))

    def fail(*args, **kwargs):
        raise error

    manager = SimpleNamespace(**{operation: fail})
    if target == 'transaction_service':
        monkeypatch.setattr(app, 'get_transaction_service', lambda: manager)
    else:
        monkeypatch.setattr(app, target, manager)
    response = app.app.test_client().open(path, method=method, json=payload, headers=_auth_headers())
    assert response.status_code == (validation_status if kind == 'validation' else 500)
    assert response.get_json() == dict(success=False, message='此操作不符合帳務規則' if kind == 'validation' else '操作暫時無法完成，請稍後以原資料重試')
    assert secret not in response.get_data(as_text=True) + caplog.text
    assert 'INSERT INTO' not in response.get_data(as_text=True) + caplog.text
    assert db.rollbacks == 1 and db.commits == 0
    if kind != 'validation':
        endpoint, _ = app.app.url_map.bind('').match(path, method=method)
        assert f'operation={endpoint}' in caplog.text and type(error).__name__ in caplog.text


def test_original_same_account_transfer_rejected_without_db_effects(command_db, monkeypatch):
    engine, data = command_db
    app = _load_web_app(monkeypatch)
    # Keep the real manager/DB effects while the existing auth fixture isolates
    # this regression from an external identity provider.
    session = scoped_session(sessionmaker(bind=engine))
    manager = AssetManager(session)
    monkeypatch.setattr(app, 'asset_manager', manager)
    monkeypatch.setattr(app, 'db_session', session)
    monkeypatch.setattr(manager, 'create_transfer', lambda owner, *args, **kwargs:
                        AssetManager.create_transfer(manager, data['a'], *args, **kwargs))
    response = app.app.test_client().post('/api/transfer', json=dict(
        source_id=data['cash'], dest_id=data['cash'], amount=100, client_request_id=str(uuid4()),
    ), headers=_auth_headers())
    assert response.status_code == 400
    assert response.get_json() == dict(success=False, message='轉出和轉入帳戶不能是同一個')
    session.remove()
    with Session(engine) as session:
        for table in (transfers_table, account_movements_table, financial_commands_table):
            assert session.scalar(select(func.count()).select_from(table)) == 0
        assert session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == 1000


def test_line_parser_failure_does_not_log_webhook_or_exception_payload(monkeypatch, caplog):
    app = _load_web_app(monkeypatch)
    db = FakeDBSession()
    monkeypatch.setattr(app, 'db_session', db)
    secret = 'PRIVATE_WEBHOOK_TEXT_AND_REPLY_TOKEN'

    def fail(body, signature):
        assert secret in body
        raise RuntimeError('Invalid event: '+body+' signature='+signature)

    monkeypatch.setattr(app, 'linebot_manager', SimpleNamespace(parser=SimpleNamespace(parse=fail)))
    response = app.app.test_client().post('/line-webhook', json=dict(text=secret, replyToken=secret),
                                          headers={'X-Line-Signature': secret})
    assert response.status_code == 400
    assert secret not in response.get_data(as_text=True) + caplog.text
    assert 'LINE webhook parsing failed' in caplog.text
    assert db.commits == 0


def test_transfer_sql_failure_after_balance_write_rolls_back_and_retries(command_db, monkeypatch, caplog):
    engine, data = command_db
    app = _load_web_app(monkeypatch)
    session = scoped_session(sessionmaker(bind=engine))
    manager = AssetManager(session)
    monkeypatch.setattr(app, 'asset_manager', manager)
    monkeypatch.setattr(app, 'db_session', session)
    monkeypatch.setattr(manager, 'create_transfer', lambda owner, *args, **kwargs:
                        AssetManager.create_transfer(manager, data['a'], *args, **kwargs))
    original = manager._update_account_with_transfer_movement

    def fail_after_write(*args, **kwargs):
        original(*args, **kwargs)
        session.execute(text('SELECT 1 / 0 /* PRIVATE_SQL_PARAMETER */'))

    monkeypatch.setattr(manager, '_update_account_with_transfer_movement', fail_after_write)
    payload = dict(source_id=data['cash'], dest_id=data['bank'], amount=100, client_request_id=str(uuid4()))
    client = app.app.test_client()
    response = client.post('/api/transfer', json=payload, headers=_auth_headers())
    assert response.status_code == 500
    assert 'PRIVATE_SQL_PARAMETER' not in response.get_data(as_text=True) + caplog.text
    assert 'SELECT 1 / 0' not in response.get_data(as_text=True) + caplog.text
    with Session(engine) as proof:
        for table in (transfers_table, account_movements_table, financial_commands_table):
            assert proof.scalar(select(func.count()).select_from(table)) == 0
        assert proof.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == 1000
    monkeypatch.setattr(manager, '_update_account_with_transfer_movement', original)
    assert client.post('/api/transfer', json=payload, headers=_auth_headers()).status_code == 200
    with Session(engine) as proof:
        assert proof.scalar(select(func.count()).select_from(transfers_table)) == 1
        assert proof.scalar(select(func.count()).select_from(account_movements_table)) == 2
        assert proof.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == 900
        assert proof.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['bank'])) == 100
    session.remove()
