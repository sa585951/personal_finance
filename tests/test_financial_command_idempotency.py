from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.engine import make_url

from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.idempotency import IdempotencyConflict
from models.reconciliation_manager import ReconciliationManager
from models.schema import (
    metadata, accounts_table, account_movements_table, financial_commands_table,
    transfers_table, settlements_table,
)
from models.seed_data import seed_reference_data
from models.settlement_account_entry_manager import SettlementAccountEntryManager
from models.trip_manager import TripManager
from models.user_manager import UserManager
from tests.test_schema_smoke import _get_test_database_url


@pytest.fixture
def command_db():
    url = _get_test_database_url()
    parsed = make_url(url)
    # These destructive regressions never honor a non-local smoke-test override.
    if parsed.host not in {'localhost', '127.0.0.1'} or not parsed.database.endswith('_test'):
        pytest.fail('Financial command regression requires a loopback *_test database')
    engine = create_engine(url)
    with engine.begin() as c:
        metadata.drop_all(c)
        metadata.create_all(c)
        seed_reference_data(c)
        users = UserManager(c)
        a = users.get_or_create_user_for_identity('qa', 'commands-A', 'A')['id']
        b = users.get_or_create_user_for_identity('qa', 'commands-B', 'B')['id']
        assets = AssetManager(c)
        assets.add_account(a, 'cash', 'cash', 1000, currency='TWD')
        assets.add_account(a, 'bank', 'bank', 0, currency='TWD')
        assets.add_account(b, 'B cash', 'cash', 1000, currency='TWD')
        a_assets = assets.get_all_assets(a)
        cash = next(x['id'] for x in a_assets.values() if x['bank_name'] == 'cash')
        bank = next(x['id'] for x in a_assets.values() if x['bank_name'] == 'bank')
        b_cash = next(iter(assets.get_all_assets(b).values()))['id']
        trips = TripManager(c)
        trip = trips.create_trip(a, 'Commands', '2026-10-01', '2026-10-03', include_in_monthly_report=True)['id']
        invite = trips.create_invite(a, trip)
        trips.accept_invite(b, invite['token'])
        members = {x['user_id']: x['id'] for x in trips.list_trip_members(a, trip)}
        am, bm = members[str(a)], members[str(b)]
        BudgetManager(c).add_transaction(a, '2026-10-01', 'Dinner', 1000, 'expense', '伙食',
            trip_id=trip, paid_by_member_id=am, split_member_ids=[am, bm])
    yield engine, dict(a=a, b=b, cash=cash, bank=bank, b_cash=b_cash, trip=trip, am=am, bm=bm)
    engine.dispose()


def apply(session, data, kind, key, amount=100):
    if kind == 'transfer':
        return AssetManager(session).create_transfer(data['a'], data['cash'], data['bank'], amount, client_request_id=key)
    return BudgetManager(session).create_trip_settlement(data['a'], data['trip'], data['bm'], data['am'],
        amount, settled_on='2026-10-02', client_request_id=key)


def assert_effects(engine, data, kind):
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(financial_commands_table)) == 1
        table = transfers_table if kind == 'transfer' else settlements_table
        assert s.scalar(select(func.count()).select_from(table)) == 1
        balances = {str(r.id): r.balance for r in s.execute(select(accounts_table.c.id, accounts_table.c.balance))}
        assert balances[data['cash']] == (900 if kind == 'transfer' else 1000)
        assert balances[data['bank']] == (100 if kind == 'transfer' else 0)
        assert s.scalar(select(func.count()).select_from(account_movements_table)) == (2 if kind == 'transfer' else 0)
        assert ReconciliationManager(s).reconcile()['summary']['mismatched'] == 0
        if kind == 'settlement':
            summary = BudgetManager(s).get_trip_split_summary(data['a'], data['trip'])
            assert next(r['net_amount'] for r in summary if r['member_id'] == data['bm']) == -400


@pytest.mark.parametrize('kind', ['transfer', 'settlement'])
def test_replay_survives_new_session_and_rejects_changed_payload(command_db, kind):
    engine, data = command_db
    key = uuid4()
    with Session(engine) as s:
        first = apply(s, data, kind, key)
        s.commit()  # Pretend the response is lost after the committed transaction.
    with Session(engine) as s:
        replay = apply(s, data, kind, key, amount='100.0000')
        s.commit()
        assert replay['replayed'] and not first['replayed']
        field = kind + '_id'
        assert first[field] == replay[field]
        with pytest.raises(IdempotencyConflict):
            apply(s, data, kind, key, amount=101)
        s.commit()
    assert_effects(engine, data, kind)


