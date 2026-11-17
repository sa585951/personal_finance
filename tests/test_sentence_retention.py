"""Typed sentences are kept only for failures and edited drafts, 30 days at most, and only the operator sees them."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from models.admin_usage import retained_sentences
from models.ai_parse_event_manager import AIParseEventManager, clip_sentence
from models.schema import ai_parse_events_table as events
from tests.line_fixtures import command_db, line_db  # noqa: F401
from tests.test_line_shortcut_pilot import lunch, webhook  # noqa: F401

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def add(session, user_id, sentence, *, age, status="success", unchanged=None, source="web"):
    return session.execute(insert(events).values(
        user_id=user_id, source=source, raw_input=sentence, parsed_payload={}, status=status,
        confirmed_unchanged=unchanged, created_at=NOW - age,
    ).returning(events.c.id)).scalar_one()


def sentence_of(session, event_id):
    return session.scalar(select(events.c.raw_input).where(events.c.id == event_id))


def test_purge_keeps_only_failures_and_edited_drafts_and_never_past_30_days(command_db):
    engine, data = command_db
    hours, days = (lambda n: timedelta(hours=n)), (lambda n: timedelta(days=n))
    with Session(engine) as s:
        ids = {
            "fresh_draft": add(s, data["a"], "剛解析", age=hours(1)),
            "old_unsaved_draft": add(s, data["a"], "沒存檔", age=days(2)),
            "old_unchanged": add(s, data["a"], "沒改", age=days(2), status="confirmed", unchanged=True),
            "old_unknown": add(s, data["a"], "未知", age=days(2), status="confirmed", unchanged=None),
            "failed": add(s, data["a"], "看不懂", age=days(10), status="failed"),
            "edited": add(s, data["a"], "被改過", age=days(10), status="confirmed", unchanged=False),
            "failed_too_old": add(s, data["a"], "太舊的失敗", age=days(31), status="failed"),
            "edited_too_old": add(s, data["a"], "太舊的修改", age=days(31), status="confirmed", unchanged=False),
        }
        AIParseEventManager(s).purge_expired_sentences(now=NOW, force=True)
        s.commit()
        kept = {name for name, event_id in ids.items() if sentence_of(s, event_id)}
    assert kept == {"fresh_draft", "failed", "edited"}


def test_purge_runs_at_most_every_few_minutes(command_db):
    engine, data = command_db
    with Session(engine) as s:
        manager = AIParseEventManager(s)
        manager.purge_expired_sentences(now=NOW, force=True)
        late = add(s, data["a"], "太舊", age=timedelta(days=40))
        manager.purge_expired_sentences(now=NOW + timedelta(minutes=1))  # throttled
        assert sentence_of(s, late)
        manager.purge_expired_sentences(now=NOW + timedelta(minutes=30))
        assert sentence_of(s, late) == ""


def test_saving_a_draft_unchanged_forgets_the_sentence_but_an_edit_keeps_it(command_db):
    engine, data = command_db
    with Session(engine) as s:
        manager = AIParseEventManager(s)
        same = manager.record_from_parse_result(data["a"], "web", {"raw_text": "午餐 120", "errors": [],
                                                                    "transaction": {"type": "expense"}})
        edited = manager.record_from_parse_result(data["a"], "web", {"raw_text": "晚餐 300", "errors": [],
                                                                      "transaction": {"type": "expense"}})
        assert sentence_of(s, same["id"]) == "午餐 120"
        manager.confirm_event(data["a"], same["id"], "expense", data["trip"], unchanged=True)
        manager.confirm_event(data["a"], edited["id"], "expense", data["trip"], unchanged=False)
        assert sentence_of(s, same["id"]) == "" and sentence_of(s, edited["id"]) == "晚餐 300"


def test_sentences_are_clipped(command_db):
    assert len(clip_sentence("字" * 500)) == 200 and clip_sentence(None) == ""


def test_operator_list_has_no_identity_and_only_what_is_worth_improving(command_db):
    engine, data = command_db
    with Session(engine) as s:
        add(s, data["a"], "看不懂的句子", age=timedelta(days=1), status="failed", source="line_bot")
        add(s, data["b"], "被改過的句子", age=timedelta(days=2), status="confirmed", unchanged=False)
        add(s, data["a"], "正常成功", age=timedelta(hours=1))
        add(s, data["a"], "", age=timedelta(days=1), status="failed")
        s.commit()
        listing = retained_sentences(s)
    assert [item["sentence"] for item in listing] == ["看不懂的句子", "被改過的句子"]
    assert {key for item in listing for key in item} == {"date", "source", "reason", "sentence"}
    assert listing[0]["source"] == "LINE" and listing[1]["reason"] == "存檔前被修改"
    assert str(data["a"]) not in str(listing) and str(data["b"]) not in str(listing)


def test_line_keeps_a_sentence_it_cannot_read_but_never_a_sensitive_one(webhook):
    send, replies, engine, data = webhook
    assert send(lunch("miss-1", "你好嗎")).status_code == 200
    assert send(lunch("sensitive-1", "我的卡號 4111 1111 1111 1111 午餐 120")).status_code == 200
    with Session(engine) as s:
        rows = s.execute(select(events.c.raw_input, events.c.status, events.c.source)).all()
    assert ("你好嗎", "failed", "line_bot") in [tuple(row) for row in rows]
    assert not any("4111" in row.raw_input for row in rows)
