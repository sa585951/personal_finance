"""One-tap starter account: created once, never next to an existing account."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.asset_manager import AssetManager
from models.schema import accounts_table
from models.user_manager import UserManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def account_rows(session, user_id):
    return session.execute(select(accounts_table).where(
        accounts_table.c.user_id == user_id, accounts_table.c.deleted_at.is_(None))).mappings().all()


def test_new_person_gets_one_cash_account_and_repeats_change_nothing(command_db):
    engine, _ = command_db
    with Session(engine) as s:
        fresh = UserManager(s).get_or_create_user_for_identity("qa", "onboarding-new", "New")["id"]
        s.commit()
        assets = AssetManager(s)
        first_id, created = assets.ensure_first_cash_account(fresh)
        s.commit()
        assert created is True
        again_id, created_again = assets.ensure_first_cash_account(fresh)
        assert created_again is False and again_id == first_id
        rows = account_rows(s, fresh)
        assert len(rows) == 1
        assert rows[0]["name"] == "現金" and rows[0]["type"] == "cash"
        assert rows[0]["currency"] == "TWD" and rows[0]["balance"] == 0


def test_someone_with_an_account_never_gets_a_second_one(command_db):
    engine, data = command_db
    with Session(engine) as s:
        before = len(account_rows(s, data["a"]))
        assert before >= 1
        _, created = AssetManager(s).ensure_first_cash_account(data["a"])
        s.commit()
        assert created is False
        assert len(account_rows(s, data["a"])) == before