@pytest.mark.parametrize('kind', ['transfer', 'settlement'])
def test_fresh_concurrent_retries_commit_once(command_db, kind):
    engine, data = command_db
    key, barrier = uuid4(), Barrier(6)
    def send(_):
        with Session(engine) as s:
            barrier.wait(timeout=5)
            result = apply(s, data, kind, key)
            s.commit()
            return result
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(send, range(6)))
    assert sum(not r['replayed'] for r in results) == 1
    assert len({r[kind + '_id'] for r in results}) == 1
    assert_effects(engine, data, kind)


def test_distinct_concurrent_transfers_use_current_balances(command_db):
    engine, data = command_db
    barrier = Barrier(2)
    def send(amount):
        with Session(engine) as s:
            barrier.wait(timeout=5)
            result = apply(s, data, 'transfer', uuid4(), amount)
            s.commit()
            return result
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, [100, 200]))
    assert len({r['transfer_id'] for r in results}) == 2
    with Session(engine) as s:
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == 700
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['bank'])) == 300


@pytest.mark.parametrize('operation', ['update', 'delete'])
def test_transfer_create_interleaves_safely_with_existing_edit_or_delete(command_db, operation):
    engine, data = command_db
    with Session(engine) as s:
        original = apply(s, data, 'transfer', uuid4())['transfer_id']
        s.commit()
    barrier = Barrier(2)
    def create():
        with Session(engine) as s:
            barrier.wait(timeout=5)
            apply(s, data, 'transfer', uuid4(), 50)
            s.commit()
    def mutate():
        with Session(engine) as s:
            manager = AssetManager(s)
            barrier.wait(timeout=5)
            if operation == 'update':
                manager.update_transfer(data['a'], original, data['cash'], data['bank'], 150)
            else:
                manager.delete_transfer(data['a'], original)
            s.commit()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create), pool.submit(mutate)]
        for future in futures:
            future.result(timeout=10)
    with Session(engine) as s:
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == (800 if operation == 'update' else 950)
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['bank'])) == (200 if operation == 'update' else 50)
        assert ReconciliationManager(s).reconcile()['summary']['mismatched'] == 0


@pytest.mark.parametrize('kind', ['transfer', 'settlement'])
def test_failure_rolls_back_command_and_all_effects_then_allows_retry(command_db, monkeypatch, kind):
    engine, data = command_db
    key = uuid4()
    cls, method = (AssetManager, '_update_account_with_transfer_movement') if kind == 'transfer' else (BudgetManager, 'add_trip_settlement')
    original = getattr(cls, method)
    def fail_after_write(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('Injected failure after a ledger write')
    monkeypatch.setattr(cls, method, fail_after_write)
    with Session(engine) as s:
        with pytest.raises(RuntimeError):
            apply(s, data, kind, key)
        s.commit()
        assert s.scalar(select(func.count()).select_from(financial_commands_table)) == 0
        assert s.scalar(select(func.count()).select_from(transfers_table)) == 0
        assert s.scalar(select(func.count()).select_from(settlements_table)) == 0
        assert s.scalar(select(func.count()).select_from(account_movements_table)) == 0
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == 1000
    monkeypatch.setattr(cls, method, original)
    with Session(engine) as s:
        apply(s, data, kind, key)
        s.commit()
    assert_effects(engine, data, kind)


def test_group_replay_does_not_change_private_postings_or_resurrect_void(command_db):
    engine, data = command_db
    key = uuid4()
    with Session(engine) as s:
        result = apply(s, data, 'settlement', key)
        sid = result['settlement_id']
        entries = SettlementAccountEntryManager(s)
        entries.create_entry(data['a'], data['trip'], sid, data['bank'])
        entries.create_entry(data['b'], data['trip'], sid, data['b_cash'])
        s.commit()
        replay = apply(s, data, 'settlement', key)
        assert replay['settlement_id'] == sid and replay['replayed']
        s.commit()
        with pytest.raises(ValueError):
            BudgetManager(s).delete_trip_settlement(data['a'], data['trip'], sid)
        s.rollback()
        entries.reverse_entry(data['a'], data['trip'], sid, reason='test')
        entries.reverse_entry(data['b'], data['trip'], sid, reason='test')
        s.commit()
        BudgetManager(s).delete_trip_settlement(data['a'], data['trip'], sid)
        s.commit()
        assert apply(s, data, 'settlement', key)['settlement_id'] == sid
        s.commit()
        assert s.scalar(select(settlements_table.c.status).where(settlements_table.c.id == sid)) == 'voided'
        assert s.scalar(select(func.count()).select_from(settlements_table)) == 1
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['bank'])) == 0
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['b_cash'])) == 1000
