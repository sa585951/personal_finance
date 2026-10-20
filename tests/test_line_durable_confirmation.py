import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from linebot.v3 import WebhookParser
from linebot.v3.webhooks import MessageEvent, PostbackEvent
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from models.ai_parse_event_manager import AIParseEventManager
from models.linebot.manager import LineBotManager, MissingGeminiModel
from models.linebot.message_handler import MessageHandler
from models.linebot.message_parser import MessageParser
from models.linebot.user_state_manager import UserStateManager
from models.schema import (
    accounts_table, account_movements_table, ai_parse_events_table,
    transactions_table, line_webhook_events_table, user_identities_table,
)
from models.user_manager import UserManager
from tests.test_financial_command_idempotency import command_db


@pytest.fixture
def line_db(command_db):
    engine, data = command_db
    with engine.begin() as c:
        for role in ('a', 'b'):
            c.execute(insert(user_identities_table).values(user_id=data[role], provider='line', provider_user_id='U-fix-'+role))
    return engine, data


class FakeLINE:
    def __init__(self):
        self.profile_calls = 0
        self.replies = 0
        self.fail_reply = False

    def get_profile(self, user_id):
        self.profile_calls += 1
        return SimpleNamespace(display_name='A' if user_id.endswith('a') else 'B')

    def reply_message(self, request):
        self.replies += 1
        if self.fail_reply:
            self.fail_reply = False
            raise RuntimeError('Lost external reply after DB commit')


def manager(session, api=None):
    m = object.__new__(LineBotManager)
    m.db_session = session
    m.line_bot_api = api or FakeLINE()
    m.app_state = SimpleNamespace(is_cold_start=lambda: False)
    m.user_manager = UserManager(session)
    m.ai_parse_event_manager = AIParseEventManager(session)
    m.user_state_manager = UserStateManager()
    m.message_handler = MessageHandler(m.user_state_manager, session)
    m.message_parser = MessageParser(MissingGeminiModel(), '{message}')
    m.parser = WebhookParser('qa-secret')
    return m


def event_dict(eid='draft-event', role='a', postback=None):
    event = dict(type='postback' if postback else 'message', mode='active',
        timestamp=1792454400000, source=dict(type='user', userId='U-fix-'+role),
        webhookEventId=eid, deliveryContext=dict(isRedelivery=False), replyToken='synthetic-reply')
    if postback:
        event['postback'] = dict(data=postback)
    else:
        event['message'] = dict(type='text', id='synthetic-message', quoteToken='synthetic-quote',
            text='2026-10-01 午餐91元 用現金')
    return event


def event(eid='draft-event', role='a', postback=None):
    data = event_dict(eid, role, postback)
    return PostbackEvent.from_dict(data) if postback else MessageEvent.from_dict(data)


def create_draft(engine):
    with Session(engine) as s:
        reply = manager(s).process_event(event())
        s.commit()
        row = s.execute(select(ai_parse_events_table)).mappings().one()
        assert row['parsed_payload']['line_draft']['amount'] == '91'
        assert row['parsed_payload']['line_draft']['date'] == '2026-10-01'
        return str(row['id']), reply


def assert_one_commit(engine, data, draft_id):
    with Session(engine) as s:
        rows = s.execute(select(transactions_table).where(transactions_table.c.client_request_id == draft_id)).mappings().all()
        assert len(rows) == 1 and rows[0]['original_amount'] == 91
        assert str(rows[0]['account_id']) == data['cash']
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == 909
        movements = s.execute(select(account_movements_table).where(account_movements_table.c.source_id == rows[0]['id'])).mappings().all()
        assert len(movements) == 1 and movements[0]['amount_delta'] == -91
        assert s.scalar(select(ai_parse_events_table.c.status).where(ai_parse_events_table.c.id == draft_id)) == 'confirmed'


def test_duplicate_message_replays_preview_without_parsing_or_ledger_write(line_db):
    engine, data = line_db
    draft_id, first = create_draft(engine)
    with Session(engine) as s:
        api = FakeLINE()
        retry = event_dict()
        retry['replyToken'] = 'different-reply-token'
        retry['deliveryContext']['isRedelivery'] = True
        reply = manager(s, api).process_event(MessageEvent.from_dict(retry))
        s.commit()
        assert json.loads(reply.to_json()) == json.loads(first.to_json())
        assert api.profile_calls == 0
        assert s.scalar(select(func.count()).select_from(ai_parse_events_table)) == 1
        assert s.scalar(select(func.count()).select_from(transactions_table)) == 1  # Seeded trip dinner only.
        assert s.scalar(select(func.count()).select_from(account_movements_table)) == 0
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data['cash'])) == 1000


