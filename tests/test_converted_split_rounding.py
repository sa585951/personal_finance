from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.schema import transactions_table, transaction_splits_table
from models.trip_manager import TripManager
from models.user_manager import UserManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


@pytest.fixture
def rounding_db(command_db):
    engine, data = command_db
    with Session(engine) as session:
        third = UserManager(session).get_or_create_user_for_identity('qa', 'round-C', 'C')['id']
        trips = TripManager(session)
        trips.close_invite(data['a'],data['trip'])
        trips.accept_invite(third,trips.create_invite(data['a'],data['trip'])['token'])
        data['cm'] = next(m['id'] for m in trips.list_trip_members(data['a'],data['trip']) if m['user_id']==str(third))
        session.commit()
    return engine, data


def create(session, data, method, rate, reverse=False):
    m = BudgetManager(session)
    members = [data['am'],data['bm'],data['cm']] if method=='equal' else [data['bm'],data['cm']]
    if reverse: members.reverse()
    options = {'split_member_ids': members} if method=='equal' else {
        'split_allocations': [dict(trip_member_id=member,amount='.01') for member in members]}
    amount = '.03' if method=='equal' else '.02'
    m.add_transaction(data['a'],'2026-10-01','Rounding',amount,'expense','伙食',
        trip_id=data['trip'], paid_by_member_id=data['am'], original_currency='USD', exchange_rate=rate, **options)
    return m.last_created_transaction_id, members, amount, options


def rows_for(session, tid):
    return session.execute(select(transaction_splits_table).where(transaction_splits_table.c.transaction_id==tid)).all()


@pytest.mark.parametrize('method,rate,target,small,large',[
    ('equal','.33333333','.0100','.0033','.0034'),
    ('custom','.33333333','.0067','.0033','.0034'),
    ('custom','.66666666','.0133','.0066','.0067'),
])
def test_converted_shares_conserve_stored_total_without_changing_originals(rounding_db,method,rate,target,small,large):
    engine, data = rounding_db
    with Session(engine) as session:
        tid,members,amount,_ = create(session,data,method,rate)
        session.commit()
    with Session(engine) as session:
        rows = rows_for(session,tid)
        assert {str(r.trip_member_id) for r in rows} == set(members)
        assert sum(r.share_amount for r in rows)==Decimal(amount)
        assert all(r.share_amount==Decimal('.01') for r in rows)
        stored = session.scalar(select(transactions_table.c.converted_amount).where(transactions_table.c.id==tid))
        assert stored==Decimal(target)
        assert sum(r.converted_share_amount for r in rows)==stored
        distribution = {str(r.trip_member_id):r.converted_share_amount for r in rows}
        assert distribution[min(members)]==Decimal(large)
        assert all(value==Decimal(small) for member,value in distribution.items() if member!=min(members))


def test_custom_order_and_metadata_edit_keep_same_remainder_owner(rounding_db):
    engine,data=rounding_db
    with Session(engine) as session:
        first,_,_,_=create(session,data,'custom','.33333333')
        second,_,_,options=create(session,data,'custom','.33333333',reverse=True)
        session.commit()
        BudgetManager(session).update_transaction(data['a'],first,'2026-10-01','Renamed','.02','expense','伙食',
            paid_by_member_id=data['am'],original_currency='USD',**options)
        session.commit()
        distributions=[{str(r.trip_member_id):r.converted_share_amount for r in rows_for(session,tid)} for tid in (first,second)]
        assert distributions[0]==distributions[1]
        assert sorted(distributions[0].values())==[Decimal('.0033'),Decimal('.0034')]


def test_zero_original_share_never_receives_converted_remainder(rounding_db):
    engine,data=rounding_db
    with Session(engine) as session:
        m=BudgetManager(session)
        m.add_transaction(data['a'],'2026-10-01','Smallest USD','.01','expense','伙食',
            trip_id=data['trip'],paid_by_member_id=data['am'],original_currency='USD',exchange_rate='.33333333',
            split_member_ids=[data['am'],data['bm'],data['cm']])
        tid=m.last_created_transaction_id
        session.commit()
        rows=rows_for(session,tid)
        assert sum(r.converted_share_amount for r in rows)==Decimal('.0033')
        assert all(r.converted_share_amount==0 for r in rows if r.share_amount==0)
        assert len([r for r in rows if r.share_amount==0])==2


def test_exact_conversion_requires_no_remainder_distribution(rounding_db):
    engine,data=rounding_db
    with Session(engine) as session:
        tid,_,_,_=create(session,data,'equal','32')
        session.commit()
        rows=rows_for(session,tid)
        assert all(r.converted_share_amount==Decimal('.32') for r in rows)
        assert sum(r.converted_share_amount for r in rows)==Decimal('.96')
