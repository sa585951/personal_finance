"""Remove typed sentences from stored parse events.

Data only, no schema change. Web parse events lose the raw sentence, the parser's legacy copy and
all free-text fields (title becomes a fingerprint); LINE events lose only the raw sentence, since a
pending LINE draft still needs its own fields. This cannot be undone: the removed text is gone.
"""
import hashlib
import json
import unicodedata

from alembic import op
from sqlalchemy import text

revision = "20261116_0024"
down_revision = "20261112_0023"
branch_labels = None
depends_on = None

SAFE_TRANSACTION_FIELDS = ("type", "budget_category", "amount", "currency", "date", "account_id")
BATCH = 500


def _digest(value):
    return hashlib.sha256(unicodedata.normalize("NFKC", str(value or "")).strip().encode("utf-8")).hexdigest()


def _redact(payload):
    transaction = payload.get("transaction")
    safe = {
        "intent": payload.get("intent"),
        "source": payload.get("source"),
        "missing_fields": payload.get("missing_fields") or [],
        "errors": payload.get("errors") or [],
        "transaction": None,
    }
    if isinstance(transaction, dict):
        safe["transaction"] = {key: transaction[key] for key in SAFE_TRANSACTION_FIELDS if key in transaction}
        if transaction.get("title"):
            safe["transaction"]["title_hash"] = _digest(transaction["title"])
        elif transaction.get("title_hash"):
            safe["transaction"]["title_hash"] = transaction["title_hash"]
    return safe


def upgrade():
    connection = op.get_bind()
    # LINE drafts keep their own fields; only the typed sentence goes.
    connection.execute(text(
        "UPDATE ai_parse_events SET raw_input = '', parsed_payload = parsed_payload - 'raw_text' "
        "WHERE parsed_payload ->> 'line_oral' IS NOT NULL"))
    while True:
        rows = connection.execute(text(
            "SELECT id, parsed_payload FROM ai_parse_events "
            "WHERE (raw_input <> '' OR parsed_payload ? 'raw_text' OR parsed_payload ? 'legacy') "
            "AND parsed_payload ->> 'line_oral' IS NULL ORDER BY id LIMIT :n"
        ).bindparams(n=BATCH)).all()
        if not rows:
            break
        for row_id, payload in rows:
            if not isinstance(payload, dict):
                connection.execute(text("UPDATE ai_parse_events SET raw_input = '' WHERE id = :id"), {"id": row_id})
                continue
            connection.execute(
                text("UPDATE ai_parse_events SET raw_input = '', parsed_payload = CAST(:payload AS JSONB) WHERE id = :id"),
                {"payload": json.dumps(_redact(payload)), "id": row_id},
            )


def downgrade():
    # The removed text cannot be restored.
    pass
