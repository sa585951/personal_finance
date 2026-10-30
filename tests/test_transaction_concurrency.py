"""R03: independent transactions must serialize account effects on PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.reconciliation_manager import ReconciliationManager
from models.schema import accounts_table, transactions_table
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def create(s, d, amount=100, account=None):
    m = BudgetManager(s)
    m.add_transaction(d['a'], '2026-10-01', 'S2', amount, 'expense', '伙食',
                      account_id=account or d['cash'], client_request_id=uuid4())
    return m.last_created_transaction_id


def concurrent(*jobs):
    barrier = Barrier(len(jobs))
    def run(job):
        barrier.wait(timeout=5)
        return job()
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [pool.submit(run, job) for job in jobs]
        return [f.result(timeout=15) for f in futures]


def balance(engine, account):
    with Session(engine) as s:
        assert ReconciliationManager(s).reconcile()['summary']['mismatched'] == 0
        return s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == account))


def test_distinct_creates_preserve_all_effects(command_db, monkeypatch):
    engine, d = command_db
    original = BudgetManager._get_account_for_balance_update
    def slow_read(*args):
        row = original(*args)
        sleep(.04)  # Expose a stale read if the account lock is removed.
        return row
    monkeypatch.setattr(BudgetManager, '_get_account_for_balance_update', slow_read)
    def send():
        with Session(engine) as s:
            result = create(s, d)
            s.commit()
            return result
    assert len(set(concurrent(*[send for _ in range(4)]))) == 4
    assert balance(engine, d['cash']) == 600


def test_transaction_and_transfer_share_account_lock(command_db):
    engine, d = command_db
    def transaction():
        with Session(engine) as s:
            create(s, d, 200)
            s.commit()
    def transfer():
        with Session(engine) as s:
            AssetManager(s).create_transfer(d['a'], d['cash'], d['bank'], 100, client_request_id=uuid4())
            s.commit()
    concurrent(transaction, transfer)
    assert balance(engine, d['cash']) == 700
    assert balance(engine, d['bank']) == 100


@pytest.mark.parametrize('operations', [('delete','delete'), ('update','update'), ('update','delete')])
def test_same_transaction_mutations_use_current_row(command_db, operations):
    engine, d = command_db
    with Session(engine) as s:
        tid = create(s, d)
        s.commit()
    def job(operation, amount):
        def run():
            with Session(engine) as s:
                try:
                    m = BudgetManager(s)
                    if operation == 'delete': m.delete_transaction(d['a'], tid)
                    else: m.update_transaction(d['a'], tid, '2026-10-01', 'S2', amount,
                                               'expense', '伙食', account_id=d['cash'])
                    s.commit()
                except ValueError as exc:
                    s.rollback()
                    assert '找不到' in str(exc)
        return run
    concurrent(*[job(op, 150+i*50) for i, op in enumerate(operations)])
    with Session(engine) as s:
        row = s.execute(select(transactions_table).where(transactions_table.c.id == tid)).first()
        expected = 1000 if row.deleted_at else 1000-row.original_amount
    assert balance(engine, d['cash']) == expected


def test_opposite_account_edits_follow_same_lock_order(command_db):
    engine, d = command_db
    with Session(engine) as s:
        AssetManager(s).create_transfer(d['a'], d['cash'], d['bank'], 500, client_request_id=uuid4())
        a, b = create(s, d, 100), create(s, d, 100, d['bank'])
        s.commit()
    def job(tid, account):
        def run():
            with Session(engine) as s:
                BudgetManager(s).update_transaction(d['a'], tid, '2026-10-01', 'S2', 100,
                                                    'expense', '伙食', account_id=account)
                s.commit()
        return run
    concurrent(job(a, d['bank']), job(b, d['cash']))
    assert balance(engine, d['cash']) == 400
    assert balance(engine, d['bank']) == 400


def test_insufficient_funds_rejects_only_one_concurrent_intent(command_db):
    engine, d = command_db
    def send():
        with Session(engine) as s:
            try:
                create(s, d, 700)
                s.commit()
                return True
            except ValueError as exc:
                s.rollback()
                assert '餘額不足' in str(exc)
                return False
    assert sorted(concurrent(send, send)) == [False, True]
    assert balance(engine, d['cash']) == 300


def test_failed_posting_rolls_back_balance_and_movements(command_db, monkeypatch):
    engine, d = command_db
    original = BudgetManager._apply_account_balance_delta
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('S2 injected failure')
    with monkeypatch.context() as patch:
        patch.setattr(BudgetManager, '_apply_account_balance_delta', fail)
        with Session(engine) as s:
            with pytest.raises(RuntimeError): create(s, d)
            s.rollback()
    assert balance(engine, d['cash']) == 1000
    with Session(engine) as s:
        create(s, d)
        s.commit()
    assert balance(engine, d['cash']) == 900


def test_relative_adjustment_and_transaction_preserve_both(command_db):
    engine, d = command_db
    def adjust():
        with Session(engine) as s:
            AssetManager(s).adjust_asset_balance(d['a'], d['cash'], 50)
            s.commit()
    def post():
        with Session(engine) as s:
            create(s, d, 200)
            s.commit()
    concurrent(adjust, post)
    assert balance(engine, d['cash']) == 850


def test_distinct_receipts_and_manual_post_share_balance_lock(command_db):
    from tests.test_receipt_import import service, qr, create_payload
    engine, d = command_db
    with Session(engine) as s:
        ids = [service(s).import_qr(d['a'], {'qr_payload': qr().replace('AB12345678', number),
                'input_method': 'qr_image'})['receipt']['id'] for number in ('AB12345678', 'AB12345679')]
        assert len(set(ids)) == 2
        s.commit()
    def receipt(rid):
        def run():
            with Session(engine) as s:
                service(s).resolve(d['a'], rid, create_payload(d['cash']))
                s.commit()
        return run
    def manual():
        with Session(engine) as s:
            create(s, d, 100)
            s.commit()
    concurrent(receipt(ids[0]), receipt(ids[1]), manual)
    assert balance(engine, d['cash']) == 660
