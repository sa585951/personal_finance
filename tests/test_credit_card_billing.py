from datetime import date

import pytest

from models.credit_card_billing import billing_schedule, normalize_billing


def profile(closing_day=5, due_day=20, due_month_offset=1, **extra):
    return normalize_billing({
        "closing_day": closing_day,
        "due_day": due_day,
        "due_month_offset": due_month_offset,
        **extra,
    })


def test_next_dates_cross_year_and_keep_open_statement_due_date():
    schedule = billing_schedule(profile(), date(2026, 12, 25))

    assert schedule["next_closing_date"] == "2027-01-05"
    assert schedule["next_due_date"] == "2027-01-20"
    assert schedule["next_due_closing_date"] == "2026-12-05"
    assert schedule["next_due_date_source"] == "estimated"


def test_short_month_uses_last_day_including_leap_year():
    billing = profile(31, 31)

    assert billing_schedule(billing, date(2028, 2, 1))["next_closing_date"] == "2028-02-29"
    assert billing_schedule(billing, date(2028, 2, 1))["next_due_date"] == "2028-02-29"
    assert billing_schedule(billing, date(2027, 2, 1))["next_closing_date"] == "2027-02-28"


def test_same_month_rule_and_invalid_collapsed_dates():
    schedule = billing_schedule(profile(5, 20, 0), date(2026, 9, 6))
    assert schedule["next_due_date"] == "2026-09-20"

    with pytest.raises(ValueError, match="晚於每月結帳日"):
        profile(30, 31, 0)


def test_manual_due_date_is_tied_to_exact_closing_cycle():
    billing = profile(
        override_closing_date="2026-09-05",
        override_due_date="2026-10-24",
    )
    schedule = billing_schedule(billing, date(2026, 10, 1))

    assert schedule["next_due_date"] == "2026-10-24"
    assert schedule["next_due_closing_date"] == "2026-09-05"
    assert schedule["next_due_date_source"] == "user_set"


@pytest.mark.parametrize("value", [
    {"closing_day": 0, "due_day": 20, "due_month_offset": 1},
    {"closing_day": 5, "due_day": 32, "due_month_offset": 1},
    {"closing_day": 5, "due_day": 20, "due_month_offset": 2},
    {"closing_day": True, "due_day": 20, "due_month_offset": 1},
])
def test_rejects_invalid_rules(value):
    with pytest.raises(ValueError):
        normalize_billing(value)


def test_rejects_invalid_manual_due_date():
    with pytest.raises(ValueError, match="結帳週期"):
        profile(override_closing_date="2026-09-06", override_due_date="2026-10-20")
    with pytest.raises(ValueError, match="不得早於今日"):
        normalize_billing({
            "closing_day": 5,
            "due_day": 20,
            "due_month_offset": 1,
            "override_closing_date": "2026-09-05",
            "override_due_date": "2026-10-20",
        }, today=date(2026, 10, 21))
