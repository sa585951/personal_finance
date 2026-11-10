from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import base64
import hashlib
import hmac
import json

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from models.ai_parse_service import AIParseService
from models.asset_manager import AssetManager
from models.idempotency import money
from models.linebot.oral_pilot import oral_payload, parse_oral
from models.ai_parse_event_manager import AIParseEventManager
from models.optional_access import load_optional_access
from models.schema import accounts_table, account_movements_table, ai_parse_events_table, transactions_table
from tests.test_ai_parse_api import _load_web_app
from tests.line_fixtures import FakeLINE, command_db, event, event_dict, line_db, manager  # noqa: F401


def lunch(eid="shortcut", text="午餐 120", **changes):
    payload = event_dict(eid)
    payload["message"]["text"] = text
    return {**payload, **changes}


def forbidden(*args, **kwargs):
    pytest.fail("shortcut pilot called the generic parser, profile API or event handler")


def safe_manager(session):
    bot = manager(session)
    bot.message_parser.parse_shared = forbidden
    parser = bot.message_parser.ai_parse_service.gemini_parser
    provider_parse = parser.parse
    parser.parse = lambda text, **kwargs: provider_parse(text, **kwargs) if kwargs else {
        "type": "expense", "category": "午餐", "budget_category": "伙食", "amount": 120,
        "currency": "TWD", "target_asset": next((name for name in ("國泰卡", "Duplicate", "B cash") if name in text), None),
    }
    bot.line_bot_api.get_profile = forbidden
    return bot


@pytest.fixture
def webhook(line_db, monkeypatch):
    engine, data = line_db
    app = _load_web_app(monkeypatch)
    db = scoped_session(sessionmaker(bind=engine))
    bot = safe_manager(db)
    replies = []
    bot.line_bot_api.reply_message = replies.append
    monkeypatch.setattr(app, "db_session", db)
    monkeypatch.setattr(app, "linebot_manager", bot)
    monkeypatch.setattr(app, "OPTIONAL_ACCESS", load_optional_access({"NOMICA_ENV": "production"}))

    def send(*events, valid=True):
        body = json.dumps({"events": events}).encode()
        signature = base64.b64encode(hmac.digest(b"qa-secret" if valid else b"wrong", body, hashlib.sha256)).decode()
        with app.app.test_client() as client:
            return client.post("/line-webhook", data=body, headers={"X-Line-Signature": signature})

    send.bot = bot
    yield send, replies, engine, data
    db.remove()


def counts(engine, data):
    with Session(engine) as session:
        return (
            session.scalar(select(func.count()).select_from(transactions_table)),
            session.scalar(select(func.count()).select_from(account_movements_table)),
            session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data["cash"])),
        )


def test_signed_shortcut_filters_recipient_and_reports_correctable_errors(webhook):
    send, replies, engine, data = webhook
    with Session(engine) as session:
        assets = AssetManager(session)
        assets.add_account(data["a"], "Foreign", "cash", 500, currency="JPY")
        assets.add_account(data["a"], "Duplicate", "cash", 50)
        assets.add_account(data["a"], "Duplicate", "bank", 60)
        assets.add_account(data["a"], "Identical", "cash", 50)
        assets.add_account(data["a"], "Identical", "cash", 60)
        session.commit()
    assert send(lunch(), valid=False).status_code == 400
    assert send(lunch(source={"type": "group", "groupId": "C-group", "userId": "U-fix-a"}),
                lunch(mode="standby")).status_code == 200
    assert replies == []
    for i, (message, fragment) in enumerate([
        ("幫助", "午餐"),
        ("午餐 80 加飲料 40", "補金額"),
        ("上個週末午餐 120", "補日期"),
        ("月底午餐 120", "補日期"),
        ("昨天去超商買咖啡花了 120 日圓", "帳戶"),
        ("轉帳 120", "Web"),
    ]):
        assert send(lunch(f"case-{i}", message)).status_code == 200
        assert fragment in str(replies[-1].messages[0].to_dict())
    for i, message in enumerate(("午餐 120 Duplicate", "午餐 120 B cash")):
        assert send(lunch(f"choose-{i}", message)).status_code == 200
        offered = replies[-1].messages[0].to_dict()["contents"]["footer"]["contents"]
        assert all(button["action"]["label"] not in {"B cash", "Foreign"} for button in offered)
        labels = [button["action"]["label"] for button in offered]
        assert {"Duplicate（現金）", "Duplicate（銀行）"} <= set(labels)
        assert all("Identical" not in label for label in labels)
    assert send(lunch("unlinked", source={"type": "user", "userId": "U-fix-unknown"})).status_code == 200
    assert "登入" in str(replies[-1].messages[0].to_dict())
    assert counts(engine, data) == (1, 0, 1000)


