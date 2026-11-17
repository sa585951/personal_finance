"""Parse events keep the outcome of a parse, never the words the person typed."""
import json

from models.ai_parse_event_manager import AIParseEventManager, redact_parse_result, title_digest
from tests.test_financial_command_idempotency import command_db  # noqa: F401

SENTENCE = "跟小明吃午餐 320 星巴克"
PARSE_RESULT = {
    "intent": "create_transaction",
    "source": "local_fallback",
    "raw_text": SENTENCE,
    "legacy": {"type": "expense", "category": "跟小明吃午餐 星巴克", "description": "備註原文", "amount": 320},
    "transaction": {
        "type": "expense", "title": "跟小明吃午餐 星巴克", "budget_category": "伙食", "amount": "320",
        "description": "備註原文", "account_hint": "玉山", "account_name": "我的玉山帳戶", "account_id": "acc-1",
        "currency": "TWD", "date": "2026-11-16", "merchant": "星巴克",
    },
    "flow": {"from": "我的玉山帳戶"},
    "missing_fields": [],
    "errors": [],
}


def test_redacted_payload_has_no_typed_text_anywhere():
    stored = json.dumps(redact_parse_result(PARSE_RESULT), ensure_ascii=False)
    for word in ("小明", "星巴克", "午餐", "備註原文", "玉山", "320 "):
        assert word not in stored
    assert "raw_text" not in stored and "legacy" not in stored and "flow" not in stored


def test_redacted_payload_keeps_what_measures_a_used_draft():
    safe = redact_parse_result(PARSE_RESULT)
    assert safe["intent"] == "create_transaction" and safe["source"] == "local_fallback"
    assert safe["transaction"] == {
        "type": "expense", "budget_category": "伙食", "amount": "320", "currency": "TWD",
        "date": "2026-11-16", "account_id": "acc-1", "title_hash": title_digest("跟小明吃午餐 星巴克"),
    }
    assert redact_parse_result({"intent": "other", "errors": ["無法識別金額"], "transaction": None})["transaction"] is None


def test_unchanged_detection_still_works_without_the_title():
    safe = redact_parse_result(PARSE_RESULT)
    saved = {"amount": 320, "budget_category": "伙食", "item": "跟小明吃午餐 星巴克",
             "date": "2026-11-16", "account_id": "acc-1"}
    assert AIParseEventManager.draft_unchanged(safe, saved) is True
    assert AIParseEventManager.draft_unchanged(safe, {**saved, "item": "晚餐"}) is False
    assert AIParseEventManager.draft_unchanged(safe, {**saved, "amount": 330}) is False
    # An event recorded before this change still carries the plain title.
    assert AIParseEventManager.draft_unchanged(PARSE_RESULT, saved) is True


def test_title_digest_ignores_width_and_surrounding_spaces():
    assert title_digest(" 午餐 ") == title_digest("午餐")
    assert title_digest("ＡＢＣ") == title_digest("ABC")
    assert title_digest("午餐") != title_digest("晚餐")


def test_migration_clears_old_sentences_but_keeps_line_drafts_and_the_outcome(command_db, monkeypatch):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import insert, select
    from sqlalchemy.orm import Session

    from models.schema import ai_parse_events_table as events

    engine, data = command_db
    web = {**PARSE_RESULT}
    line = {"line_oral": True, "raw_text": "old", "line_draft": {"item": "午餐", "amount": "91"}}
    with Session(engine) as s:
        ids = {}
        for name, source, raw, payload in (
            ("web", "web", SENTENCE, web), ("line", "line_bot", "舊原句", line), ("bare", "web", "只有原句", None),
        ):
            ids[name] = s.execute(insert(events).values(
                user_id=data["a"], source=source, raw_input=raw, parsed_payload=payload, status="success",
            ).returning(events.c.id)).scalar_one()
        s.commit()

    monkeypatch.setenv("DATABASE_URL", engine.url.render_as_string(hide_password=False))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(config, "20261112_0023")
    command.upgrade(config, "head")

    with Session(engine) as s:
        rows = {row.id: row for row in s.execute(select(events)).all()}
    assert all(row.raw_input == "" for row in rows.values())
    web_row = rows[ids["web"]]
    stored = json.dumps(web_row.parsed_payload, ensure_ascii=False)
    assert "小明" not in stored and "星巴克" not in stored and "legacy" not in stored and "raw_text" not in stored
    assert web_row.parsed_payload["transaction"]["amount"] == "320"
    assert web_row.parsed_payload["transaction"]["title_hash"] == title_digest("跟小明吃午餐 星巴克")
    line_row = rows[ids["line"]]
    assert "raw_text" not in line_row.parsed_payload
    assert line_row.parsed_payload["line_draft"] == {"item": "午餐", "amount": "91"}
    assert rows[ids["bare"]].parsed_payload is None
