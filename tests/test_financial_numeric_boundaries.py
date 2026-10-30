from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.schema import accounts_table,transactions_table,transaction_splits_table,account_movements_table
from tests.test_financial_command_idempotency import command_db  # noqa: F401


@pytest.mark.parametrize('value',['NaN','sNaN','Infinity','-Infinity','not-money',None,True,'.00001','100000000000000'])
def test_invalid_amounts_raise_validation_error_without_database(value):
    with pytest.raises(ValueError): BudgetManager(None)._normalize_amount(value)


@pytest.mark.parametrize('value',['.0001','1','10.0000','99999999999999.9999'])
def test_valid_amount_storage_boundaries_remain_exact(value):
    assert BudgetManager(None)._normalize_amount(value)==Decimal(value)


def snapshot(s):
    return [list(s.execute(select(t).order_by(t.c.id))) for t in (
        accounts_table,transactions_table,transaction_splits_table,account_movements_table)]


@pytest.mark.parametrize('operation',['create','update'])
@pytest.mark.parametrize('field,value',[
    ('amount','NaN'),('amount','Infinity'),('amount','1.00001'),('amount','100000000000000'),
    ('exchange_rate','NaN'),('exchange_rate','Infinity'),('exchange_rate','.123456789'),
    ('exchange_rate','10000000000'),('converted_overflow',None),
])
def test_invalid_transaction_numbers_are_rejected_without_persistent_effects(command_db,operation,field,value):
    engine,data=command_db
    with Session(engine) as s:
        m=BudgetManager(s)
        options=dict(amount=1,original_currency='USD',exchange_rate=32)
        if operation=='update':
            m.add_transaction(data['a'],'2026-10-01','Original',transaction_type='expense',budget_category='伙食',**options)
            tid=m.last_created_transaction_id;s.commit()
        if field=='converted_overflow': options.update(amount='99999999999999',exchange_rate=2)
        else: options[field]=value
        before=snapshot(s)
        with pytest.raises(ValueError):
            if operation=='create':
                m.add_transaction(data['a'],'2026-10-01','Invalid',transaction_type='expense',budget_category='伙食',**options)
            else:
                m.update_transaction(data['a'],tid,'2026-10-01','Invalid',transaction_type='expense',budget_category='伙食',**options)
        s.commit()
        assert snapshot(s)==before


@pytest.mark.parametrize('value',['NaN','Infinity',None])
def test_nonfinite_custom_share_is_validation_error_and_rolls_back(command_db,value):
    engine,data=command_db
    with Session(engine) as s:
        m=BudgetManager(s);before=snapshot(s)
        with pytest.raises(ValueError):
            m.add_transaction(data['a'],'2026-10-01','Invalid share',1,'expense','伙食',
                trip_id=data['trip'],paid_by_member_id=data['am'],original_currency='USD',exchange_rate=32,
                split_allocations=[dict(trip_member_id=data['am'],amount=value)])
        s.commit()
        assert snapshot(s)==before
