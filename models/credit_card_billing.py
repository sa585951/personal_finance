"""信用卡帳期規則；只計算日期，不推論帳單金額或繳款狀態。"""

from calendar import monthrange
from datetime import date


def _month(year, month, offset):
    index = year * 12 + month - 1 + offset
    return index // 12, index % 12 + 1


def _cycle_date(year, month, day):
    return date(year, month, min(day, monthrange(year, month)[1]))


def normalize_billing(value, *, today=None):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("信用卡帳期格式不正確")

    fields = {}
    for name, label in (("closing_day", "結帳日"), ("due_day", "繳款日")):
        raw = value.get(name)
        if isinstance(raw, bool) or not isinstance(raw, int) or not 1 <= raw <= 31:
            raise ValueError(f"{label}必須是 1 至 31 日")
        fields[name] = raw

    offset = value.get("due_month_offset")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset not in (0, 1):
        raise ValueError("繳款月份必須是結帳當月或次月")
    fields["due_month_offset"] = offset

    # 當月繳款規則必須在所有月份都晚於結帳日；月底縮短時不能變成同一天。
    if offset == 0:
        for year in (2025, 2028):
            for month in range(1, 13):
                if _cycle_date(year, month, fields["due_day"]) <= _cycle_date(
                    year, month, fields["closing_day"]
                ):
                    raise ValueError("當月繳款日必須晚於每月結帳日")

    closing_raw = value.get("override_closing_date") or None
    due_raw = value.get("override_due_date") or None
    if bool(closing_raw) != bool(due_raw):
        raise ValueError("當期截止日修正需要對應的結帳週期")
    if closing_raw:
        try:
            closing_date = date.fromisoformat(closing_raw)
            due_date = date.fromisoformat(due_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("當期截止日格式不正確") from exc
        if closing_date.isoformat() != closing_raw or due_date.isoformat() != due_raw:
            raise ValueError("當期截止日格式不正確")
        if closing_date != _cycle_date(closing_date.year, closing_date.month, fields["closing_day"]):
            raise ValueError("修正日期不屬於此信用卡的結帳週期")
        if due_date <= closing_date or (today and due_date < today):
            raise ValueError("當期截止日必須晚於結帳日且不得早於今日")
        fields["override_closing_date"] = closing_date
        fields["override_due_date"] = due_date
    else:
        fields["override_closing_date"] = None
        fields["override_due_date"] = None
    return fields


def billing_schedule(profile, today):
    closing_days = []
    due_days = []
    for offset in range(-2, 4):
        year, month = _month(today.year, today.month, offset)
        closing_date = _cycle_date(year, month, profile["closing_day"])
        if closing_date >= today:
            closing_days.append(closing_date)
        due_year, due_month = _month(year, month, profile["due_month_offset"])
        due_date = _cycle_date(due_year, due_month, profile["due_day"])
        source = "estimated"
        if profile.get("override_closing_date") == closing_date:
            due_date = profile["override_due_date"]
            source = "user_set"
        if due_date >= today:
            due_days.append((due_date, closing_date, source))

    next_due, due_closing, source = min(due_days, key=lambda item: item[0])
    return {
        "next_closing_date": min(closing_days).isoformat(),
        "next_due_date": next_due.isoformat(),
        "next_due_closing_date": due_closing.isoformat(),
        "next_due_date_source": source,
        "today": today.isoformat(),
    }