def test_shortcut_replay_and_concurrent_confirmation_debit_once(webhook):
    send, replies, engine, data = webhook
    assert send(lunch()).status_code == 200
    with Session(engine) as session:
        unselected = str(session.scalar(select(ai_parse_events_table.c.id)))
    assert send(event_dict("skip-selection", postback="nomica.oral.confirm:" + unselected)).status_code == 200
    assert counts(engine, data) == (1, 0, 1000)
    assert send(lunch(replyToken="retry-token", deliveryContext={"isRedelivery": True})).status_code == 200
    assert replies[0].messages[0].to_dict() == replies[-1].messages[0].to_dict()
    buttons = replies[-1].messages[0].to_dict()["contents"]["footer"]["contents"]
    choose = next(button["action"]["data"] for button in buttons if button["action"]["label"] == "cash")
    assert send(event_dict("forged-account", postback=choose.rsplit(":", 1)[0] + ":" + data["b_cash"])).status_code == 200
    assert "已無法選用" in str(replies[-1].messages[0].to_dict())
    assert send(event_dict("pick-account", postback=choose)).status_code == 200
    assert send(event_dict("pick-account", postback=choose)).status_code == 200
    assert counts(engine, data) == (1, 0, 1000)
    with Session(engine) as session:
        draft = session.execute(select(ai_parse_events_table)).mappings().one()
        draft_id = str(draft["id"])
        assert draft["parsed_payload"]["line_draft"]["account_id"] == data["cash"]
        assert draft["parsed_payload"]["line_draft"]["original_currency"] == "TWD"
    action = "nomica.oral.confirm:" + draft_id
    assert send(event_dict("other-owner", role="b", postback=action)).status_code == 200
    assert counts(engine, data) == (1, 0, 1000)

    def confirm(_):
        with Session(engine) as session:
            reply = safe_manager(session).process_oral_event(event(str(uuid4()), postback=action))
            session.commit()
            return reply

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum("記帳完成" in str(reply.to_dict()) for reply in pool.map(confirm, range(4))) == 1
    assert counts(engine, data) == (2, 1, 880)


def test_shortcut_cancel_expiry_and_legacy_draft_rejected(webhook):
    send, replies, engine, data = webhook
    # A draft from the retired non-oral flow, still pending in the database, can never be confirmed here.
    with Session(engine) as session:
        legacy = AIParseEventManager(session).record_from_parse_result(data["a"], "line_bot", {
            "raw_text": "old", "line_draft": {"date": "2026-10-01", "item": "午餐", "amount": "91", "type": "expense",
                                              "budget_category": "伙食", "account_id": data["cash"],
                                              "original_currency": "TWD"}})
        session.commit()
        legacy_id = str(legacy["id"])
    assert send(event_dict("legacy", postback="nomica.oral.confirm:" + legacy_id)).status_code == 200
    assert counts(engine, data) == (1, 0, 1000)

    for label in ("cancel", "expired"):
        assert send(lunch(label)).status_code == 200
        selection = replies[-1].messages[0].to_dict()["contents"]["footer"]["contents"][0]["action"]["data"]
        assert send(event_dict("pick-" + label, postback=selection)).status_code == 200
        card = replies[-1].messages[0].to_dict()
        confirm = card["contents"]["footer"]["contents"][0]["action"]["data"]
        draft_id = confirm.rsplit(":", 1)[-1]
        if label == "cancel":
            cancel = card["contents"]["footer"]["contents"][1]["action"]["data"]
            assert send(event_dict("cancel-draft", postback=cancel)).status_code == 200
        else:
            with Session(engine) as session:
                session.execute(update(ai_parse_events_table).where(ai_parse_events_table.c.id == draft_id)
                    .values(created_at=datetime.now(timezone.utc) - timedelta(minutes=31)))
                session.commit()
        assert send(event_dict("confirm-" + label, postback=confirm)).status_code == 200
        assert counts(engine, data) == (1, 0, 1000)


