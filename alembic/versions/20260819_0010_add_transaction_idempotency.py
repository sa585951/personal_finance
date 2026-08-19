"""add transaction idempotency key

Revision ID: 20260819_0010
Revises: 20260721_0009
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260819_0010"
down_revision = "20260721_0009"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("transactions")}
    if "client_request_id" not in columns:
        op.add_column(
            "transactions",
            sa.Column("client_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("transactions")}
    if "uq_transactions_user_client_request_id" not in indexes:
        op.create_index(
            "uq_transactions_user_client_request_id",
            "transactions",
            ["user_id", "client_request_id"],
            unique=True,
            postgresql_where=sa.text("client_request_id IS NOT NULL"),
        )


def downgrade():
    bind = op.get_bind()
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("transactions")}
    if "uq_transactions_user_client_request_id" in indexes:
        op.drop_index("uq_transactions_user_client_request_id", table_name="transactions")

    columns = {column["name"] for column in sa.inspect(bind).get_columns("transactions")}
    if "client_request_id" in columns:
        op.drop_column("transactions", "client_request_id")