def test_distinct_concurrent_confirm_events_create_one_transaction(line_db):
    engine, data = line_db
    draft_id, _ = create_draft(engine)
    def confirm(_):
        with Session(engine) as s:
            response = manager(s).process_event(event(str(uuid4()), postback='nomica.confirm:'+draft_id))
            s.commit()
            return response
    with ThreadPoolExecutor(max_workers=6) as pool:
        replies = list(pool.map(confirm, range(6)))
    assert sum('記帳完成' in r for r in replies) == 1
    assert_one_commit(engine, data, draft_id)


def test_confirmation_owner_cancel_and_expiry_are_fail_closed(line_db):
    engine, data = line_db
    draft_id, _ = create_draft(engine)
    with Session(engine) as s:
        other = manager(s).process_event(event('wrong-owner', role='b', postback='nomica.confirm:'+draft_id))
        s.commit()
        assert '找不到' in other
        manager(s).process_event(event('cancel', postback='nomica.cancel:'+draft_id))
        s.commit()
        retry = manager(s).process_event(event('confirm-after-cancel', postback='nomica.confirm:'+draft_id))
        s.commit()
        assert '取消' in retry
        assert s.scalar(select(func.count()).select_from(transactions_table)) == 1
        # Another preview remains unconfirmed after its expiry.
        manager(s).process_event(event('new-draft'))
        s.commit()
        second = s.execute(select(ai_parse_events_table.c.id).where(ai_parse_events_table.c.id != draft_id)).scalar_one()
        s.execute(update(ai_parse_events_table).where(ai_parse_events_table.c.id == second).values(created_at=datetime.now(timezone.utc)-timedelta(minutes=31)))
        s.commit()
        expired = manager(s).process_event(event('expired', postback='nomica.confirm:'+str(second)))
        s.commit()
        assert '逾期' in expired
        assert s.scalar(select(func.count()).select_from(transactions_table)) == 1
        assert s.scalar(select(func.count()).select_from(account_movements_table)) == 0


def test_failed_confirmation_rolls_back_event_transaction_movement_and_status(line_db, monkeypatch):
    engine, data = line_db
    draft_id, _ = create_draft(engine)
    original = AIParseEventManager.confirm_event
    def fail(*args, **kwargs):
        raise RuntimeError('Injected draft update failure after financial write')
    monkeypatch.setattr(AIParseEventManager, 'confirm_event', fail)
    with Session(engine) as s:
        with pytest.raises(RuntimeError):
            manager(s).process_event(event('retry-confirm', postback='nomica.confirm:'+draft_id))
        s.commit()
        assert s.scalar(select(func.count()).select_from(transactions_table)) == 1
        assert s.scalar(select(func.count()).select_from(account_movements_table)) == 0
        assert s.scalar(select(func.count()).select_from(line_webhook_events_table)) == 1
        assert s.scalar(select(ai_parse_events_table.c.status).where(ai_parse_events_table.c.id == draft_id)) == 'success'
    monkeypatch.setattr(AIParseEventManager, 'confirm_event', original)
    with Session(engine) as s:
        manager(s).process_event(event('retry-confirm', postback='nomica.confirm:'+draft_id))
        s.commit()
    assert_one_commit(engine, data, draft_id)


def test_real_flask_webhook_retries_after_reply_failure_without_reposting(line_db, monkeypatch):
    import web_app
    engine, data = line_db
    db = scoped_session(sessionmaker(bind=engine))
    api = FakeLINE()
    m = manager(db, api)
    monkeypatch.setattr(web_app, 'db_session', db)
    monkeypatch.setattr(web_app, 'linebot_manager', m)
    client = web_app.app.test_client()
    def send(payload, valid=True):
        body = json.dumps(dict(events=[payload]), separators=(',', ':'))
        signature = base64.b64encode(hmac.new(b'qa-secret', body.encode(), hashlib.sha256).digest()).decode() if valid else 'invalid'
        return client.post('/line-webhook', data=body, content_type='application/json', headers={'X-Line-Signature': signature})
    assert send(event_dict(), valid=False).status_code == 400
    api.fail_reply = True
    assert send(event_dict()).status_code == 503
    assert send(event_dict()).status_code == 200
    with Session(engine) as s:
        draft_id = str(s.scalar(select(ai_parse_events_table.c.id)))
        assert s.scalar(select(func.count()).select_from(transactions_table)) == 1
    confirmation = event_dict('confirm-over-http', postback='nomica.confirm:'+draft_id)
    api.fail_reply = True
    assert send(confirmation).status_code == 503
    assert send(confirmation).status_code == 200
    assert_one_commit(engine, data, draft_id)
    db.remove()
