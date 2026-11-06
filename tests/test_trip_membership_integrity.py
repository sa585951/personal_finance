from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep

import pytest
from sqlalchemy import insert,select,func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.schema import trip_members_table,transaction_splits_table
from models.trip_manager import TripManager
from models.user_manager import UserManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def join_data(engine,data):
    with Session(engine) as s:
        users=UserManager(s)
        c=users.get_or_create_user_for_identity('qa','member-C','C')['id']
        d=users.get_or_create_user_for_identity('qa','member-D','D')['id']
        trips=TripManager(s)
        trips.close_invite(data['a'],data['trip'])
        token=trips.create_invite(data['a'],data['trip'])['token']
        s.commit()
    return c,d,token


def concurrent(*jobs):
    barrier=Barrier(len(jobs))
    def run(job):
        barrier.wait(timeout=5)
        return job()
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        return [f.result(timeout=15) for f in [pool.submit(run,j) for j in jobs]]


@pytest.mark.parametrize('kind',['member','split'])
def test_database_rejects_duplicate_identity_pair(command_db,kind):
    engine,data=command_db
    with Session(engine) as s:
        if kind=='member':
            stmt=insert(trip_members_table).values(trip_id=data['trip'],user_id=data['a'],display_name='Duplicate',role='editor',status='active')
        else:
            row=s.execute(select(transaction_splits_table).limit(1)).one()
            values={k:v for k,v in row._mapping.items() if k not in ('id','created_at','updated_at')}
            stmt=insert(transaction_splits_table).values(**values)
        with pytest.raises(IntegrityError):
            with s.begin_nested(): s.execute(stmt)


@pytest.mark.parametrize('same_user',[True,False])
def test_concurrent_invites_do_not_duplicate_or_exceed_capacity(command_db,monkeypatch,same_user):
    engine,data=command_db
    c,d,token=join_data(engine,data)
    original=TripManager._active_member_count
    def slow(*args):
        count=original(*args);sleep(.1);return count
    monkeypatch.setattr(TripManager,'_active_member_count',slow)
    def job(user):
        def run():
            with Session(engine) as s:
                try:
                    result=TripManager(s).accept_invite(user,token,member_limit=3)
                    s.commit();return result['member']['id']
                except ValueError as e:
                    s.rollback();assert '上限' in str(e);return None
        return run
    results=concurrent(job(c),job(c if same_user else d))
    if same_user: assert results[0] is not None and results[0]==results[1]
    else: assert sum(x is not None for x in results)==1
    with Session(engine) as s:
        assert TripManager(s)._active_member_count(data['trip'])==3
        assert s.scalar(select(func.count()).select_from(trip_members_table).where(
            trip_members_table.c.trip_id==data['trip'],trip_members_table.c.user_id==c))<=1


def test_external_members_obey_same_active_limit(command_db):
    engine,data=command_db
    with Session(engine) as s:
        trips=TripManager(s)
        for i in range(13): trips.add_external_member(data['a'],data['trip'],f'External {i}')
        with pytest.raises(ValueError,match='上限'):
            trips.add_external_member(data['a'],data['trip'],'One too many')
        assert trips._active_member_count(data['trip'])==15


def test_external_and_invite_compete_for_last_slot(command_db,monkeypatch):
    engine,data=command_db
    c,_,token=join_data(engine,data)
    with Session(engine) as s:
        for i in range(12): TripManager(s).add_external_member(data['a'],data['trip'],f'External {i}')
        s.commit()
    original=TripManager._active_member_count
    def slow(*args):
        count=original(*args);sleep(.1);return count
    monkeypatch.setattr(TripManager,'_active_member_count',slow)
    def job(external):
        def run():
            with Session(engine) as s:
                try:
                    trips=TripManager(s)
                    if external: trips.add_external_member(data['a'],data['trip'],'Last external')
                    else: trips.accept_invite(c,token)
                    s.commit();return True
                except ValueError as e:
                    s.rollback();assert '上限' in str(e);return False
        return run
    assert sorted(concurrent(job(False),job(True)))==[False,True]
    with Session(engine) as s: assert TripManager(s)._active_member_count(data['trip'])==15


def test_rejoin_restores_same_identity_and_external_names_are_not_identity(command_db):
    engine,data=command_db
    c,_,token=join_data(engine,data)
    with Session(engine) as s:
        trips=TripManager(s)
        member=trips.accept_invite(c,token)['member']['id']
        trips.leave_trip(c,data['trip'])
        assert trips.accept_invite(c,token)['member']['id']==member
        assert trips.add_external_member(data['a'],data['trip'],'Same name')['id']!=trips.add_external_member(data['a'],data['trip'],'Same name')['id']
        s.commit()