def test_oral_clarification_preserves_draft_and_frozen_account(webhook):
    send, replies, engine, data = webhook
    assert send(lunch("ambiguous", "午餐 80 加飲料 40")).status_code == 200
    assert "補金額" in str(replies[-1].messages[0].to_dict())
    assert send(lunch("invalid-clarify", "補金額 1,2,0")).status_code == 200
    assert "格式不正確" in str(replies[-1].messages[0].to_dict())
    assert send(lunch("clarify", "補金額 120")).status_code == 200
    buttons = replies[-1].messages[0].to_dict()["contents"]["footer"]["contents"]
    choice = next(button["action"]["data"] for button in buttons if button["action"]["label"] == "cash")
    assert send(event_dict("pick", postback=choice)).status_code == 200
    with Session(engine) as session:
        draft = session.execute(select(ai_parse_events_table)).mappings().one()
        assert draft["parsed_payload"]["line_draft"]["account_id"] == data["cash"]
        assert draft["parsed_payload"]["line_draft"]["amount"] == "120"
    assert counts(engine, data) == (1, 0, 1000)


def test_previous_and_pilot_parse_paths_replay_same_model_fixture():
    cases = [
        ("午餐 120 現金", 120, None, "現金", "draft"),
        ("午餐 １２０ 元 現金", 120, None, "現金", "draft"),
        ("晚餐 1,200", 1200, None, None, "choose"),
        ("昨天跟同事吃午餐，刷國泰卡 120", 120, "2026-11-08", "國泰卡", "draft"),
        ("午餐 80 加飲料 40", 120, None, "現金", "clarify"),
        ("上個週末午餐 120", 120, None, "現金", "clarify"),
        ("轉帳 120", 120, None, None, "guide"),
        ("查詢本月支出", 120, None, None, "guide"),
    ]
    baseline_calls = pilot_calls = baseline_ready = pilot_ready = baseline_correct = pilot_correct = 0
    for message, amount, expected_day, account, expected in cases:
        calls = []
        class Model:
            def parse(self, text):
                calls.append(text)
                return {"type": "expense", "category": "午餐", "budget_category": "伙食",
                        "amount": amount, "target_asset": account, "currency": "TWD"}

        parser = AIParseService(None, "", gemini_parser=Model())
        parser._today = lambda: date(2026, 11, 9)
        old = parser.parse(message)["legacy"]
        baseline_calls += len(calls)
        old_expense = old.get("type") == "expense"
        # The previous preview allowed an expense with no account attached.
        old_behavior = ("draft" if old.get("target_asset") else "unlinked") if old_expense else "guide"
        baseline_ready += old_expense
        baseline_correct += old_behavior == expected
        calls.clear()

        parsed, _ = parse_oral(parser, message)
        pilot_calls += len(calls)
        if parsed.get("type") == "expense":
            fields = oral_payload(parser, message, parsed, money)
            behavior = ("clarify" if not fields["amount"] or not fields["date"] else
                        "draft" if parsed.get("target_asset") else "choose")
            if behavior != "clarify":
                assert Decimal(fields["amount"]) == amount
                assert fields["date"] == (expected_day or "2026-11-09")
                assert parsed.get("target_asset") == account
        else:
            behavior = "guide"
        assert behavior == expected, message
        pilot_ready += behavior == "draft"
        pilot_correct += behavior == expected

    print(f"Baseline: {baseline_correct}/8 expected, {baseline_ready} drafts, {baseline_calls} model calls")
    print(f"Pilot: {pilot_correct}/8 expected, {pilot_ready} drafts, {pilot_calls} model calls")
    assert (baseline_correct, baseline_ready, baseline_calls) == (5, 6, 6)
    # The Web's local rules now answer most of these sentences, so only one still needs the model.
    assert (pilot_correct, pilot_ready, pilot_calls) == (8, 3, 1)


