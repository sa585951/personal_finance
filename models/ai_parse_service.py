import re
from copy import deepcopy
from decimal import Decimal, InvalidOperation

from .linebot.parsers import GeminiParser, QuickParser


TRANSACTION_TYPES = {"expense", "income"}
DISABLED_GOAL_TYPES = {
    "goal_query",
    "manage_goal",
    "goal_progress",
    "start_add_goal",
    "start_edit_goal",
    "start_delete_goal",
}


class AIParseService:
    """跨入口共用的語意解析服務。

    現階段先沿用 LINE Bot 既有 QuickParser / GeminiParser，並額外整理出
    Web / PWA / iOS 未來可共用的 normalized result。
    """

    def __init__(self, gemini_model, prompt_template, quick_parser=None, gemini_parser=None):
        self.quick_parser = quick_parser or QuickParser()
        self.gemini_parser = gemini_parser or GeminiParser(
            model=gemini_model,
            prompt_template=prompt_template,
        )

    def parse(self, message):
        """解析使用者輸入，回傳跨平台可共用的 normalized result。"""
        raw_text = (message or "").strip()
        legacy_result, parser_source = self._parse_legacy(raw_text)

        return {
            "intent": self._detect_intent(legacy_result),
            "source": parser_source,
            "raw_text": raw_text,
            "legacy": deepcopy(legacy_result),
            "transaction": self._normalize_transaction(legacy_result, raw_text),
            "flow": self._normalize_flow(legacy_result),
            "missing_fields": self._detect_missing_fields(legacy_result),
            "errors": self._normalize_errors(legacy_result),
        }

    def parse_legacy(self, message):
        """相容既有 LINE MessageHandler 的解析格式。"""
        return self.parse(message)["legacy"]

    def _parse_legacy(self, message):
        quick_result = self.quick_parser.parse(message)
        if quick_result:
            return quick_result, "quick"

        gemini_result = self.gemini_parser.parse(message)
        fallback_result = self._parse_local_fallback(message, gemini_result)
        if fallback_result:
            return fallback_result, "local_fallback"

        return gemini_result, "gemini"

    def _parse_local_fallback(self, message, gemini_result):
        """Gemini 失敗時的本地規則 fallback，供本地開發與基本輸入測試使用。"""
        if gemini_result.get("type") != "other" or not gemini_result.get("error"):
            return None

        amount = self._extract_amount(message)
        if amount is None:
            return None

        transaction_type = self._detect_transaction_type(message)
        budget_category, category = self._detect_category(message, transaction_type)
        local_title = self._detect_local_title(message, category)

        return {
            "type": transaction_type,
            "budget_category": budget_category,
            "category": local_title,
            "description": "",
            "amount": amount,
            "currency": self._detect_currency(message),
            "target_asset": self._detect_account_hint(message),
            "fallback_reason": "gemini_error",
        }

    def _extract_amount(self, message):
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|塊|圓|twd|ntd)?", message, re.IGNORECASE)
        if not match:
            return None
        amount = Decimal(match.group(1))
        if amount <= 0:
            return None
        return float(amount) if amount % 1 else int(amount)

    def _detect_transaction_type(self, message):
        income_keywords = ["收入", "薪水", "薪資", "發薪", "獎金", "報銷", "補貼", "利息"]
        if any(keyword in message for keyword in income_keywords):
            return "income"
        return "expense"

    def _detect_category(self, message, transaction_type):
        if transaction_type == "income":
            income_category_keywords = [
                ("薪資", ["薪水", "薪資", "發薪"]),
                ("獎金", ["獎金"]),
                ("利息", ["利息"]),
                ("報銷/補貼", ["報銷", "補貼"]),
                ("禮金/贈與", ["禮金", "贈與", "紅包"]),
            ]
            for category, keywords in income_category_keywords:
                if any(keyword in message for keyword in keywords):
                    return category, category
            return "其他收入", "收入"

        expense_category_keywords = [
            ("伙食", "早餐", ["早餐", "早午餐"]),
            ("伙食", "午餐", ["午餐"]),
            ("伙食", "晚餐", ["晚餐"]),
            ("伙食", "飲料", ["飲料", "咖啡", "手搖", "可樂"]),
            ("伙食", "餐飲", ["麥當勞", "便當", "餐", "吃", "7-11", "全家"]),
            ("交通", "交通", ["捷運", "公車", "計程車", "高鐵", "台鐵", "停車", "加油"]),
            ("購物", "購物", ["購物", "衣服", "鞋", "包", "網購"]),
            ("娛樂", "娛樂", ["電影", "遊戲", "唱歌", "娛樂"]),
            ("醫療", "醫療", ["醫院", "診所", "看醫生", "藥"]),
            ("訂閱", "訂閱", ["訂閱", "月費", "年費"]),
            ("手續費", "手續費", ["手續費", "匯費"]),
        ]
        for budget_category, category, keywords in expense_category_keywords:
            if any(keyword in message for keyword in keywords):
                return budget_category, category
        return "其他", "記帳"

    def _detect_account_hint(self, message):
        account_keywords = ["現金", "信用卡", "刷卡", "銀行", "郵局", "LINE Pay", "街口", "悠遊卡"]
        for keyword in account_keywords:
            if keyword.lower() in message.lower():
                return "信用卡" if keyword == "刷卡" else keyword
        return None

    def _detect_currency(self, message):
        currency_keywords = [
            ("JPY", ["jpy", "日幣", "日圓", "日元", "円"]),
            ("TWD", ["twd", "ntd", "台幣", "新台幣", "臺幣", "元"]),
            ("USD", ["usd", "美金", "美元"]),
            ("EUR", ["eur", "歐元"]),
            ("KRW", ["krw", "韓元", "韓幣"]),
        ]
        lowered_message = message.lower()
        for currency, keywords in currency_keywords:
            if any(keyword in lowered_message for keyword in keywords):
                return currency
        return None

    def _clean_local_description(self, message):
        description = re.sub(r"\d+(?:\.\d+)?\s*(?:元|塊|圓|twd|ntd)?", "", message, flags=re.IGNORECASE)
        description = re.sub(r"(用|使用|付|付款|刷卡|現金|信用卡|銀行|郵局|LINE Pay|街口|悠遊卡)", "", description)
        description = re.sub(r"[，,。．\s]+", " ", description).strip()
        return description

    def _detect_local_title(self, message, fallback_category):
        title = self._clean_local_description(message)
        if title:
            return title
        return fallback_category

    def _detect_intent(self, legacy_result):
        result_type = legacy_result.get("type")
        if result_type in TRANSACTION_TYPES:
            return "create_transaction"
        if result_type == "query":
            return "query_transactions"
        if result_type == "asset_query":
            return "query_assets"
        if result_type in DISABLED_GOAL_TYPES:
            return "other"
        if result_type and result_type.startswith("start_"):
            return "start_flow"
        return "other"

    def _normalize_transaction(self, legacy_result, raw_text):
        transaction_type = legacy_result.get("type")
        if transaction_type not in TRANSACTION_TYPES:
            return None

        title = legacy_result.get("category")
        if not title:
            title = "收入" if transaction_type == "income" else "記帳"

        budget_category = legacy_result.get("budget_category")
        if not budget_category:
            budget_category = "收入" if transaction_type == "income" else "其他"

        description = self._normalize_description(
            legacy_result.get("description"), raw_text, title
        )

        return {
            "type": transaction_type,
            "title": title,
            "budget_category": budget_category,
            "amount": self._normalize_amount(legacy_result.get("amount")),
            "description": description,
            "account_hint": legacy_result.get("target_asset"),
            "currency": legacy_result.get("currency"),
            "date": legacy_result.get("date"),
            "merchant": legacy_result.get("merchant"),
        }

    def _normalize_description(self, description, raw_text, title=None):
        if description is None:
            return ""

        normalized = str(description).strip()
        if not normalized:
            return ""

        if normalized in {"支出", "收入", "記帳"}:
            return ""

        if normalized == str(raw_text).strip():
            return ""

        if title is not None and normalized == str(title).strip():
            return ""

        return normalized

    def _normalize_flow(self, legacy_result):
        result_type = legacy_result.get("type")
        if result_type in DISABLED_GOAL_TYPES:
            return None
        if not result_type or not result_type.startswith("start_"):
            return None

        return {
            "name": result_type.removeprefix("start_"),
            "payload": {
                key: value
                for key, value in legacy_result.items()
                if key != "type"
            },
        }

    def _detect_missing_fields(self, legacy_result):
        if legacy_result.get("type") not in TRANSACTION_TYPES:
            return []

        missing_fields = []
        if self._normalize_amount(legacy_result.get("amount")) is None:
            missing_fields.append("amount")
        if not legacy_result.get("category"):
            missing_fields.append("title")
        if not legacy_result.get("budget_category"):
            missing_fields.append("budget_category")
        return missing_fields

    def _normalize_errors(self, legacy_result):
        error = legacy_result.get("error")
        if not error:
            return []
        return [str(error)]

    def _normalize_amount(self, value):
        if value is None:
            return None
        try:
            return str(Decimal(str(value)))
        except (InvalidOperation, ValueError):
            return None
