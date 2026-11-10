"""Shared LINE webhook fixtures: two users with LINE identities and a manager wired to fakes."""
from types import SimpleNamespace

import pytest
from linebot.v3 import WebhookParser
from linebot.v3.webhooks import MessageEvent, PostbackEvent
from sqlalchemy import insert

from models.ai_parse_event_manager import AIParseEventManager
from models.linebot.manager import LineBotManager, MissingGeminiModel
from models.linebot.message_parser import MessageParser
from models.schema import user_identities_table
from models.user_manager import UserManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


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