def test_natural_sentence_uses_same_draft_card_for_card_alias(webhook, monkeypatch):
    send, replies, engine, data = webhook
    monkeypatch.setattr(AIParseService, "_today", lambda self: date(2026, 11, 9))
    with Session(engine) as session:
        created = AssetManager(session).add_account(data["a"], "國泰信用卡", "credit_card", 500)
        session.commit()
    assert send(lunch("spoken", "昨天跟同事吃午餐，刷國泰卡 120")).status_code == 200
    card = replies[-1].messages[0].to_dict()["contents"]
    assert card["footer"]["contents"][0]["action"]["data"].startswith("nomica.oral.confirm:")
    with Session(engine) as session:
        draft = session.scalar(select(ai_parse_events_table.c.parsed_payload))["line_draft"]
        assert (draft["date"], draft["account_id"], draft["amount"]) == ("2026-11-08", str(created.account_id), "120")
    assert counts(engine, data) == (1, 0, 1000)
    confirm = card["footer"]["contents"][0]["action"]["data"]
    assert send(event_dict("spoken-confirm", postback=confirm)).status_code == 200
    assert "記帳完成" in str(replies[-1].messages[0].to_dict())
    with Session(engine) as session:
        assert session.scalar(select(accounts_table.c.balance).where(
            accounts_table.c.id == created.account_id,
        )) == 380


def test_convenience_store_is_not_a_transaction_date():
    parser = AIParseService(None, "")
    parser._today = lambda: date(2026, 11, 9)
    fields = oral_payload(
        parser, "在7-11買了可口可樂，付了現金30元",
        {"type": "expense", "amount": 30, "currency": "TWD"}, money,
    )
    assert (fields["date"], fields["amount"]) == ("2026-11-09", "30")


@pytest.mark.parametrize(("message", "parsed", "field"), [
    ("昨天或11/7午餐 120", {"amount": 120}, "date"),
    ("11/7或11/8午餐 120", {"amount": 120}, "date"),
    ("前些日子午餐 120", {"amount": 120, "date": "2026-11-04"}, "date"),
    ("午餐 120.5.2 元", {"amount": "120.5"}, "amount"),
    ("午餐 120JPY", {"amount": 120, "currency": "TWD"}, "original_currency"),
])
def test_uncertain_fields_are_not_frozen(message, parsed, field):
    parser = AIParseService(None, "")
    parser._today = lambda: date(2026, 11, 9)
    fields = oral_payload(parser, message, {"type": "expense", **parsed}, money)
    assert fields[field] is None


