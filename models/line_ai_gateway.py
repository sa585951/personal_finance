"""Budget, consent and the only outbound Gemini path for LINE bookkeeping."""
import logging
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
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
    """Carries a fixed, safe reply instead of a provider exception."""

    def __init__(self, message, code="blocked"):
        super().__init__(message)
        self.code = code


# One shared notice for the Web, where there is no chat to reply "同意 AI" in.
WEB_CONSENT_NOTICE = (
    "規則無法處理的記帳文字會傳給 Google Gemini 解析，請勿輸入卡號、密碼或其他敏感資料。"
    "Google 依付費服務條款處理，可能短期保留資料供安全監控。AI 只產生草稿，確認後才會入帳。"
    "你隨時可以在「我的」撤回，LINE 與網頁共用同一份同意。"
)

# AI calls in flight per process: the provider call holds a worker for seconds.
MAX_CONCURRENT_CALLS = 4


class _InFlight:
    """Non-blocking caps: a few calls overall and one at a time per person."""

    def __init__(self, limit):
        self._slots = threading.BoundedSemaphore(limit)
        self._owners = set()
        self._lock = threading.Lock()

    def acquire(self, owner):
        with self._lock:
            if owner in self._owners:
                raise AIRequestBlocked("上一個 AI 解析還在處理中，請稍候。", "busy")
            if not self._slots.acquire(blocking=False):
                raise AIRequestBlocked("現在使用 AI 的人較多，請稍後再試，或直接輸入金額記帳。", "busy")
            self._owners.add(owner)

    def release(self, owner):
        with self._lock:
            if owner in self._owners:
                self._owners.discard(owner)
                self._slots.release()


# Applies when NOMICA_LINE_AI_MONTHLY_USD is unset; set "0" to turn LINE AI off.
DEFAULT_MONTHLY_USD = Decimal("5")
# Per-person AI requests per Taipei calendar day; keeps one account from using up
# the shared monthly budget. Rule-based entries never reach the gateway.
DEFAULT_DAILY_PER_USER = 20
ALERT_RATIO = Decimal("0.8")
LOCAL_TZ = ZoneInfo("Asia/Taipei")
# Attempts that never reached the provider do not count toward the daily cap.
UNSENT_STATUSES = ("rejected",)


def read_line_ai_budget(env):
    raw = (env.get("NOMICA_LINE_AI_MONTHLY_USD") or "").strip()
    if not raw:
        return DEFAULT_MONTHLY_USD
    try:
        value = Decimal(raw)
    except InvalidOperation:
        # A typo must never lift the cap: fail closed.
        return None
    return value if value.is_finite() and 0 < value <= 1_000_000 else None


def read_line_ai_daily_limit(env):
    raw = (env.get("NOMICA_LINE_AI_DAILY_PER_USER") or "").strip()
    if not raw:
        return DEFAULT_DAILY_PER_USER
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if 0 < value <= 10_000 else None


def set_line_ai_consent(session, owner, consented):
    values = dict(version=CONSENT_VERSION, consented=consented, updated_at=func.now())
    session.execute(insert(line_ai_consents).values(user_id=UUID(str(owner)), **values)
                    .on_conflict_do_update(index_elements=[line_ai_consents.c.user_id], set_=values))


def _valid_token_count(value):
    return type(value) is int and value >= 0


