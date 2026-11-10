"""Read-only LINE cards (today, month, balances, recent) and one-tap repeats of recent entries.

Nothing here writes money: the cards only read the signed-in person's own rows, and a repeat only
prepares the same preview-and-confirm draft that typing a sentence would.
"""
import os
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
GUIDE_ALT_TEXT = "Nomica 使用說明"
ENTRY_COMMAND = "記一筆"


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


def _tap(label, text=None):
    return {"type": "button", "height": "sm", "style": "secondary",
            "action": {"type": "message", "label": label, "text": text or label}}


def guide_card(*, linked=True):
    """What to type, what to tap, and what AI needs: sent on follow and for 「幫助」."""
    section = lambda text: {"type": "text", "text": text, "weight": "bold", "size": "sm", "margin": "lg"}  # noqa: E731
    note = lambda text: {"type": "text", "text": text, "size": "xs", "color": "#666666", "wrap": True, "margin": "sm"}  # noqa: E731
    body = [{"type": "text", "text": "Nomica 怎麼用", "weight": "bold", "size": "lg"}]
    if not linked:
        body.append(note("先用同一個 LINE 帳號登入 Nomica Web，之後就能在這裡記帳。"))
    body += [
        section("1. 說一句話記帳"),
        note("像聊天一樣輸入，確認後才會記帳。點下面的範例可以直接試試："),
        _tap("午餐 120"),
        _tap("昨天晚餐 刷卡 450"),
        section("2. 少打字"),
        note("每次回覆下方會有快速按鈕：點最近常記的項目，會直接產生確認卡。確認卡上可按「改分類」，或回「改金額 150」。"),
        section("3. 看摘要"),
        {"type": "box", "layout": "horizontal", "spacing": "sm", "margin": "sm",
         "contents": [_tap("今天"), _tap("本月")]},
        {"type": "box", "layout": "horizontal", "spacing": "sm", "margin": "sm",
         "contents": [_tap("餘額"), _tap("最近")]},
        section("4. AI 輔助（選用）"),
        note("規則看不懂的句子可交給 AI。第一次會說明資料如何處理，回「同意 AI」才會開啟，回「撤回 AI」可隨時關閉。"),
        note("旅行分帳、報表與帳戶管理請到 Nomica Web。"),
    ]
    contents = {"type": "bubble", "body": {"type": "box", "layout": "vertical", "paddingAll": "20px",
                                          "contents": body}}
    web = (os.environ.get("FRONTEND_BASE_URL") or "").rstrip("/")
    if web.startswith("https://"):
        contents["footer"] = {"type": "box", "layout": "vertical", "contents": [{
            "type": "button", "style": "primary", "height": "sm",
            "action": {"type": "uri", "label": "開啟 Nomica Web", "uri": web}}]}
    return FlexSendMessage(alt_text=GUIDE_ALT_TEXT, contents=contents)


def entry_prompt_card():
    """Answer to the rich-menu 「記一筆」: how to record without leaving LINE."""
    return info_card(
        "說一句話就能記帳",
        [("例如", "午餐 120"), ("", "昨天晚餐 刷卡 450"), ("", "計程車 280 現金")],
        "直接輸入就好。核對確認卡後按確認才會記帳；點下方最近常記的項目可以一鍵重記。",
    )
