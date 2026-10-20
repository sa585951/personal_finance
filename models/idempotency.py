"""Durable command results, committed atomically with their financial effects."""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from .schema import financial_commands_table


class IdempotencyConflict(ValueError):
    pass


def money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal('.0001')):
            raise ValueError('金額必須大於0且最多四位小數')
        return format(amount.normalize(), 'f')
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('金額格式不正確') from exc


def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


class IdempotencyManager:
    def __init__(self, db_session):
        self.db_session = db_session

    def execute(self, user_id, operation, request_id, payload, apply):
        # Legacy internal callers may omit a key; new Web clients always send it.
        if request_id is None:
            return {**apply(), 'replayed': False}
        try:
            key, owner = UUID(str(request_id)), UUID(str(user_id))
        except (ValueError, TypeError) as exc:
            raise ValueError('client_request_id 格式不正確') from exc
        digest = fingerprint(payload)
        table = financial_commands_table
        # A conflicting insert waits across workers. Failure rolls back the
        # reservation and all ledger writes together; the caller owns commit.
        with self.db_session.begin_nested():
            self.db_session.execute(insert(table).values(
                user_id=owner, operation=operation, request_id=key, payload_hash=digest,
            ).on_conflict_do_nothing(index_elements=['user_id', 'operation', 'request_id']))
            row = self.db_session.execute(select(table).where(
                table.c.user_id == owner, table.c.operation == operation, table.c.request_id == key,
            ).with_for_update()).mappings().one()
            if row['payload_hash'] != digest:
                raise IdempotencyConflict('同一請求識別碼不可用於不同資料，請先確認原提交結果')
            if row['result'] is not None:
                return {**row['result'], 'replayed': True}
            result = apply()
            if not result.get('success'):
                raise ValueError(result.get('message') or '操作未完成')
            self.db_session.execute(update(table).where(table.c.id == row['id']).values(result=result))
            return {**result, 'replayed': False}
