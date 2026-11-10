from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Event
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from models.line_ai_gateway import (
    LOCAL_TZ, RESERVE, AIRequestBlocked, LineAIGateway, read_line_ai_budget, read_line_ai_daily_limit,
    set_line_ai_consent,
)
from models.schema import line_ai_attempts, line_ai_control
from tests.test_line_durable_confirmation import command_db, line_db  # noqa: F401


class Provider:
    def __init__(self):
        self.calls = []
        self.count = 100
        self.text = "{}"
        self.usage = SimpleNamespace(prompt_token_count=100, candidates_token_count=50,
                                     thoughts_token_count=10, total_token_count=160)
        self.started = Event()
        self.release = Event()
        self.release.set()
        self.fail = False

    def count_tokens(self, *, model, contents):
        self.calls.append(("count", model))
        return SimpleNamespace(total_tokens=self.count)

    def generate_content(self, *, model, contents, config):
        self.calls.append(("generate", model))
        assert config.max_output_tokens == 512 and config.candidate_count == 1
        self.started.set()
        assert self.release.wait(5)
        if self.fail:
            raise TimeoutError("private provider exception")
        return SimpleNamespace(text=self.text, usage_metadata=self.usage)


@pytest.fixture
def gate(line_db):
    engine, data = line_db
    with engine.begin() as conn:
        conn.execute(line_ai_control.insert().values(id=1, enabled=True))
    provider = Provider()
    gateway = LineAIGateway(sessionmaker(bind=engine), provider, Decimal("0.001792"))
    return engine, data, provider, gateway


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "typo"])
def test_unusable_budget_does_not_enable_provider(value):
    assert read_line_ai_budget({"NOMICA_LINE_AI_MONTHLY_USD": value}) is None


@pytest.mark.parametrize("env", [{}, {"NOMICA_LINE_AI_MONTHLY_USD": ""}, {"NOMICA_LINE_AI_MONTHLY_USD": "  "}])
def test_unset_budget_uses_default_cap(env):
    assert read_line_ai_budget(env) == Decimal("5")


def test_explicit_budget_overrides_default():
    assert read_line_ai_budget({"NOMICA_LINE_AI_MONTHLY_USD": "2.50"}) == Decimal("2.50")


def consent(gateway, user_id, granted=True):
    with gateway.sessions.begin() as session:
        set_line_ai_consent(session, user_id, granted)


def test_consent_is_per_account_and_revocable(gate):
    engine, data, provider, gateway = gate
    consent(gateway, data["a"])
    with pytest.raises(AIRequestBlocked, match="同意 AI"):
        gateway.generate(data["b"], "other", "private text")
    gateway.generate(data["a"], "first", "private text")
    consent(gateway, data["a"], False)
    with pytest.raises(AIRequestBlocked, match="同意 AI"):
        gateway.generate(data["a"], "second", "private text")
    with engine.connect() as conn:
        attempt = conn.execute(select(line_ai_attempts)).mappings().one()
    assert attempt["status"] == "completed"
    assert attempt["input_tokens"] == 100 and attempt["output_tokens"] == 60
    assert attempt["charge_usd"] == Decimal("0.000115")
    assert "private text" not in str(attempt)
    assert len(provider.calls) == 2


def test_parallel_reservation_and_unknown_result_cannot_repeat(gate):
    engine, data, provider, gateway = gate
    for role in ("a", "b"):
        consent(gateway, data[role])
    provider.release.clear()
    provider.fail = True
    with ThreadPoolExecutor() as pool:
        first = pool.submit(gateway.generate, data["a"], "first", "private text")
        try:
            assert provider.started.wait(5)
            with pytest.raises(AIRequestBlocked, match="費用上限"):
                gateway.generate(data["b"], "other", "private text")
            # The same person cannot start a second call while one is in flight.
            with pytest.raises(AIRequestBlocked, match="還在處理中"):
                gateway.generate(data["a"], "first", "private text")
        finally:
            provider.release.set()
        with pytest.raises(AIRequestBlocked, match="暫時"):
            first.result()
    with engine.connect() as conn:
        attempt = conn.execute(select(line_ai_attempts)).mappings().one()
    assert attempt["status"] == "unknown" and attempt["charge_usd"] == Decimal("0.001792")
    assert len(provider.calls) == 2


def test_tokens_and_live_switch_gate_provider(gate):
    engine, data, provider, gateway = gate
    for role in ("a", "b"):
        consent(gateway, data[role])
    provider.count = 4097
    with pytest.raises(AIRequestBlocked, match="太長"):
        gateway.generate(data["a"], "large", "test")
    assert [action for action, _ in provider.calls] == ["count"]
    with engine.begin() as conn:
        conn.execute(line_ai_control.update().values(enabled=False))
    with pytest.raises(AIRequestBlocked, match="暫停"):
        gateway.generate(data["b"], "switched-off", "test")
    assert len(provider.calls) == 1


