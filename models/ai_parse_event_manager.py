import hashlib
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import desc, insert, or_, select, update

from .schema import ai_parse_events_table


SAFE_TRANSACTION_FIELDS = ("type", "budget_category", "amount", "currency", "date", "account_id")

# The typed sentence is kept only where it helps improve the rules: a parse that failed, or a draft the
# person changed before saving. Everything else loses it within a day, and nothing outlives 30 days.
SENTENCE_KEEP_DAYS = 30
DRAFT_SENTENCE_HOURS = 24
MAX_SENTENCE_CHARS = 200
PURGE_INTERVAL = timedelta(minutes=10)
_last_purge = None


def clip_sentence(text):
    return str(text or "").strip()[:MAX_SENTENCE_CHARS]


def title_digest(value):
    """Fingerprint of a title so a draft can be compared with the saved entry without keeping the words."""
    return hashlib.sha256(unicodedata.normalize("NFKC", str(value or "")).strip().encode("utf-8")).hexdigest()


def redact_parse_result(parse_result):
    """The parse outcome without anything the person typed: no sentence, title, note or merchant.

    What remains is enough to measure whether a draft was used unchanged: type, category, amount,
    currency, date and account id, plus a fingerprint of the title.
    """
    transaction = parse_result.get("transaction")
    safe = {
        "intent": parse_result.get("intent"),
        "source": parse_result.get("source"),
        "missing_fields": parse_result.get("missing_fields") or [],
        "errors": parse_result.get("errors") or [],
        "transaction": None,
    }
    if transaction:
        safe["transaction"] = {key: transaction[key] for key in SAFE_TRANSACTION_FIELDS if key in transaction}
        if transaction.get("title"):
            safe["transaction"]["title_hash"] = title_digest(transaction["title"])
    return safe


class AIParseEventManager:
    """管理跨入口 AI parse event 紀錄。"""

    def __init__(self, db_session):
        self.db_session = db_session

    def record_parse_event(
        self,
        user_id,
        source,
        raw_input,
        parsed_payload,
        status,
        result_type=None,
        result_id=None,
        confidence=None,
        error_message=None,
    ):
        self.purge_expired_sentences()
        payload = self._to_jsonable(parsed_payload)
        stmt = (
            insert(ai_parse_events_table)
            .values(
                user_id=UUID(str(user_id)),
                source=source,
                raw_input=raw_input,
                parsed_payload=payload,
                confidence=confidence,
                status=status,
                result_type=result_type,
                result_id=UUID(str(result_id)) if result_id else None,
                error_message=error_message,
            )
            .returning(ai_parse_events_table)
        )
        row = self.db_session.execute(stmt).first()
        return dict(row._mapping)

    def record_from_parse_result(self, user_id, source, parse_result):
        errors = parse_result.get("errors") or []
        status = "failed" if errors else "success"
        transaction = parse_result.get("transaction")

        return self.record_parse_event(
            user_id=user_id,
            source=source,
            # Kept for now so a failed or edited draft can be reviewed; purge_expired_sentences clears it.
            raw_input=clip_sentence(parse_result.get("raw_text")),
            parsed_payload=redact_parse_result(parse_result),
            status=status,
            result_type=transaction.get("type") if transaction else parse_result.get("intent"),
            error_message="; ".join(errors) if errors else None,
        )

    def record_failure(self, user_id, source, sentence, reason):
        """A sentence the rules (and AI, if on) could not turn into an entry; kept for rule improvement."""
        return self.record_parse_event(
            user_id=user_id, source=source, raw_input=clip_sentence(sentence),
            parsed_payload={"failure": reason}, status="failed", error_message=reason,
        )

    def purge_expired_sentences(self, now=None, force=False):
        """Clear sentences that no longer earn their place. Runs at most every few minutes per process."""
        global _last_purge
        now = now or datetime.now(timezone.utc)
        if not force and _last_purge is not None and now - _last_purge < PURGE_INTERVAL:
            return
        _last_purge = now
        table = ai_parse_events_table
        has_text = table.c.raw_input != ""
        self.db_session.execute(update(table).where(
            has_text, table.c.created_at < now - timedelta(days=SENTENCE_KEEP_DAYS)).values(raw_input=""))
        # Worth keeping: a failure, or a draft the person edited. Anything else only waits for its confirmation.
        worth_keeping = or_(table.c.status == "failed", table.c.confirmed_unchanged.is_(False))
        self.db_session.execute(update(table).where(
            has_text, ~worth_keeping, table.c.created_at < now - timedelta(hours=DRAFT_SENTENCE_HOURS),
        ).values(raw_input=""))

    @staticmethod
    def draft_unchanged(parsed_payload, submitted):
        """True when the saved entry matches every field the parser filled in."""
        draft = (parsed_payload or {}).get("transaction") or {}

        def same_amount(left, right):
            try:
                return Decimal(str(left)) == Decimal(str(right))
            except (InvalidOperation, TypeError, ValueError):
                return False

        checks = []
        if draft.get("amount") not in (None, ""):
            checks.append(same_amount(draft["amount"], submitted.get("amount")))
        if draft.get("budget_category"):
            checks.append(draft["budget_category"] == submitted.get("budget_category"))
        if draft.get("title_hash"):
            checks.append(draft["title_hash"] == title_digest(submitted.get("item")))
        elif draft.get("title"):  # events recorded before titles stopped being stored
            checks.append(draft["title"] == submitted.get("item"))
        if draft.get("date"):
            checks.append(draft["date"] == submitted.get("date"))
        if draft.get("account_id"):
            checks.append(str(draft["account_id"]) == str(submitted.get("account_id") or ""))
        return bool(checks) and all(checks)

    def confirm_event(self, user_id, event_id, result_type, result_id, *, unchanged=None):
        values = dict(status="confirmed", result_type=result_type, result_id=UUID(str(result_id)),
                      confirmed_unchanged=unchanged)
        if unchanged is True:
            values["raw_input"] = ""  # Saved as parsed: nothing to learn from the sentence.
        stmt = (
            update(ai_parse_events_table)
            .where(
                ai_parse_events_table.c.id == UUID(str(event_id)),
                ai_parse_events_table.c.user_id == UUID(str(user_id)),
            )
            .values(**values)
            .returning(ai_parse_events_table)
        )
        row = self.db_session.execute(stmt).first()
        if not row:
            raise ValueError("找不到可確認的 AI 解析紀錄")
        return dict(row._mapping)

    def parsed_payload(self, user_id, event_id):
        try:
            key = UUID(str(event_id))
        except ValueError:
            return None
        return self.db_session.scalar(select(ai_parse_events_table.c.parsed_payload).where(
            ai_parse_events_table.c.id == key, ai_parse_events_table.c.user_id == UUID(str(user_id))))

    def list_recent_events(self, user_id, limit=20):
        safe_limit = max(1, min(int(limit or 20), 100))
        stmt = (
            select(ai_parse_events_table)
            .where(ai_parse_events_table.c.user_id == UUID(str(user_id)))
            .order_by(desc(ai_parse_events_table.c.created_at))
            .limit(safe_limit)
        )
        rows = self.db_session.execute(stmt).fetchall()
        return [
            self._to_jsonable(dict(row._mapping))
            for row in rows
        ]

    def _to_jsonable(self, value):
        if isinstance(value, dict):
            return {key: self._to_jsonable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, tuple):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, (UUID, Decimal, date, datetime)):
            return str(value)
        return value
