from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect,insert,select,text
from sqlalchemy.orm import Session

from models.schema import accounts_table,trip_members_table,transaction_splits_table,transactions_table
from tests.test_financial_command_idempotency import command_db  # noqa: F401

CONSTRAINTS={
    'trip_members':'uq_trip_members_trip_user',
    'transaction_splits':'uq_transaction_splits_transaction_member',
}


def snapshot(engine):
    with engine.connect() as c:
        return [list(c.execute(select(t).order_by(t.c.id))) for t in (
            accounts_table,trip_members_table,transactions_table,transaction_splits_table)]


def old_schema(engine,monkeypatch):
    # Simulate the actual deployed 0018 shape, not the moving initial metadata.
    with engine.begin() as c:
        for table,name in CONSTRAINTS.items():
            if name in {x['name'] for x in inspect(c).get_unique_constraints(table)}:
                c.execute(text(f'ALTER TABLE {table} DROP CONSTRAINT {name}'))
    monkeypatch.setenv('DATABASE_URL',engine.url.render_as_string(hide_password=False))
    cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    command.stamp(cfg,'20261021_0018')
    return cfg


def test_r09_populated_upgrade_preserves_all_financial_rows(command_db,monkeypatch):
    engine,_=command_db
    cfg=old_schema(engine,monkeypatch)
    before=snapshot(engine)
    command.upgrade(cfg,'head')
    assert snapshot(engine)==before
    with engine.connect() as c:
        for table,name in CONSTRAINTS.items():
            assert name in {x['name'] for x in inspect(c).get_unique_constraints(table)}
        assert c.scalar(text('SELECT version_num FROM alembic_version'))=='20261110_0022'


@pytest.mark.parametrize('kind',['member','split'])
def test_r09_duplicate_preflight_aborts_without_cleanup_or_version_change(command_db,monkeypatch,kind):
    engine,data=command_db
    cfg=old_schema(engine,monkeypatch)
    with engine.begin() as c:
        if kind=='member':
            c.execute(insert(trip_members_table).values(trip_id=data['trip'],user_id=data['a'],display_name='Duplicate',role='editor',status='removed'))
        else:
            row=c.execute(select(transaction_splits_table).limit(1)).one()
            values={k:v for k,v in row._mapping.items() if k not in ('id','created_at','updated_at')}
            c.execute(insert(transaction_splits_table).values(**values))
    before=snapshot(engine)
    with pytest.raises(RuntimeError,match='R09'):
        command.upgrade(cfg,'head')
    assert snapshot(engine)==before
    with engine.connect() as c:
        assert c.scalar(text('SELECT version_num FROM alembic_version'))=='20261021_0018'
        for table,name in CONSTRAINTS.items():
            assert name not in {x['name'] for x in inspect(c).get_unique_constraints(table)}