def test_signed_oral_ai_requests_consent_and_only_sends_when_needed(webhook, monkeypatch):
    from sqlalchemy.orm import sessionmaker
    from models.line_ai_gateway import LineAIGateway
    from models.linebot.manager import LineBotManager
    from models.schema import line_ai_attempts, line_ai_control
    from tests.test_line_ai_gateway import Provider

    send, replies, engine, data = webhook
    with engine.begin() as conn:
        conn.execute(line_ai_control.insert().values(id=1, enabled=True))
    with Session(engine) as session:
        card_account = AssetManager(session).add_account(data["a"], "國泰信用卡", "credit_card", 500)
        session.commit()
    provider = Provider()
    provider.text = ('{"type":"expense","category":"午餐","budget_category":"伙食",'
                     '"amount":120,"currency":"TWD","target_asset":"國泰卡"}')
    gateway = LineAIGateway(sessionmaker(bind=engine), provider, Decimal("1"))
    monkeypatch.setattr(LineBotManager, "line_ai_gateway", gateway, raising=False)

    # 「聚會」 is not a category the rules know, so this sentence needs the model.
    spoken = "昨天跟同事聚會，刷國泰卡 120"
    assert send(lunch("needs-consent", spoken)).status_code == 200
    assert "同意 AI" in str(replies[-1].messages[0].to_dict())
    assert not provider.calls
    assert send(lunch("consent", "同意 AI")).status_code == 200
    assert "Google Gemini" in str(replies[-1].messages[0].to_dict())
    assert send(lunch("quick", "午餐 120 現金")).status_code == 200
    assert send(lunch("greeting", "你好")).status_code == 200
    assert send(lunch("secret", "午餐 120，卡號 4111 1111 1111 1111")).status_code == 200
    assert "請移除" in str(replies[-1].messages[0].to_dict())
    assert not provider.calls
    assert send(lunch("spoken", spoken)).status_code == 200
    card = replies[-1].messages[0].to_dict()["contents"]
    confirm = card["footer"]["contents"][0]["action"]["data"]
    assert confirm.startswith("nomica.oral.confirm:")
    assert "國泰信用卡" in str(card)
    assert send(lunch("spoken", spoken)).status_code == 200
    assert len(provider.calls) == 2
    assert counts(engine, data) == (1, 0, 1000)
    assert send(event_dict("confirm-ai", postback=confirm)).status_code == 200
    assert send(event_dict("confirm-ai-again", postback=confirm)).status_code == 200
    assert send(lunch("withdraw", "撤回 AI")).status_code == 200
    assert send(lunch("after-withdraw", spoken)).status_code == 200
    assert "同意 AI" in str(replies[-1].messages[0].to_dict())
    assert len(provider.calls) == 2
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(line_ai_attempts)) == 1
        assert session.scalar(select(accounts_table.c.balance).where(
            accounts_table.c.id == card_account.account_id,
        )) == 380
    assert counts(engine, data) == (2, 1, 1000)


def _footer(reply):
    return reply.messages[0].to_dict()["contents"]["footer"]["contents"]


def _labels(reply):
    return [button["action"]["label"] for button in _footer(reply)]


def _draft(engine, draft_id=None):
    with Session(engine) as session:
        query = select(ai_parse_events_table)
        query = (query.where(ai_parse_events_table.c.id == draft_id) if draft_id
                 else query.order_by(ai_parse_events_table.c.created_at.desc()))
        return session.execute(query).mappings().first()


def _many_accounts(engine, data):
    from models.budget_manager import BudgetManager
    with Session(engine) as session:
        assets = AssetManager(session)
        for i in range(1, 11):
            assets.add_account(data["a"], f"帳戶{i:02d}", "cash", 100)
        assets.add_account(data["a"], "Foreign", "cash", 500, currency="JPY")
        session.commit()
        ids = {row.name: row.id for row in session.execute(
            select(accounts_table.c.name, accounts_table.c.id).where(accounts_table.c.user_id == data["a"]))}
    today = date.today().isoformat()
    # Two uses of 帳戶07, then one later use of 帳戶03: 03 is latest, 07 is most used.
    for name in ("帳戶07", "帳戶07", "帳戶03"):
        with Session(engine) as session:
            BudgetManager(session).add_transaction(
                data["a"], today, "usage", 10, "expense", "伙食", account_id=str(ids[name]),
                client_request_id=uuid4())
            session.commit()
    return ids


