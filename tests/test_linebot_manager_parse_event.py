from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.ai_parse_event_manager import AIParseEventManager
from models.budget_manager import TransactionCreationResult
from models.linebot.manager import LineBotManager
from models.schema import transactions_table,ai_parse_events_table
from tests.test_financial_command_idempotency import command_db  # noqa: F401


@pytest.mark.parametrize('mode',['explicit','query','missing','stale'])
def test_line_parse_confirmation_uses_only_explicit_creation_result(command_db,mode):
    engine,data=command_db
    with Session(engine) as session:
        events=AIParseEventManager(session)
        event=events.record_parse_event(data['a'],'line_bot','Synthetic',{},'success',result_type='expense')
        tid=session.scalar(select(transactions_table.c.id).limit(1))
        legacy=uuid4() if mode in ('explicit','stale') else None
        manager=SimpleNamespace(ai_parse_event_manager=events,
            message_handler=SimpleNamespace(budget_manager=SimpleNamespace(last_created_transaction_id=legacy)))
        options={'creation_result':TransactionCreationResult('Created',tid)} if mode=='explicit' else {}
        LineBotManager._confirm_parse_event_if_transaction_created(manager,data['a'],event,
            {'type':'query' if mode=='query' else 'expense'},**options)
        session.commit()
        saved=session.execute(select(ai_parse_events_table).where(ai_parse_events_table.c.id==event['id'])).one()
        assert (saved.status,saved.result_id)==(('confirmed',tid) if mode=='explicit' else ('success',None))
