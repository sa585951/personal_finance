"""One shared exchange rate per trip: defaults for new expenses, owner-only edits, and explicit re-apply."""
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.budget_manager import BudgetManager
from models.reconciliation_manager import ReconciliationManager
from models.schema import accounts_table, transaction_splits_table, transactions_table, trip_exchange_rate_changes_table
from models.trip_rates import TripRateManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def jpy_expense(session, data, amount=1000, paid_by="am", account=None, rate=None, date="2026-10-02"):
    budget = BudgetManager(session)
    budget.add_transaction(
        data["a"] if paid_by == "am" else data["b"], date, "Ramen", amount, "expense", "伙食", trip_id=data["trip"],
        paid_by_member_id=data[paid_by], split_member_ids=[data["am"], data["bm"]], original_currency="JPY",
        account_id=account, exchange_rate=rate)
    return budget.last_created_transaction_id


def row(session, tx_id):
    return session.execute(select(transactions_table).where(transactions_table.c.id == tx_id)).mappings().one()


def test_new_expenses_default_to_the_trip_rate_but_an_explicit_rate_still_wins(command_db):
    engine, data = command_db
    with Session(engine) as s:
        rates = TripRateManager(s)
        # No trip rate yet: the built-in reference rate (JPY 0.22) is used.
        assert row(s, jpy_expense(s, data))["converted_amount"] == Decimal("220")
        rates.set_rate(data["a"], data["trip"], "JPY", "0.215")
        assert row(s, jpy_expense(s, data))["converted_amount"] == Decimal("215")
        assert row(s, jpy_expense(s, data, rate="0.2"))["converted_amount"] == Decimal("200")
        # An expense in the trip's own currency is untouched by any rate.
        BudgetManager(s).add_transaction(data["a"], "2026-10-02", "Taxi", 500, "expense", "交通", trip_id=data["trip"],
                                         paid_by_member_id=data["am"], split_member_ids=[data["am"]])
        assert s.scalar(select(transactions_table.c.converted_amount).where(
            transactions_table.c.title == "Taxi")) == Decimal("500")


def test_only_the_owner_sets_rates_and_values_are_validated(command_db):
    engine, data = command_db
    with Session(engine) as s:
        rates = TripRateManager(s)
        with pytest.raises(ValueError, match="owner"):
            rates.set_rate(data["b"], data["trip"], "JPY", "0.215")
        for bad in ("0", "-1", "abc", "", None, "1000001", "0.123456789", "NaN", "Infinity"):
            with pytest.raises(ValueError):
                rates.set_rate(data["a"], data["trip"], "JPY", bad)
        for currency in ("TWD", "XXX", ""):
            with pytest.raises(ValueError):
                rates.set_rate(data["a"], data["trip"], currency, "0.215")
        listing = TripRateManager(s).list_rates(data["b"], data["trip"])  # a member may read
        assert listing["is_owner"] is False
        assert {r["currency"] for r in listing["rates"]} == {"JPY", "KRW", "USD", "EUR"}


def test_changing_a_rate_leaves_recorded_expenses_alone_and_is_logged(command_db):
    engine, data = command_db
    with Session(engine) as s:
        rates = TripRateManager(s)
        rates.set_rate(data["a"], data["trip"], "JPY", "0.215")
        first = jpy_expense(s, data)
        result = rates.set_rate(data["a"], data["trip"], "JPY", "0.23")
        assert result["changed"] is True and result["different_count"] == 1
        assert row(s, first)["exchange_rate"] == Decimal("0.215") and row(s, first)["converted_amount"] == Decimal("215")
        assert rates.set_rate(data["a"], data["trip"], "JPY", "0.23")["changed"] is False  # same value: no log
        listing = rates.list_rates(data["a"], data["trip"])
        history = listing["history"]
        assert [(h["old_rate"], h["new_rate"], h["action"]) for h in history] == [("0.215", "0.23", "set"), (None, "0.215", "set")]
        assert history[0]["changed_by_name"] == "A"
        jpy = next(r for r in listing["rates"] if r["currency"] == "JPY")
        assert jpy["rate"] == "0.23" and jpy["recorded_expenses"] == 1 and jpy["default_rate"] == "0.22"


