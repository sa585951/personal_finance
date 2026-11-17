"""Local rules: more income words, and naming an account by its short name."""
import pytest
from sqlalchemy.orm import Session

from models.ai_parse_service import AIParseService
from models.asset_manager import AssetManager
from models.linebot.oral_pilot import confident_local
from tests.test_financial_command_idempotency import command_db  # noqa: F401

SERVICE = AIParseService(None, "")


@pytest.mark.parametrize("sentence,category", [
    ("租屋補助 5000", "報銷/補貼"),
    ("育兒津貼 2500", "報銷/補貼"),
    ("退稅 3500", "報銷/補貼"),
    ("年終 80000", "獎金"),
    ("股利 1200", "利息"),
    ("配息 300", "利息"),
    ("加班費 2400", "薪資"),
    ("薪水 50000", "薪資"),
])
def test_income_words_are_understood_by_the_local_rules(sentence, category):
    transaction = SERVICE.parse_local(sentence)["transaction"]
    assert transaction["type"] == "income"
    assert transaction["amount"] == str(int("".join(ch for ch in sentence if ch.isdigit())))
    # The category shows up as the budget category (「租屋補助」) or as the title (「年終」 -> 獎金).
    assert category in (transaction["budget_category"], transaction["title"])
    assert confident_local(SERVICE, sentence)  # LINE trusts it too, without asking a model


@pytest.mark.parametrize("sentence", ["午餐 120", "紅包 1000", "計程車 280", "跟朋友吃飯 320"])
def test_ambiguous_or_spending_words_stay_expenses(sentence):
    assert SERVICE.parse_local(sentence)["transaction"]["type"] == "expense"


def test_a_red_envelope_is_income_only_when_the_sentence_says_so():
    result = SERVICE.parse_local("紅包 收入 1000")["transaction"]
    assert result["type"] == "income" and result["title"] == "禮金/贈與"


def add_accounts(session, user_id, *names):
    assets = AssetManager(session)
    for name, kind in names:
        assets.add_account(user_id, name, kind, 0)
    session.commit()


def test_a_bare_short_name_selects_the_one_matching_account(command_db):
    engine, data = command_db
    with Session(engine) as s:
        add_accounts(s, data["a"], ("玉山銀行", "bank"), ("國泰世華", "bank"))
        assets = AssetManager(s)
        asset, token = assets.find_asset_mentioned_in(data["a"], "租屋補助 5000 玉山")
        assert asset["bank_name"] == "玉山銀行" and token == "玉山"
        asset, _ = assets.find_asset_mentioned_in(data["a"], "國泰世華 薪水 50000")
        assert asset["bank_name"] == "國泰世華"
        assert assets.find_asset_mentioned_in(data["a"], "租屋補助 5000") is None
        assert assets.find_asset_mentioned_in(data["a"], "午餐 120 現金") is None  # a type word names no account


def test_two_accounts_sharing_the_word_are_never_guessed(command_db):
    engine, data = command_db
    with Session(engine) as s:
        add_accounts(s, data["a"], ("玉山銀行", "bank"), ("玉山信用卡", "credit_card"))
        assert AssetManager(s).find_asset_mentioned_in(data["a"], "租屋補助 5000 玉山") is None


def test_other_peoples_accounts_are_never_matched(command_db):
    engine, data = command_db
    with Session(engine) as s:
        add_accounts(s, data["b"], ("永豐銀行", "bank"))
        assert AssetManager(s).find_asset_mentioned_in(data["a"], "租屋補助 5000 永豐") is None


def test_removing_account_words_keeps_the_title_readable():
    assert AssetManager.remove_account_words("租屋補助 玉山", "玉山") == "租屋補助"
    assert AssetManager.remove_account_words("玉山", "玉山") == "玉山"  # never leave it empty


def test_latin_account_names_are_never_matched_by_accident(command_db):
    engine, data = command_db
    with Session(engine) as s:
        # The fixture person owns accounts named "cash" and "bank"; "B cash" is someone else's.
        assert AssetManager(s).find_asset_mentioned_in(data["a"], "午餐 120 B cash") is None


def test_web_parse_fills_the_account_and_cleans_the_title(monkeypatch):
    from tests.test_ai_parse_api import FakeAssetManager, FakeDBSession, FakeLineBotManager, _auth_headers, _load_web_app

    class Assets(FakeAssetManager):
        def find_asset_mentioned_in(self, user_id, text, currency=None):
            return {"account_key": "acc-1", "bank_name": "玉山銀行"}, "玉山"

        @staticmethod
        def remove_account_words(title, token):
            return AssetManager.remove_account_words(title, token)

    web_app = _load_web_app(monkeypatch)
    manager = FakeLineBotManager()
    manager.message_parser.ai_parse_service = SERVICE
    monkeypatch.setattr(web_app, "linebot_manager", manager)
    monkeypatch.setattr(web_app, "db_session", FakeDBSession())
    monkeypatch.setattr(web_app, "asset_manager", Assets())
    response = web_app.app.test_client().post("/api/parse/local", json={"text": "租屋補助 5000 玉山"},
                                              headers=_auth_headers())
    assert response.status_code == 200
    transaction = response.get_json()["data"]["parse_result"]["transaction"]
    assert transaction["type"] == "income" and transaction["amount"] == "5000"
    assert transaction["account_id"] == "acc-1" and transaction["account_name"] == "玉山銀行"
    assert transaction["title"] == "租屋補助"
