"""Budget, consent and the only outbound Gemini path for LINE bookkeeping."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from google.genai import types
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from .schema import line_ai_attempts, line_ai_consents, line_ai_control


MODEL = "gemini-3.1-flash-lite"
CONSENT_VERSION = 1
INPUT_LIMIT = 4096
OUTPUT_LIMIT = 512
# Gemini Developer API standard text rates, in USD per token.
INPUT_RATE = Decimal("0.00000025")
OUTPUT_RATE = Decimal("0.00000150")
RESERVE = INPUT_LIMIT * INPUT_RATE + OUTPUT_LIMIT * OUTPUT_RATE
CONSENT_NOTICE = (
    "這句需要 AI。若同意，日後規則無法處理的記帳文字會自動傳給 Google Gemini 解析，"
    "請勿傳卡號、密碼或其他敏感資料。Google 依付費服務條款處理，可能短期保留資料供安全監控："
    " https://ai.google.dev/gemini-api/terms 。AI 只產生草稿。"
    "回「同意 AI」開啟，再重傳這句。回「撤回 AI」可停止授權新的請求。"
)


class AIRequestBlocked(Exception):
    """Carries a fixed, safe LINE reply instead of a provider exception."""


def read_line_ai_budget(env):
    try:
        value = Decimal(env.get("NOMICA_LINE_AI_MONTHLY_USD") or "0")
    except InvalidOperation:
        return None
    return value if value.is_finite() and 0 < value <= 1_000_000 else None


def set_line_ai_consent(session, owner, consented):
    values = dict(version=CONSENT_VERSION, consented=consented, updated_at=func.now())
    session.execute(insert(line_ai_consents).values(user_id=UUID(str(owner)), **values)
                    .on_conflict_do_update(index_elements=[line_ai_consents.c.user_id], set_=values))


def _valid_token_count(value):
    return type(value) is int and value >= 0


class LineAIGateway:
    def __init__(self, sessions, models, budget):
        self.sessions = sessions
        self.models = models
        self.budget = budget

    def _check_consent(self, session, owner, *, lock=False):
        query = select(line_ai_consents.c.consented).where(
            line_ai_consents.c.user_id == owner, line_ai_consents.c.version == CONSENT_VERSION,
        )
        consent = session.scalar(query.with_for_update(read=True) if lock else query)
        if not consent:
            raise AIRequestBlocked(CONSENT_NOTICE)

    def _check_switch(self, session, *, lock=False):
        query = select(line_ai_control.c.enabled).where(line_ai_control.c.id == 1)
        if not session.scalar(query.with_for_update() if lock else query):
            raise AIRequestBlocked("AI 解析目前暫停。可用「午餐 120」或到 Nomica Web 記帳。")

    def _reserve(self, owner, event_id):
        now = datetime.now(timezone.utc)
        month = now.date().replace(day=1)
        attempts = line_ai_attempts
        with self.sessions.begin() as session:
            # One shared row serializes reservations across workers. Release it before I/O.
            self._check_switch(session, lock=True)
            self._check_consent(session, owner)
            if session.scalar(select(attempts.c.event_id).where(attempts.c.event_id == event_id)):
                raise AIRequestBlocked("這則 AI 記帳已受理。請查看先前回覆，或另傳一則訊息。")
            recent = select(attempts.c.event_id).where(
                attempts.c.user_id == owner, attempts.c.created_at > now - timedelta(seconds=5),
            ).limit(1)
            if session.scalar(recent):
                raise AIRequestBlocked("AI 解析請間隔幾秒再試，也可以用「午餐 120」記帳。")
            used = session.scalar(select(func.coalesce(func.sum(attempts.c.charge_usd), 0))
                                  .where(attempts.c.month == month))
            if used + RESERVE > self.budget:
                raise AIRequestBlocked("AI 解析已達本月費用上限。可用「午餐 120」或到 Nomica Web 記帳。")
            session.execute(insert(attempts).values(
                event_id=event_id, user_id=owner, month=month, model=MODEL,
                created_at=now, status="reserved", charge_usd=RESERVE,
            ))

    def _authorize(self, owner, event_id, stage):
        with self.sessions.begin() as session:
            # Record each dispatch decision under the same locks used by stop and withdrawal.
            self._check_switch(session, lock=True)
            self._check_consent(session, owner, lock=True)
            session.execute(update(line_ai_attempts).where(line_ai_attempts.c.event_id == event_id)
                            .values(status=stage))

    def _authorize_or_release(self, owner, event_id, stage):
        try:
            self._authorize(owner, event_id, stage)
        except AIRequestBlocked:
            self._finish(event_id, "rejected", charge_usd=0)
            raise

    def _finish(self, event_id, status, **usage):
        with self.sessions.begin() as session:
            if status == "limit_exceeded":
                session.execute(update(line_ai_control).where(line_ai_control.c.id == 1).values(enabled=False))
            session.execute(update(line_ai_attempts).where(line_ai_attempts.c.event_id == event_id)
                            .values(status=status, **usage))

    def generate(self, owner, event_id, prompt):
        if len(prompt.encode("utf-8")) > 24_000:
            raise AIRequestBlocked("記帳文字太長，請縮短後再試。")
        owner = UUID(str(owner))
        self._reserve(owner, event_id)
        self._authorize_or_release(owner, event_id, "counting")
        try:
            counted = self.models.count_tokens(model=MODEL, contents=prompt).total_tokens
        except Exception:
            self._finish(event_id, "unknown")
            raise AIRequestBlocked("AI 解析暫時無法使用，請稍後再試。") from None
        if type(counted) is not int or not 0 < counted <= INPUT_LIMIT:
            self._finish(event_id, "rejected", charge_usd=0)
            raise AIRequestBlocked("記帳文字太長或無法計算 Token，請縮短後再試。")
        self._authorize_or_release(owner, event_id, "generating")
        try:
            response = self.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(
                    candidate_count=1, max_output_tokens=OUTPUT_LIMIT,
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                ),
            )
        except Exception:
            self._finish(event_id, "unknown")
            raise AIRequestBlocked("AI 解析暫時無法使用，請稍後再試。") from None
        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", None)
        output_tokens = getattr(usage, "candidates_token_count", None)
        thoughts = getattr(usage, "thoughts_token_count", None)
        total = getattr(usage, "total_token_count", None)
        billed_output = sum(n for n in (output_tokens, thoughts) if _valid_token_count(n))
        complete = (
            all(_valid_token_count(n) for n in (input_tokens, output_tokens, total))
            and (thoughts is None or _valid_token_count(thoughts))
            and input_tokens > 0 and total == input_tokens + billed_output
        )
        known_charge = (input_tokens if _valid_token_count(input_tokens) else 0) * INPUT_RATE + billed_output * OUTPUT_RATE
        if (_valid_token_count(input_tokens) and input_tokens > INPUT_LIMIT) or billed_output > OUTPUT_LIMIT:
            self._finish(event_id, "limit_exceeded",
                         input_tokens=input_tokens if _valid_token_count(input_tokens) else None, output_tokens=billed_output,
                         charge_usd=known_charge if complete else max(known_charge, RESERVE))
            raise AIRequestBlocked("AI 解析已暫停，請用「午餐 120」或到 Nomica Web 記帳。")
        if not complete:
            self._finish(event_id, "unknown")
            raise AIRequestBlocked("AI 解析暫時無法驗證用量，請稍後再試。")
        self._finish(event_id, "completed", input_tokens=input_tokens,
                     output_tokens=billed_output, charge_usd=known_charge)
        return response
