"""LINE read-only cards, one-tap repeats of recent entries, and editing a draft before confirming."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.schema import ai_parse_events_table, categories_table, transactions_table
from tests.line_fixtures import command_db, event_dict, line_db  # noqa: F401
from tests.test_line_shortcut_pilot import counts, lunch, webhook  # noqa: F401


def _card(replies):
    return replies[-1].messages[0].to_dict()


def _chips(replies):
    return (_card(replies).get("quickReply") or {}).get("items", [])


def _confirm_a_lunch(send, replies, label="first"):
    assert send(lunch(label)).status_code == 200
    buttons = _card(replies)["contents"]["footer"]["contents"]
    pick = next(b["action"]["data"] for b in buttons if b["action"]["label"] == "cash")
    assert send(event_dict("pick-" + label, postback=pick)).status_code == 200
    confirm = _card(replies)["contents"]["footer"]["contents"][0]["action"]["data"]
    assert send(event_dict("confirm-" + label, postback=confirm)).status_code == 200


def test_query_commands_reply_with_cards_and_change_nothing(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    before = counts(engine, data)
    for command, title in (("今天", "今天"), ("本月", "本月"), ("餘額", "帳戶餘額"), ("最近", "最近紀錄")):
        assert send(lunch("q-" + command, text=command)).status_code == 200
        card = _card(replies)
        assert title in card["altText"], command
        labels = [item["action"]["label"] for item in _chips(replies)]
        assert labels[:4] == ["今天", "本月", "餘額", "最近"]
    assert counts(engine, data) == before
    assert send(lunch("balances", text="餘額")).status_code == 200
    assert "1,000" in str(_card(replies))  # the cash account balance


def test_other_people_get_only_their_own_numbers(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    assert send(lunch("a-balance", text="餘額")).status_code == 200
    mine = str(_card(replies))
    assert send({**lunch("b-balance", text="餘額"), "source": {"type": "user", "userId": "U-fix-b"}}).status_code == 200
    theirs = str(_card(replies))
    assert mine != theirs


def test_a_recent_entry_repeats_with_one_tap_and_still_needs_confirmation(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    _confirm_a_lunch(send, replies)
    assert counts(engine, data)[2] == 880
    assert send(lunch("again-menu", text="最近")).status_code == 200
    repeats = [i for i in _chips(replies) if i["action"]["type"] == "postback"]
    assert repeats and repeats[0]["action"]["label"] == "午餐 120"
    assert send(event_dict("tap-repeat", postback=repeats[0]["action"]["data"])).status_code == 200
    card = _card(replies)
    assert card["altText"] == "確認收支：尚未記帳"
    assert "quickReply" not in card  # no shortcut chips beside a confirm button
    assert counts(engine, data)[2] == 880  # nothing is booked until confirmed
    confirm = card["contents"]["footer"]["contents"][0]["action"]["data"]
    assert send(event_dict("confirm-repeat", postback=confirm)).status_code == 200
    assert counts(engine, data)[2] == 760


def test_a_repeat_cannot_copy_someone_elses_transaction(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    _confirm_a_lunch(send, replies)
    with Session(engine) as session:
        tx_id = str(session.scalar(select(transactions_table.c.id).where(
            transactions_table.c.user_id == data["a"], transactions_table.c.title == "午餐")))
    assert send(event_dict("steal", role="b", postback="nomica.oral.again:" + tx_id)).status_code == 200
    assert "找不到這筆紀錄" in str(_card(replies))
    assert send(event_dict("junk", postback="nomica.oral.again:not-a-uuid")).status_code == 200


def test_amount_can_be_corrected_on_the_card_before_confirming(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    assert send(lunch()).status_code == 200
    buttons = _card(replies)["contents"]["footer"]["contents"]
    pick = next(b["action"]["data"] for b in buttons if b["action"]["label"] == "cash")
    assert send(event_dict("pick", postback=pick)).status_code == 200
    assert send(lunch("fix-amount", text="改金額 150")).status_code == 200
    card = _card(replies)
    assert card["altText"] == "確認收支：尚未記帳" and "150" in str(card)
    assert send(lunch("bad-amount", text="改金額 很多")).status_code == 200
    assert "格式不正確" in str(_card(replies))
    confirm = card["contents"]["footer"]["contents"][0]["action"]["data"]
    assert send(event_dict("confirm", postback=confirm)).status_code == 200
    assert counts(engine, data)[2] == 850


def test_category_can_be_changed_on_the_card_before_confirming(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    assert send(lunch()).status_code == 200
    buttons = _card(replies)["contents"]["footer"]["contents"]
    pick = next(b["action"]["data"] for b in buttons if b["action"]["label"] == "cash")
    assert send(event_dict("pick", postback=pick)).status_code == 200
    footer = _card(replies)["contents"]["footer"]["contents"]
    change = next(b["action"]["data"] for b in footer if b["action"]["label"] == "改分類")
    assert send(event_dict("cats", postback=change)).status_code == 200
    assert _card(replies)["altText"] == "選擇分類"
    options = _card(replies)["contents"]["footer"]["contents"]
    other = next(b for b in options if b["action"]["label"] == "交通")
    assert send(event_dict("cat", postback=other["action"]["data"])).status_code == 200
    card = _card(replies)
    assert "交通" in str(card["contents"]["body"])
    confirm = card["contents"]["footer"]["contents"][0]["action"]["data"]
    assert send(event_dict("confirm", postback=confirm)).status_code == 200
    with Session(engine) as session:
        name = session.scalar(select(categories_table.c.name).join(
            transactions_table, transactions_table.c.category_id == categories_table.c.id
        ).where(transactions_table.c.user_id == data["a"], transactions_table.c.title == "午餐"))
        draft = session.execute(select(ai_parse_events_table)).mappings().all()[-1]
    assert name == "交通" and draft["status"] == "confirmed"
    # A forged category id is refused.
    assert send(event_dict("forged", postback=change.replace("cats", "cat") + ":" + data["b_cash"])).status_code == 200


def _follow(eid, user="U-fix-a"):
    return {"type": "follow", "mode": "active", "timestamp": 1792454400000, "webhookEventId": eid,
            "deliveryContext": {"isRedelivery": False}, "replyToken": "follow-token",
            "source": {"type": "user", "userId": user}, "follow": {"isUnblocked": False}}


def test_following_the_account_sends_one_guide_card(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    assert send(_follow("follow-linked")).status_code == 200
    card = _card(replies)
    text = str(card)
    assert card["altText"] == "Nomica 使用說明"
    for expected in ("午餐 120", "今天", "本月", "餘額", "最近", "同意 AI"):
        assert expected in text
    assert "先用同一個 LINE 帳號登入" not in text
    assert [item["action"]["label"] for item in _chips(replies)][:4] == ["今天", "本月", "餘額", "最近"]
    # A redelivery of the same event does not send a second card.
    count = len(replies)
    assert send({**_follow("follow-linked"), "deliveryContext": {"isRedelivery": True}}).status_code == 200
    assert str(replies[-1].messages[0].to_dict()) == text and len(replies) == count + 1


def test_guide_tells_an_unlinked_person_to_sign_in_and_help_shows_the_same_card(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    assert send(_follow("follow-new", user="U-never-seen")).status_code == 200
    assert "先用同一個 LINE 帳號登入" in str(_card(replies))
    assert _chips(replies) == []  # no account, so no personal shortcuts
    assert send(lunch("help", text="幫助")).status_code == 200
    assert _card(replies)["altText"] == "Nomica 使用說明"
    assert "午餐 120" in str(_card(replies))


def test_follow_events_outside_a_one_to_one_chat_are_ignored(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    group = {**_follow("follow-group"), "source": {"type": "group", "groupId": "C-1", "userId": "U-fix-a"}}
    assert send(group).status_code == 200
    assert replies == []


def test_record_command_explains_how_to_enter_a_sentence_and_offers_recent_entries(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    _confirm_a_lunch(send, replies)
    before = counts(engine, data)
    assert send(lunch("record", text="記一筆")).status_code == 200
    card = _card(replies)
    assert card["altText"] == "說一句話就能記帳" and "午餐 120" in str(card)
    assert any(item["action"]["type"] == "postback" for item in _chips(replies))
    assert counts(engine, data) == before  # only an explanation; nothing is booked
    assert send({**lunch("record-unknown", text="記一筆"), "source": {"type": "user", "userId": "U-never-seen"}}).status_code == 200
    assert "登入" in str(_card(replies))


class _ModelThatMustNotRun:
    """Stands in for the AI gateway: refuses with the consent notice and records that it was asked."""

    def __init__(self):
        self.asked = 0

    def generate(self, owner, event_id, prompt):
        from models.line_ai_gateway import CONSENT_NOTICE, AIRequestBlocked
        self.asked += 1
        raise AIRequestBlocked(CONSENT_NOTICE, "consent_required")


def test_everyday_sentences_use_local_rules_without_asking_for_ai(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    gateway = send.bot.line_ai_gateway = _ModelThatMustNotRun()
    for i, text in enumerate(("咖啡 85 星巴克", "午餐麥當勞 150 用現金", "計程車 280 現金")):
        assert send(lunch(f"local-{i}", text=text)).status_code == 200
        card = _card(replies)
        assert "同意 AI" not in str(card), text
        assert "選擇記帳帳戶" in card["altText"] or "確認收支" in card["altText"], text
    assert gateway.asked == 0


def test_local_rules_keep_the_amount_and_category_visible_on_the_card(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    send.bot.line_ai_gateway = _ModelThatMustNotRun()
    assert send(lunch("coffee", text="咖啡 85 星巴克")).status_code == 200
    buttons = _card(replies)["contents"]["footer"]["contents"]
    pick = next(b["action"]["data"] for b in buttons if b["action"]["label"] == "cash")
    assert send(event_dict("pick-coffee", postback=pick)).status_code == 200
    card = str(_card(replies)["contents"]["body"])
    assert "85" in card and "伙食" in card


def test_sentences_the_rules_do_not_understand_still_go_to_ai(webhook):  # noqa: F811
    send, replies, engine, data = webhook
    gateway = send.bot.line_ai_gateway = _ModelThatMustNotRun()
    for i, text in enumerate(("買了一個東西 500", "今天走了 8000 步")):
        assert send(lunch(f"ai-{i}", text=text)).status_code == 200
        assert "同意 AI" in str(_card(replies)), text
    assert gateway.asked == 2
