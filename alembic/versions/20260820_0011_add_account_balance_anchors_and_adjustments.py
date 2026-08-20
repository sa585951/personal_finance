"""add account balance anchors and adjustments

Revision ID: 20260820_0011
Revises: 20260819_0010
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260820_0011"
down_revision = "20260819_0010"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "account_balance_anchors" not in tables:
        op.create_table(
            "account_balance_anchors",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("balance", sa.Numeric(18, 4), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("source", sa.String(length=30), nullable=False),
            sa.Column(
                "anchored_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "source in ('account_created', 'migration', 'user_confirmed')",
                name="ck_account_balance_anchors_source",
            ),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["currency"], ["currencies.code"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_account_balance_anchors_account_date",
            "account_balance_anchors",
            ["account_id", "anchored_at"],
        )

    if "account_adjustments" not in tables:
        op.create_table(
            "account_adjustments",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("client_request_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("amount_delta", sa.Numeric(18, 4), nullable=False),
            sa.Column("balance_before", sa.Numeric(18, 4), nullable=False),
            sa.Column("balance_after", sa.Numeric(18, 4), nullable=False),
            sa.Column("reason", sa.String(length=40), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "adjusted_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.CheckConstraint("amount_delta <> 0", name="ck_account_adjustments_non_zero"),
            sa.CheckConstraint(
                "balance_after = balance_before + amount_delta",
                name="ck_account_adjustments_balance_math",
            ),
            sa.CheckConstraint(
                "reason in ('balance_correction', 'statement_reconciliation', 'opening_balance', 'other')",
                name="ck_account_adjustments_reason",
            ),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_account_adjustments_account_date",
            "account_adjustments",
            ["account_id", "adjusted_at"],
        )
        op.create_index(
            "uq_account_adjustments_user_client_request_id",
            "account_adjustments",
            ["user_id", "client_request_id"],
            unique=True,
            postgresql_where=sa.text("client_request_id IS NOT NULL"),
        )

    # Existing balances become the trusted starting point. Historical movements
    # are intentionally not guessed or replayed during this migration.
    bind.execute(
        sa.text(
            """
            INSERT INTO account_balance_anchors
                (user_id, account_id, balance, currency, source, anchored_at)
            SELECT
                accounts.user_id,
                accounts.id,
                accounts.balance,
                accounts.currency,
                'migration',
                now()
            FROM accounts
            WHERE accounts.track_balance = true
              AND accounts.balance IS NOT NULL
              AND accounts.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM account_balance_anchors anchors
                  WHERE anchors.account_id = accounts.id
              )
            """
        )
    )


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "account_adjustments" in tables:
        op.drop_table("account_adjustments")
    if "account_balance_anchors" in tables:
        op.drop_table("account_balance_anchors")