def test_account_menu_orders_by_usage_and_pages_beyond_eight(webhook):
    send, replies, engine, data = webhook
    ids = _many_accounts(engine, data)
    assert send(lunch("menu")).status_code == 200
    labels = _labels(replies[-1])
    # 12 TWD accounts: latest-used first, then most-used, 8 per page plus a "more" button.
    assert labels[:2] == ["帳戶03", "帳戶07"]
    assert len(labels) == 9 and labels[-1] == "更多帳戶（2/2）"
    assert "Foreign" not in labels

    draft = _draft(engine)
    assert send(event_dict("more", postback=f"nomica.oral.more:{draft['id']}:1")).status_code == 200
    second = _labels(replies[-1])
    assert len(second) == 5 and second[-1] == "更多帳戶（1/2）"
    assert not set(second[:-1]) & set(labels[:-1])

    # A button from the first page still works after paging.
    first_page_id = ids["帳戶03"]
    assert send(event_dict("pick", postback=f"nomica.oral.account:{draft['id']}:{first_page_id}")).status_code == 200
    assert "確認" in str(replies[-1].messages[0].to_dict())
    assert _draft(engine)["parsed_payload"]["line_draft"]["account_id"] == str(first_page_id)


def test_typed_account_name_selects_only_own_same_currency_account(webhook):
    send, replies, engine, data = webhook
    ids = _many_accounts(engine, data)
    assert send(lunch("menu")).status_code == 200
    waiting = _draft(engine)["id"]
    # Another user's account and a different-currency account are never chosen by name.
    for i, name in enumerate(("B cash", "Foreign")):
        assert send(lunch(f"other-{i}", name)).status_code == 200
        assert "確認收支" not in str(replies[-1].messages[0].to_dict())
        assert _draft(engine, waiting)["parsed_payload"]["line_draft"].get("account_id") is None
    assert send(lunch("typed", "帳戶05")).status_code == 200
    assert "確認" in str(replies[-1].messages[0].to_dict())
    assert _draft(engine, waiting)["parsed_payload"]["line_draft"]["account_id"] == str(ids["帳戶05"])
    # Nothing is recorded until the confirm card is used.
    assert counts(engine, data)[0] == 4


def _draft_ready_to_confirm(send, replies):
    assert send(lunch()).status_code == 200
    buttons = replies[-1].messages[0].to_dict()["contents"]["footer"]["contents"]
    selection = next(b["action"]["data"] for b in buttons if b["action"]["label"] == "cash")
    assert send(event_dict("pick", postback=selection)).status_code == 200
    return replies[-1].messages[0].to_dict()["contents"]["footer"]["contents"][0]["action"]["data"]


def test_lost_reply_is_retried_without_creating_a_second_draft(webhook):
    send, replies, engine, data = webhook
    api = send.bot.line_bot_api
    original = api.reply_message
    failures = []

    def lose_first_reply(request):
        if not failures:
            failures.append(request)
            raise RuntimeError("Lost external reply after DB commit")
        original(request)

    api.reply_message = lose_first_reply
    assert send(lunch()).status_code == 503
    assert send(lunch()).status_code == 200
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ai_parse_events_table)) == 1


def test_failed_confirmation_rolls_back_everything_and_can_be_retried(webhook, monkeypatch):
    send, replies, engine, data = webhook
    confirm = _draft_ready_to_confirm(send, replies)
    draft_id = confirm.rsplit(":", 1)[-1]
    original = AIParseEventManager.confirm_event

    def fail(*args, **kwargs):
        raise RuntimeError("Injected draft update failure after financial write")

    monkeypatch.setattr(AIParseEventManager, "confirm_event", fail)
    assert send(event_dict("confirm-once", postback=confirm)).status_code == 503
    assert counts(engine, data) == (1, 0, 1000)
    with Session(engine) as session:
        assert session.scalar(select(ai_parse_events_table.c.status).where(
            ai_parse_events_table.c.id == draft_id)) == "success"
    monkeypatch.setattr(AIParseEventManager, "confirm_event", original)
    assert send(event_dict("confirm-once", postback=confirm)).status_code == 200
    assert counts(engine, data) == (2, 1, 880)