def test_overrun_is_recorded_and_stops_future_dispatch(gate):
    engine, data, provider, gateway = gate
    for role in ("a", "b"):
        consent(gateway, data[role])
    provider.usage.candidates_token_count = 0
    provider.usage.thoughts_token_count = 600
    provider.usage.total_token_count = 700
    with pytest.raises(AIRequestBlocked, match="已暫停"):
        gateway.generate(data["a"], "overrun", "test")
    with pytest.raises(AIRequestBlocked, match="暫停"):
        gateway.generate(data["b"], "new", "test")
    with engine.connect() as conn:
        attempt = conn.execute(select(line_ai_attempts)).mappings().one()
    assert attempt["status"] == "limit_exceeded"
    assert attempt["output_tokens"] == 600
    assert len(provider.calls) == 2


def test_withdrawal_while_counting_stops_generation(gate, monkeypatch):
    _, data, provider, gateway = gate
    consent(gateway, data["a"])
    count = provider.count_tokens

    def count_then_revoke(**kwargs):
        result = count(**kwargs)
        consent(gateway, data["a"], False)
        return result

    monkeypatch.setattr(provider, "count_tokens", count_then_revoke)
    with pytest.raises(AIRequestBlocked, match="同意 AI"):
        gateway.generate(data["a"], "revoke", "test")
    assert [action for action, _ in provider.calls] == ["count"]


def test_configured_provider_is_line_only_and_sdk_does_not_retry(monkeypatch):
    from models.linebot import manager
    from models.linebot.manager import MissingGeminiModel

    monkeypatch.setenv("NOMICA_LINE_AI_MONTHLY_USD", "2.50")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic")
    monkeypatch.setenv("NOMICA_AI_MODE", "disabled")
    monkeypatch.setenv("NOMICA_LINE_MODE", "oral_pilot")
    monkeypatch.setenv("LINE_MSG_CHANNEL_SECRET", "synthetic-line-secret")
    monkeypatch.setenv("LINE_MSG_CHANNEL_ACCESS_TOKEN", "synthetic-line-token")
    provider = Provider()

    def create_client(**kwargs):
        assert kwargs["vertexai"] is False
        assert kwargs["http_options"].retry_options.attempts == 1
        return SimpleNamespace(models=provider)

    monkeypatch.setattr(manager.genai, "Client", create_client)
    db = SimpleNamespace(get_bind=lambda: None)
    monkeypatch.delenv("NOMICA_LINE_AI_PAID_PROJECT_VERIFIED", raising=False)
    assert manager.LineBotManager(None, db).line_ai_gateway is None
    monkeypatch.setenv("NOMICA_LINE_AI_PAID_PROJECT_VERIFIED", "true")
    bot = manager.LineBotManager(None, db)
    assert isinstance(bot.model, MissingGeminiModel)
    assert bot.line_ai_gateway.models is provider
    assert bot.line_ai_gateway.budget == Decimal("2.50")
    assert provider.calls == []


def test_withdrawal_after_reservation_blocks_token_count(gate, monkeypatch):
    _, data, provider, gateway = gate
    consent(gateway, data["a"])
    reserve = gateway._reserve

    def reserve_then_revoke(owner, event_id):
        reserve(owner, event_id)
        consent(gateway, owner, False)

    monkeypatch.setattr(gateway, "_reserve", reserve_then_revoke)
    with pytest.raises(AIRequestBlocked, match="同意 AI"):
        gateway.generate(data["a"], "revoke-before-count", "test")
    assert provider.calls == []


@pytest.mark.parametrize("env,expected", [
    ({}, 20), ({"NOMICA_LINE_AI_DAILY_PER_USER": ""}, 20), ({"NOMICA_LINE_AI_DAILY_PER_USER": "5"}, 5),
    ({"NOMICA_LINE_AI_DAILY_PER_USER": "0"}, None), ({"NOMICA_LINE_AI_DAILY_PER_USER": "-1"}, None),
    ({"NOMICA_LINE_AI_DAILY_PER_USER": "typo"}, None),
])
def test_daily_limit_setting_fails_closed(env, expected):
    assert read_line_ai_daily_limit(env) == expected