def test_preview_then_apply_updates_expenses_splits_and_linked_accounts_consistently(command_db):
    engine, data = command_db
    with Session(engine) as s:
        rates = TripRateManager(s)
        rates.set_rate(data["a"], data["trip"], "JPY", "0.2")
        linked = jpy_expense(s, data, 1000, "am", account=str(data["cash"]))  # A paid with a TWD account
        unlinked = jpy_expense(s, data, 500, "bm")  # B paid, no account
        s.flush()
        before_bank = s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data["cash"]))
        rates.set_rate(data["a"], data["trip"], "JPY", "0.25")
        preview = rates.preview_apply(data["a"], data["trip"], "JPY")
        assert preview["count"] == 2 and preview["locked"] is False
        assert Decimal(preview["old_total"]) == Decimal("300") and Decimal(preview["new_total"]) == Decimal("375")
        assert preview["account_adjustment_count"] == 1 and Decimal(preview["account_adjustment_total"]) == Decimal("50")
        changes = {m["display_name"]: Decimal(m["change"]) for m in preview["members"]}
        assert sum(changes.values()) == 0  # what one member is owed more, others owe more
        assert rates.preview_apply(data["a"], data["trip"], "JPY") == preview  # previewing changes nothing
        assert row(s, linked)["converted_amount"] == Decimal("200")

        assert rates.apply_rate(data["a"], data["trip"], "JPY")["updated"] == 2
        assert row(s, linked)["converted_amount"] == Decimal("250") and row(s, unlinked)["converted_amount"] == Decimal("125")
        for tx_id, expected in ((linked, Decimal("250")), (unlinked, Decimal("125"))):
            shares = s.execute(select(transaction_splits_table).where(
                transaction_splits_table.c.transaction_id == tx_id)).mappings().all()
            assert sum(sh["converted_share_amount"] for sh in shares) == expected  # shares still add up
            assert all(sh["exchange_rate"] == Decimal("0.25") for sh in shares)
        # The payer's TWD account moved by exactly the converted difference, and the books still reconcile.
        assert s.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data["cash"])) == before_bank - Decimal("50")
        assert ReconciliationManager(s).reconcile()["summary"]["mismatched"] == 0
        assert rates.preview_apply(data["a"], data["trip"], "JPY")["count"] == 0  # nothing left to re-apply
        log = s.execute(select(trip_exchange_rate_changes_table).where(
            trip_exchange_rate_changes_table.c.action == "apply")).mappings().one()
        assert log["affected_count"] == 2 and log["new_rate"] == Decimal("0.25")


def test_apply_is_owner_only_and_needs_a_rate_and_is_refused_after_a_settlement(command_db):
    engine, data = command_db
    with Session(engine) as s:
        rates = TripRateManager(s)
        jpy_expense(s, data)
        with pytest.raises(ValueError, match="匯率"):
            rates.preview_apply(data["a"], data["trip"], "JPY")  # no trip rate set yet
        rates.set_rate(data["a"], data["trip"], "JPY", "0.3")
        with pytest.raises(ValueError, match="owner"):
            rates.apply_rate(data["b"], data["trip"], "JPY")
        BudgetManager(s).create_trip_settlement(data["a"], data["trip"], data["bm"], data["am"], 100,
                                                settled_on="2026-10-02", client_request_id="00000000-0000-4000-8000-000000000001")
        assert rates.list_rates(data["a"], data["trip"])["locked"] is True
        assert rates.preview_apply(data["a"], data["trip"], "JPY")["locked"] is True
        with pytest.raises(ValueError, match="還款紀錄"):
            rates.apply_rate(data["a"], data["trip"], "JPY")
        # New expenses still use the rate; only re-applying to recorded ones is locked.
        assert row(s, jpy_expense(s, data))["converted_amount"] == Decimal("300")


def test_a_failure_part_way_leaves_every_expense_unchanged(command_db, monkeypatch):
    engine, data = command_db
    with Session(engine) as s:
        rates = TripRateManager(s)
        rates.set_rate(data["a"], data["trip"], "JPY", "0.2")
        ids = [jpy_expense(s, data, 1000), jpy_expense(s, data, 2000)]
        rates.set_rate(data["a"], data["trip"], "JPY", "0.3")
        s.commit()
    with Session(engine) as s:
        rates = TripRateManager(s)
        original = TripRateManager._resave
        calls = []

        def flaky(self, row_, rate):
            if calls:
                raise ValueError("boom")
            calls.append(1)
            return original(self, row_, rate)

        monkeypatch.setattr(TripRateManager, "_resave", flaky)
        with pytest.raises(ValueError, match="boom"):
            rates.apply_rate(data["a"], data["trip"], "JPY")
        s.rollback()  # the API layer rolls back on any error
    with Session(engine) as s:
        assert [row(s, i)["converted_amount"] for i in ids] == [Decimal("200"), Decimal("400")]
        assert s.scalar(select(func.count()).select_from(trip_exchange_rate_changes_table).where(
            trip_exchange_rate_changes_table.c.action == "apply")) == 0


def test_apply_that_would_overdraw_a_payer_account_is_refused_with_a_clear_message(command_db):
    engine, data = command_db
    with Session(engine) as s:
        rates = TripRateManager(s)
        rates.set_rate(data["a"], data["trip"], "JPY", "0.2")
        jpy_expense(s, data, 4000, "am", account=str(data["cash"]))  # 800 TWD of a 1000 TWD account
        rates.set_rate(data["a"], data["trip"], "JPY", "0.5")  # would now cost 2000
        with pytest.raises(ValueError, match="整批都沒有變動"):
            rates.apply_rate(data["a"], data["trip"], "JPY")