class LineAIGateway:
    def __init__(self, sessions, models, budget, *, daily_limit=DEFAULT_DAILY_PER_USER, notify=None):
        self.sessions = sessions
        self.models = models
        self.budget = budget
        self.daily_limit = daily_limit
        # Best-effort admin notice; called after the reservation commits.
        self.notify = notify
        self.in_flight = _InFlight(MAX_CONCURRENT_CALLS)

    def status(self, owner):
        """Consent and today's remaining AI requests for one person."""
        owner = UUID(str(owner))
        local_midnight = datetime.now(timezone.utc).astimezone(LOCAL_TZ).replace(
            hour=0, minute=0, second=0, microsecond=0)
        with self.sessions.begin() as session:
            consented = bool(session.scalar(select(line_ai_consents.c.consented).where(
                line_ai_consents.c.user_id == owner, line_ai_consents.c.version == CONSENT_VERSION)))
            enabled = bool(session.scalar(select(line_ai_control.c.enabled).where(line_ai_control.c.id == 1)))
            used = session.scalar(select(func.count()).select_from(line_ai_attempts).where(
                line_ai_attempts.c.user_id == owner, line_ai_attempts.c.created_at >= local_midnight,
                line_ai_attempts.c.status.not_in(UNSENT_STATUSES))) or 0
        return {"enabled": enabled, "consented": consented,
                "remaining": max(0, self.daily_limit - used), "daily_limit": self.daily_limit}

    def _check_consent(self, session, owner, *, lock=False):
        query = select(line_ai_consents.c.consented).where(
            line_ai_consents.c.user_id == owner, line_ai_consents.c.version == CONSENT_VERSION,
        )
        consent = session.scalar(query.with_for_update(read=True) if lock else query)
        if not consent:
            raise AIRequestBlocked(CONSENT_NOTICE, "consent_required")

    def _check_switch(self, session, *, lock=False):
        query = select(line_ai_control.c.enabled).where(line_ai_control.c.id == 1)
        if not session.scalar(query.with_for_update() if lock else query):
            raise AIRequestBlocked("AI 解析目前暫停。可用「午餐 120」或到 Nomica Web 記帳。", "paused")

    def _reserve(self, owner, event_id):
        now = datetime.now(timezone.utc)
        month = now.date().replace(day=1)
        local_midnight = now.astimezone(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        attempts = line_ai_attempts
        alert = None
        with self.sessions.begin() as session:
            # One shared row serializes reservations across workers. Release it before I/O.
            self._check_switch(session, lock=True)
            self._check_consent(session, owner)
            if session.scalar(select(attempts.c.event_id).where(attempts.c.event_id == event_id)):
                raise AIRequestBlocked("這則 AI 記帳已受理。請查看先前回覆，或另傳一則訊息。")
            today = session.scalar(select(func.count()).select_from(attempts).where(
                attempts.c.user_id == owner, attempts.c.created_at >= local_midnight,
                attempts.c.status.not_in(UNSENT_STATUSES),
            ))
            if today >= self.daily_limit:
                raise AIRequestBlocked("今天的 AI 解析次數已用完，明天恢復。可先用「午餐 120」或到 Nomica Web 記帳。", "daily_limit")
            recent = select(attempts.c.event_id).where(
                attempts.c.user_id == owner, attempts.c.created_at > now - timedelta(seconds=5),
            ).limit(1)
            if session.scalar(recent):
                raise AIRequestBlocked("AI 解析請間隔幾秒再試，也可以用「午餐 120」記帳。", "too_fast")
            used = session.scalar(select(func.coalesce(func.sum(attempts.c.charge_usd), 0))
                                  .where(attempts.c.month == month))
            if used + RESERVE > self.budget:
                raise AIRequestBlocked("AI 解析已達本月費用上限。可用「午餐 120」或到 Nomica Web 記帳。", "budget")
            session.execute(insert(attempts).values(
                event_id=event_id, user_id=owner, month=month, model=MODEL,
                created_at=now, status="reserved", charge_usd=RESERVE,
            ))
            projected = used + RESERVE
            if projected >= self.budget * ALERT_RATIO:
                # The control row is locked above, so only one worker records this month's alert.
                sent_for = session.scalar(select(line_ai_control.c.alert_month).where(line_ai_control.c.id == 1))
                if sent_for != month:
                    session.execute(update(line_ai_control).where(line_ai_control.c.id == 1)
                                    .values(alert_month=month))
                    alert = (f"Nomica LINE AI 本月用量已達 {projected / self.budget:.0%}"
                             f"（約 {projected:.4f} / {self.budget} USD）。到上限後會自動改用規則記帳。")
        if alert and self.notify:
            try:
                self.notify(alert)
            except Exception:
                logging.getLogger(__name__).warning("LINE AI budget alert failed")

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
        # Checked before reserving, so a refused call is never counted against the daily cap.
        self.in_flight.acquire(owner)
        try:
            return self._generate(owner, event_id, prompt)
        finally:
            self.in_flight.release(owner)

    def _generate(self, owner, event_id, prompt):
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