def _past_attempts(engine, owner, statuses, when):
    with engine.begin() as conn:
        for i, status in enumerate(statuses):
            conn.execute(line_ai_attempts.insert().values(
                event_id=f"past-{status}-{i}-{when.timestamp()}", user_id=owner, month=when.date().replace(day=1),
                model="m", created_at=when, status=status, charge_usd=0))


def test_daily_cap_counts_sent_requests_since_local_midnight(line_db):
    engine, data = line_db
    with engine.begin() as conn:
        conn.execute(line_ai_control.insert().values(id=1, enabled=True))
    gateway = LineAIGateway(sessionmaker(bind=engine), Provider(), Decimal("1"), daily_limit=2)
    consent(gateway, data["a"])
    now = datetime.now(timezone.utc)
    midnight = now.astimezone(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    # Yesterday's requests and requests that never reached the provider do not count.
    _past_attempts(engine, data["a"], ["completed", "completed"], midnight - timedelta(minutes=1))
    _past_attempts(engine, data["a"], ["rejected", "rejected"], now - timedelta(minutes=1))
    _past_attempts(engine, data["a"], ["completed"], now - timedelta(minutes=1))
    gateway.generate(data["a"], "today-2", "private text")
    with pytest.raises(AIRequestBlocked, match="今天的 AI 解析次數已用完"):
        gateway.generate(data["a"], "today-3", "private text")
    # The cap is per person.
    consent(gateway, data["b"])
    gateway.generate(data["b"], "other-person", "private text")


def test_budget_alert_is_sent_once_per_month(line_db):
    engine, data = line_db
    with engine.begin() as conn:
        conn.execute(line_ai_control.insert().values(id=1, enabled=True))
    sent = []
    # One reservation already passes 80% of this budget.
    gateway = LineAIGateway(sessionmaker(bind=engine), Provider(), RESERVE * Decimal("1.1"), notify=sent.append)
    for role in ("a", "b"):
        consent(gateway, data[role])
    gateway.generate(data["a"], "first", "private text")
    gateway.generate(data["b"], "second", "private text")
    assert len(sent) == 1 and "本月用量已達" in sent[0]
    assert "private text" not in sent[0]


def test_alert_failure_does_not_block_the_request(line_db):
    engine, data = line_db
    with engine.begin() as conn:
        conn.execute(line_ai_control.insert().values(id=1, enabled=True))

    def broken(text):
        raise RuntimeError("push failed")
    gateway = LineAIGateway(sessionmaker(bind=engine), Provider(), RESERVE, notify=broken)
    consent(gateway, data["a"])
    gateway.generate(data["a"], "first", "private text")
    with engine.connect() as conn:
        assert conn.execute(select(line_ai_attempts.c.status)).scalar_one() == "completed"


def test_status_reports_consent_and_remaining_requests(gate):
    engine, data, provider, gateway = gate
    gateway.daily_limit = 3
    before = gateway.status(data["a"])
    assert before == {"enabled": True, "consented": False, "remaining": 3, "daily_limit": 3}
    consent(gateway, data["a"])
    gateway.generate(data["a"], "status-1", "private text")
    after = gateway.status(data["a"])
    assert after["consented"] is True and after["remaining"] == 2


def test_blocked_requests_carry_a_machine_readable_code(gate):
    engine, data, provider, gateway = gate
    with pytest.raises(AIRequestBlocked) as blocked:
        gateway.generate(data["a"], "no-consent", "private text")
    assert blocked.value.code == "consent_required"
    consent(gateway, data["a"])
    gateway.daily_limit = 1
    gateway.generate(data["a"], "one", "private text")
    with pytest.raises(AIRequestBlocked) as limited:
        gateway.generate(data["a"], "two", "private text")
    assert limited.value.code in {"daily_limit", "too_fast"}


def test_global_in_flight_cap_refuses_without_counting(gate, monkeypatch):
    engine, data, provider, gateway = gate
    from models import line_ai_gateway as module
    gateway.in_flight = module._InFlight(1)
    gateway.budget = Decimal("1")
    for role in ("a", "b"):
        consent(gateway, data[role])
    provider.release.clear()
    with ThreadPoolExecutor() as pool:
        first = pool.submit(gateway.generate, data["a"], "first", "private text")
        try:
            assert provider.started.wait(5)
            with pytest.raises(AIRequestBlocked) as busy:
                gateway.generate(data["b"], "second", "private text")
            assert busy.value.code == "busy"
        finally:
            provider.release.set()
        first.result()
    with engine.connect() as conn:
        ids = [row.event_id for row in conn.execute(select(line_ai_attempts))]
    assert ids == ["first"]  # the refused call left no attempt behind
    # The slot is free again afterwards.
    gateway.generate(data["b"], "third", "private text")
