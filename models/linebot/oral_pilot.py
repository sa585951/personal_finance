"""LINE pilot for natural-language drafts and explicit account selection."""
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from unicodedata import normalize
from uuid import UUID

from sqlalchemy import and_, func, select, update

from ..asset_manager import ACCOUNT_TYPE_LABELS
from ..budget_manager import DEFAULT_CURRENCY
from ..line_ai_gateway import AIRequestBlocked, CONSENT_NOTICE, set_line_ai_consent
from ..schema import accounts_table, ai_parse_events_table, categories_table, transactions_table
from ..user_manager import UserManager
from .line_sdk import FlexSendMessage
from .transaction_drafts import LineTransactionDrafts


MEAL = re.compile(r"(早餐|午餐|晚餐)\s+(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:元|塊)?(?:\s+(現金|cash))?")
AMOUNT_TEXT = re.compile(r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?")
AMBIGUOUS_DATE = re.compile(
    r"(?:上|下|這|本)(?:個)?(?:週|周|禮拜|星期|月)|(?:週|周|禮拜|星期)[一二三四五六日天]"
    r"|大前天|明天|後天|月初|月中|月底|週末|周末|日前|最近|前[幾几]天|[0-9]+天前"
)
DATE_CUE = re.compile(
    r"前天|昨天|昨晚|昨日|今天|今日|剛剛"
    r"|(?<![0-9])20[0-9]{2}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}(?:日|號)?"
    r"|(?<![0-9])[0-9]{1,2}\s*[/月-]\s*[0-9]{1,2}(?:日|號)?"
)
STORE_NAME = re.compile(r"(?<![0-9/-])7-11(?![0-9/-])(?=\s*(?:買|消費|超商|門市))|(?<=在)7-11(?![0-9/-])")
EXPLICIT_CURRENCIES = {
    "TWD": re.compile(r"(?<![A-Za-z])(?:TWD|NTD)(?![A-Za-z])|新?[台臺]幣|NT\$", re.I | re.ASCII),
    "JPY": re.compile(r"(?<![A-Za-z])JPY(?![A-Za-z])|日幣|日圓|日元|円", re.I | re.ASCII),
    "USD": re.compile(r"(?<![A-Za-z])USD(?![A-Za-z])|美金|美元|US\$", re.I | re.ASCII),
    "EUR": re.compile(r"(?<![A-Za-z])EUR(?![A-Za-z])|歐元|€", re.I | re.ASCII),
    "KRW": re.compile(r"(?<![A-Za-z])KRW(?![A-Za-z])|韓元|韓幣|₩", re.I | re.ASCII),
}
SENSITIVE_TEXT = re.compile(
    r"密碼|驗證碼|身分證|身份證|卡號|(?i:\b(?:cvv|cvc|otp|password|api[ -]?key)\b)"
    r"|(?<!\d)(?:\d[ -]?){13,19}(?!\d)"
)
BOOKKEEPING_TEXT = re.compile(
    r"(?:[0-9]|[一二兩三四五六七八九十百千萬]+[十百千萬元塊])"
)
GUIDE = "可傳「昨天午餐刷卡 120」或「午餐 120」。請核對草稿後確認，其他操作請到 Nomica Web。"
NO_DRAFT = "找不到可操作的收支草稿，請重新輸入。"
ACCOUNT_PAGE_SIZE = 8
USAGE_WINDOW_DAYS = 90


def parse_oral(parser, message, *, generate=None):
    """Use local rules only for a complete, unambiguous pattern."""
    text = normalize("NFKC", message).strip()
    quick = MEAL.fullmatch(text)
    if quick:
        item, amount, account = quick.groups()
        return {"type": "expense", "category": item, "budget_category": "伙食",
                "amount": amount.replace(",", ""), "target_asset": account}, "rule"
    parsed = parser.parse(text, generate=generate)
    if parsed["source"] == "local_fallback":
        return {}, "unavailable"
    return parsed["legacy"], parsed["source"]


def oral_payload(parser, message, parsed, validate_amount):
    text = normalize("NFKC", message)
    # Keep a store name from being mistaken for a date or amount.
    text = STORE_NAME.sub("超商", text)
    without_date = parser._remove_date_phrase(text)
    numbers = re.findall(r"(?<![\d.])-?\d+(?:,\d{3})*(?:\.\d+)?(?![\d.])", without_date)
    amount = None
    if (len(numbers) == 1 and AMOUNT_TEXT.fullmatch(numbers[0])
            and not re.search(r"[-−負]\s*\d", without_date)):
        candidate = validate_amount(numbers[0].replace(",", ""))
        if candidate == validate_amount(parsed.get("amount")):
            amount = candidate
    day = parser._extract_transaction_date(text)
    if AMBIGUOUS_DATE.search(text) or len(DATE_CUE.findall(text)) > 1:
        day = None
    elif not day and without_date == text:
        today = parser._today().isoformat()
        if parsed.get("date") in (None, "", today):
            day = today
    explicit = {currency for currency, pattern in EXPLICIT_CURRENCIES.items() if pattern.search(text)}
    currency = parsed.get("currency")
    if explicit and (len(explicit) != 1 or currency and currency not in explicit):
        currency = None
    else:
        currency = currency or next(iter(explicit), DEFAULT_CURRENCY)
    return dict(date=day, item=parsed.get("category") or "記帳", amount=amount,
                type=parsed["type"], budget_category=parsed.get("budget_category") or
                ("收入" if parsed["type"] == "income" else "其他"),
                description=parsed.get("description") or "", original_currency=currency)


class LineOralPilot:
    def __init__(self, session, parser, gateway=None):
        self.session = session
        self.parser = parser
        self.gateway = gateway
        self.drafts = LineTransactionDrafts(session)

    def handle(self, event):
        message = getattr(event, "message", None)
        text = message.text.strip() if message else ""
        if text == "幫助":
            return GUIDE
        user = UserManager(self.session).get_user_by_identity("line", event.source.user_id)
        if not user:
            return "請先用你目前傳訊息的 LINE 帳號登入 Nomica Web。"
        owner = user["id"]
        if not message:
            return self._postback(owner, event.postback.data)
        command = " ".join(text.upper().split())
        if command == "AI 說明":
            return CONSENT_NOTICE if self.gateway else "AI 解析目前暫停。"
        if command == "撤回 AI":
            set_line_ai_consent(self.session, owner, False)
            return ("已撤回 AI 同意。系統會停止授權新的請求，已獲准處理的請求可能仍會送出。"
                    "規則記帳和既有草稿仍可使用。")
        if command == "同意 AI":
            if not self.gateway:
                return "AI 解析目前暫停。"
            set_line_ai_consent(self.session, owner, True)
            return ("已開啟 AI 口語記帳。規則無法處理的記帳文字會傳給 Google Gemini。"
                    "請再傳一筆記帳文字，隨時可回「撤回 AI」。")
        if text.startswith(("補金額 ", "補日期 ")):
            return self._clarify(owner, text)
        chosen = self._choose_account_by_name(owner, text)
        if chosen is not None:
            return chosen
        if len(text) > 1000:
            return "訊息太長，請簡短描述一筆收支。"
        try:
            if self.gateway:
                def generate(prompt):
                    normalized = normalize("NFKC", text)
                    if SENSITIVE_TEXT.search(normalized):
                        raise AIRequestBlocked("請移除卡號、密碼或驗證資訊，再傳送記帳文字。")
                    if not (BOOKKEEPING_TEXT.search(normalized) and re.search(r"[一-鿿a-zA-Z]", normalized)):
                        raise AIRequestBlocked(GUIDE)
                    return self.gateway.generate(owner, event.webhook_event_id, prompt)
                parsed, _ = parse_oral(self.parser, text, generate=generate)
            else:
                parsed, _ = parse_oral(self.parser, text)
        except AIRequestBlocked as blocked:
            return str(blocked)
        if parsed.get("type") not in {"expense", "income"}:
            return GUIDE

        payload = oral_payload(self.parser, text, parsed, self._amount)
        budget = self.drafts.service.budget_manager
        try:
            rate = budget._default_exchange_rate(payload["original_currency"], DEFAULT_CURRENCY)
        except ValueError:
            return "無法確認幣別或取得適用匯率，請到 Nomica Web 記帳。"
        if payload["original_currency"] != DEFAULT_CURRENCY:
            payload["exchange_rate"] = str(rate)
        category_id = budget._get_category_id(owner, payload["budget_category"], payload["type"])
        payload["budget_category"] = self.session.scalar(
            select(categories_table.c.name).where(categories_table.c.id == category_id)
        )
        # An invented model hint must never select a real account.
        hint = parsed.get("target_asset")
        if hint:
            normalized_hint = normalize("NFKC", hint)
            normalized_text = normalize("NFKC", text)
            alias = self._card_alias(normalized_hint)
            if normalized_hint not in normalized_text and not (alias and f"{alias}卡" in normalized_text):
                hint = None
        record = self.drafts.events.record_parse_event(owner, "line_bot", "", {
            "line_oral": True, "line_draft": payload,
            "account_hint": hint, "offered_accounts": [], "category_id": str(category_id),
        }, "success", result_type=parsed["type"])
        return self._advance(owner, record)

    def _amount(self, value):
        try:
            return format(self.drafts.service.budget_manager._normalize_amount(value), "f")
        except ValueError:
            return None

    def _accounts(self, owner, currency):
        """Same-currency accounts, most useful first: last used, then most used in 90 days."""
        table, tx = accounts_table, transactions_table
        since = date.today() - timedelta(days=USAGE_WINDOW_DAYS)
        usage = select(
            tx.c.account_id,
            func.max(tx.c.created_at).label("last_used"),
            func.count().filter(tx.c.transaction_date >= since).label("recent_uses"),
        ).where(tx.c.user_id == owner, tx.c.deleted_at.is_(None), tx.c.account_id.is_not(None)
                ).group_by(tx.c.account_id).subquery()
        rows = self.session.execute(
            select(table.c.id, table.c.name, table.c.type, usage.c.last_used, usage.c.recent_uses)
            .select_from(table.outerjoin(usage, usage.c.account_id == table.c.id))
            .where(
                table.c.user_id == owner, table.c.deleted_at.is_(None),
                table.c.is_active.is_(True), table.c.track_balance.is_(True), table.c.currency == currency,
            ).order_by(table.c.name, table.c.id)
        ).mappings().all()
        used = [row for row in rows if row["last_used"] is not None]
        latest = max(used, key=lambda row: row["last_used"])["id"] if used else None
        ordered = sorted(rows, key=lambda row: (row["id"] != latest, -(row["recent_uses"] or 0)))
        return [{"id": row["id"], "name": row["name"], "type": row["type"]} for row in ordered]

    def _save(self, row, data):
        self.session.execute(update(ai_parse_events_table).where(ai_parse_events_table.c.id == row["id"])
                             .values(parsed_payload=data))

    def _advance(self, owner, row):
        data = row["parsed_payload"]
        payload = data["line_draft"]
        if payload["amount"] is None:
            return "請補金額，例如「補金額 120」。"
        if payload["date"] is None:
            return f"請補日期，例如「補日期 {self.parser._today().isoformat()}」。"
        accounts = self._accounts(owner, payload["original_currency"])
        if not accounts:
            return "找不到符合幣別的本人帳戶，請到 Nomica Web 檢查帳戶。"
        hint = data.get("account_hint")
        if hint:
            exact = [account for account in accounts if account["name"] == hint]
            if len(exact) == 1:
                return self._freeze_account(row, exact[0])
            if not exact:
                alias = self._card_alias(hint)
                matches = [account for account in accounts if account["type"] == "credit_card"
                           and alias and self._card_alias(account["name"]) == alias]
                if len(matches) == 1:
                    return self._freeze_account(row, matches[0])
        return self._account_menu(row, accounts, page=0)

    @staticmethod
    def _menu_options(accounts):
        labels = Counter(account["name"][:20] for account in accounts)
        options = []
        for account in accounts:
            label = account["name"][:20]
            if labels[label] > 1:
                suffix = f"（{ACCOUNT_TYPE_LABELS[account['type']]}）"
                label = account["name"][:20 - len(suffix)] + suffix
            options.append((account, label))
        label_counts = Counter(label for _, label in options)
        return [(account, label) for account, label in options if label_counts[label] == 1]

    def _account_menu(self, row, accounts, page):
        options = self._menu_options(accounts)
        if not options:
            return "無法在 LINE 區分同名帳戶，請到 Nomica Web 記帳。"
        pages = (len(options) + ACCOUNT_PAGE_SIZE - 1) // ACCOUNT_PAGE_SIZE
        page = min(max(page, 0), pages - 1)
        offered = options[page * ACCOUNT_PAGE_SIZE:(page + 1) * ACCOUNT_PAGE_SIZE]
        data = row["parsed_payload"]
        # Keep earlier pages valid: every account ever shown on this draft stays selectable.
        known = list(data.get("offered_accounts") or [])
        known += [str(account["id"]) for account, _ in offered if str(account["id"]) not in known]
        data["offered_accounts"] = known
        self._save(row, data)
        buttons = [{
            "type": "button", "action": {"type": "postback", "label": label,
                "data": f"nomica.oral.account:{row['id']}:{account['id']}"},
        } for account, label in offered]
        if pages > 1:
            following = (page + 1) % pages
            buttons.append({
                "type": "button", "style": "secondary", "action": {
                    "type": "postback", "label": f"更多帳戶（{following + 1}/{pages}）",
                    "data": f"nomica.oral.more:{row['id']}:{following}"},
            })
        return FlexSendMessage(alt_text="選擇記帳帳戶", contents={
            "type": "bubble",
            "body": {"type": "box", "layout": "vertical", "contents": [{
                "type": "text", "text": "請選擇帳戶，或直接回覆帳戶名稱。", "wrap": True,
            }]},
            "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": buttons},
        })

    def _awaiting_account(self, owner):
        table = ai_parse_events_table
        rows = self.session.execute(self._pending(owner).where(
            table.c.parsed_payload["line_draft"]["account_id"].as_string().is_(None),
        ).limit(2)).mappings().all()
        rows = [row for row in rows if row["parsed_payload"].get("offered_accounts")]
        return rows[0] if len(rows) == 1 else None

    def _choose_account_by_name(self, owner, text):
        """A reply that names one of the person's accounts picks it for the waiting draft."""
        name = normalize("NFKC", text).strip()
        if not name or len(name) > 100:
            return None
        row = self._awaiting_account(owner)
        if not row:
            return None
        accounts = self._accounts(owner, row["parsed_payload"]["line_draft"]["original_currency"])
        exact = [account for account in accounts if normalize("NFKC", account["name"]) == name]
        if not exact:
            alias = self._card_alias(name)
            exact = [account for account in accounts if account["type"] == "credit_card"
                     and alias and self._card_alias(account["name"]) == alias]
        if len(exact) != 1:
            return None
        return self._freeze_account(row, exact[0])

    @staticmethod
    def _card_alias(name):
        match = re.fullmatch(r"(.+?)(?:信用卡|卡)", name)
        return match.group(1) if match else None

    def _freeze_account(self, row, account):
        data = row["parsed_payload"]
        payload = data["line_draft"]
        payload["account_id"] = str(account["id"])
        self._save(row, data)
        label = f"{account['name']}（{ACCOUNT_TYPE_LABELS[account['type']]}）"
        return self.drafts.preview(row["id"], payload, label)

    def _pending(self, owner):
        table = ai_parse_events_table
        return select(table).where(
            table.c.user_id == owner, table.c.source == "line_bot", table.c.status == "success",
            table.c.parsed_payload["line_oral"].as_boolean().is_(True),
            table.c.created_at >= datetime.now(timezone.utc) - self.drafts.ttl,
        ).with_for_update()

    def _clarify(self, owner, text):
        command, value = text.split(maxsplit=1)
        field = "amount" if command == "補金額" else "date"
        table = ai_parse_events_table
        rows = self.session.execute(self._pending(owner).where(
            table.c.parsed_payload["line_draft"][field].as_string().is_(None),
        ).limit(2)).mappings().all()
        if len(rows) != 1:
            return "找不到唯一待補資料的草稿，請重新傳一筆完整收支。"
        if field == "amount":
            value = normalize("NFKC", value)
            value = self._amount(value.replace(",", "")) if AMOUNT_TEXT.fullmatch(value) else None
        else:
            try:
                value = date.fromisoformat(value).isoformat()
            except ValueError:
                value = None
        if value is None:
            return "補充資料格式不正確，請再試一次。"
        row = rows[0]
        row["parsed_payload"]["line_draft"][field] = value
        self._save(row, row["parsed_payload"])
        return self._advance(owner, row)

    def _postback(self, owner, data):
        action, _, args = data.partition(":")
        if action in {"nomica.oral.confirm", "nomica.oral.cancel"}:
            return self.drafts.resolve(owner, args, action.rsplit(".", 1)[-1])
        if action not in {"nomica.oral.account", "nomica.oral.more"}:
            return None
        draft_id, _, account_id = args.partition(":")
        try:
            key = UUID(draft_id)
        except ValueError:
            return NO_DRAFT
        row = self.session.execute(self._pending(owner).where(ai_parse_events_table.c.id == key)).mappings().first()
        if not row:
            return NO_DRAFT
        saved = row["parsed_payload"]
        payload = saved["line_draft"]
        if payload.get("account_id"):
            return "已選定帳戶，請使用確認卡。"
        if action == "nomica.oral.more":
            try:
                page = int(account_id)
            except ValueError:
                return NO_DRAFT
            return self._account_menu(row, self._accounts(owner, payload["original_currency"]), page)
        if account_id in saved["offered_accounts"]:
            for account in self._accounts(owner, payload["original_currency"]):
                if str(account["id"]) == account_id:
                    return self._freeze_account(row, account)
        return "該帳戶已無法選用，請重新輸入。"
