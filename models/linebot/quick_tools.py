"""Read-only LINE cards (today, month, balances, recent) and one-tap repeats of recent entries.

Nothing here writes money: the cards only read the signed-in person's own rows, and a repeat only
prepares the same preview-and-confirm draft that typing a sentence would.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from linebot.v3.messaging import MessageAction, PostbackAction, QuickReply, QuickReplyItem
from sqlalchemy import func, or_, select

from ..asset_manager import AssetManager
from ..budget_manager import BudgetManager
from ..schema import accounts_table, categories_table, transactions_table
from .line_sdk import FlexSendMessage

LOCAL_TZ = ZoneInfo("Asia/Taipei")
QUERY_COMMANDS = {"今天": "today", "本月": "month", "餘額": "balances", "最近": "recent"}
REPEAT_WINDOW_DAYS = 90
MAX_REPEATS = 8           # LINE allows 13 quick-reply items: 4 queries + 8 repeats leaves room.
MAX_BALANCE_ROWS = 10
RECENT_LIMIT = 5
DRAFT_CARD_ALT_TEXTS = {"確認收支：尚未記帳", "選擇記帳帳戶", "選擇分類"}


def today():
    return datetime.now(LOCAL_TZ).date()


def money(value):
    amount = Decimal(str(value or 0))
    return f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"


def info_card(title, rows, note=None):
    body = [{"type": "text", "text": title, "weight": "bold", "size": "md", "wrap": True}]
    for label, value in rows:
        body.append({"type": "box", "layout": "horizontal", "margin": "md", "contents": [
            {"type": "text", "text": label, "size": "sm", "color": "#666666", "wrap": True, "flex": 5},
            {"type": "text", "text": value, "size": "sm", "align": "end", "wrap": True, "flex": 5},
        ]})
    if note:
        body.append({"type": "text", "text": note, "size": "xs", "color": "#888888", "wrap": True, "margin": "lg"})
    return FlexSendMessage(alt_text=title, contents={
        "type": "bubble", "body": {"type": "box", "layout": "vertical", "paddingAll": "20px", "contents": body},
    })


def _own_daily(owner):
    t = transactions_table
    return [t.c.user_id == owner, t.c.trip_id.is_(None), t.c.deleted_at.is_(None),
            t.c.type.in_(("expense", "income"))]


def today_card(session, owner):
    t = transactions_table
    day = today()
    rows = session.execute(
        select(t.c.type, t.c.base_currency, func.sum(t.c.converted_amount), func.count())
        .where(*_own_daily(owner), t.c.transaction_date == day).group_by(t.c.type, t.c.base_currency)
    ).all()
    if not rows:
        return info_card(f"今天 {day:%m/%d}", [("尚無日常收支", "—")], "旅行分帳請到 Nomica Web 查看。")
    lines = []
    for kind, currency, total, count in sorted(rows, key=lambda r: (r[0] != "expense", r[1])):
        lines.append(("支出" if kind == "expense" else "收入", f"{currency} {money(total)}（{count} 筆）"))
    return info_card(f"今天 {day:%m/%d}", lines, "只含日常收支，不含旅行分帳。")


def month_card(session, owner):
    month = today().strftime("%Y-%m")
    try:
        summary = BudgetManager(session).get_budget_summary(owner, month)
    except ValueError:
        return info_card(f"{month} 本月", [("暫時無法統計", "請到 Nomica Web 查看")])
    spent = sum(Decimal(str(item["spent"])) for item in summary)
    budgeted = [item for item in summary if item["budget"] is not None]
    rows = [("本月支出", f"TWD {money(spent)}")]
    if budgeted:
        limit = sum(Decimal(str(item["budget"])) for item in budgeted)
        used = sum(Decimal(str(item["spent"])) for item in budgeted)
        rows.append(("預算使用", f"{money(used)} / {money(limit)}（{used / limit:.0%}）" if limit else "—"))
        over = [item["category"] for item in budgeted if item["remaining"] is not None and item["remaining"] < 0]
        if over:
            rows.append(("已超支", "、".join(over[:4])))
    for item in sorted(summary, key=lambda i: -i["spent"])[:3]:
        if item["spent"] > 0:
            rows.append((item["category"], f"TWD {money(item['spent'])}"))
    if len(rows) == 1 and spent == 0:
        rows = [("本月支出", "尚無紀錄")]
    return info_card(f"{month} 本月", rows, "含你選擇納入月報的旅行分攤。")


def balances_card(session, owner):
    assets = [a for a in AssetManager(session).get_all_assets(owner).values() if a.get("track_balance", True)]
    if not assets:
        return info_card("帳戶餘額", [("尚未建立帳戶", "請到 Nomica Web 新增")])
    rows = [(a["bank_name"], f"{a.get('currency') or 'TWD'} {money(a['balance'])}") for a in assets[:MAX_BALANCE_ROWS]]
    note = f"另有 {len(assets) - MAX_BALANCE_ROWS} 個帳戶，請到 Nomica Web 查看。" if len(assets) > MAX_BALANCE_ROWS else None
    return info_card("帳戶餘額", rows, note)


def recent_card(session, owner):
    t, c = transactions_table, categories_table
    rows = session.execute(
        select(t.c.transaction_date, t.c.title, t.c.type, t.c.original_amount, t.c.original_currency,
               t.c.trip_id, c.c.name)
        .join(c, t.c.category_id == c.c.id)
        .where(t.c.user_id == owner, t.c.deleted_at.is_(None), t.c.type.in_(("expense", "income")))
        .order_by(t.c.transaction_date.desc(), t.c.created_at.desc()).limit(RECENT_LIMIT)
    ).all()
    if not rows:
        return info_card("最近紀錄", [("尚無紀錄", "—")])
    lines = []
    for day, title, kind, amount, currency, trip_id, category in rows:
        sign = "-" if kind == "expense" else "+"
        label = f"{day:%m/%d} {title}" + ("（旅行）" if trip_id else "")
        lines.append((label, f"{sign}{currency} {money(amount)}"))
    return info_card("最近紀錄", lines)


def query_card(session, owner, command):
    return {"today": today_card, "month": month_card, "balances": balances_card,
            "recent": recent_card}[QUERY_COMMANDS[command]](session, owner)


def repeat_choices(session, owner, limit=MAX_REPEATS):
    """The person's own most repeated daily entries; each one points at its newest transaction."""
    t = transactions_table
    since = today() - timedelta(days=REPEAT_WINDOW_DAYS)
    group = (t.c.title, t.c.original_amount, t.c.original_currency, t.c.type, t.c.account_id)
    rows = session.execute(
        select(func.count().label("uses"), func.max(t.c.created_at).label("last"),
               *group)
        .where(*_own_daily(owner), t.c.transaction_date >= since, t.c.account_id.is_not(None))
        .group_by(*group).order_by(func.count().desc(), func.max(t.c.created_at).desc()).limit(limit)
    ).all()
    choices = []
    for row in rows:
        newest = session.execute(
            select(t.c.id).where(*_own_daily(owner), t.c.title == row.title,
                                 t.c.original_amount == row.original_amount, t.c.account_id == row.account_id,
                                 t.c.type == row.type, t.c.original_currency == row.original_currency)
            .order_by(t.c.created_at.desc()).limit(1)
        ).scalar()
        label = f"{row.title} {money(row.original_amount)}"[:20]
        choices.append({"transaction_id": str(newest), "label": label})
    return choices


def quick_replies(session, owner):
    items = [QuickReplyItem(action=MessageAction(label=label, text=label)) for label in QUERY_COMMANDS]
    for choice in repeat_choices(session, owner):
        items.append(QuickReplyItem(action=PostbackAction(
            label=choice["label"], data=f"nomica.oral.again:{choice['transaction_id']}",
            display_text=choice["label"])))
    return QuickReply(items=items[:13])


def attach(message, quick_reply):
    if getattr(message, "alt_text", None) in DRAFT_CARD_ALT_TEXTS:
        return message  # Never put shortcut chips next to a confirm button.
    message.quick_reply = quick_reply
    return message


def category_choices(session, owner, kind, limit=12):
    c = categories_table
    return session.execute(
        select(c.c.id, c.c.name).where(
            c.c.deleted_at.is_(None), c.c.is_active.is_(True), c.c.scope == "transaction",
            c.c.kind.in_([kind, "both"]), or_(c.c.user_id.is_(None), c.c.user_id == owner),
        ).order_by(c.c.sort_order, c.c.name).limit(limit)
    ).all()


def account_label(session, account_id):
    a = accounts_table
    return session.execute(select(a.c.name, a.c.type).where(a.c.id == account_id)).first()
