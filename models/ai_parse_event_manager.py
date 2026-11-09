from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import desc, insert, select, update

from .schema import ai_parse_events_table


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
            raw_input=parse_result.get("raw_text", ""),
            parsed_payload=parse_result,
            status=status,
            result_type=transaction.get("type") if transaction else parse_result.get("intent"),
            error_message="; ".join(errors) if errors else None,
        )

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
        if draft.get("title"):
            checks.append(draft["title"] == submitted.get("item"))
        if draft.get("date"):
            checks.append(draft["date"] == submitted.get("date"))
        if draft.get("account_id"):
            checks.append(str(draft["account_id"]) == str(submitted.get("account_id") or ""))
        return bool(checks) and all(checks)

    def confirm_event(self, user_id, event_id, result_type, result_id, *, unchanged=None):
        stmt = (
            update(ai_parse_events_table)
            .where(
                ai_parse_events_table.c.id == UUID(str(event_id)),
                ai_parse_events_table.c.user_id == UUID(str(user_id)),
            )
            .values(
                status="confirmed",
                result_type=result_type,
                result_id=UUID(str(result_id)),
                confirmed_unchanged=unchanged,
            )
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
