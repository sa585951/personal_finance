"""add settlement account entries

Revision ID: 20260821_0012
Revises: 20260820_0011
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260821_0012"
down_revision = "20260820_0011"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "settlement_account_entries" in tables:
        return

    op.create_table(
        "settlement_account_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trip_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'posted'"), nullable=False),
        sa.Column("balance_before", sa.Numeric(18, 4), nullable=False),
        sa.Column("balance_after", sa.Numeric(18, 4), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reversal_balance_before", sa.Numeric(18, 4), nullable=True),
        sa.Column("reversal_balance_after", sa.Numeric(18, 4), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reversal_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "direction in ('incoming', 'outgoing')",
            name="ck_settlement_account_entries_direction",
        ),
        sa.CheckConstraint("amount > 0", name="ck_settlement_account_entries_amount_positive"),
        sa.CheckConstraint(
            "status in ('posted', 'reversed')",
            name="ck_settlement_account_entries_status",
        ),
        sa.CheckConstraint(
            "(direction = 'incoming' AND balance_after = balance_before + amount) OR "
            "(direction = 'outgoing' AND balance_after = balance_before - amount)",
            name="ck_settlement_account_entries_posting_math",
        ),
        sa.CheckConstraint(
            "(status = 'posted' AND reversal_balance_before IS NULL AND reversal_balance_after IS NULL "
            "AND reversed_at IS NULL AND reversed_by_user_id IS NULL) OR "
            "(status = 'reversed' AND reversal_balance_before IS NOT NULL AND reversal_balance_after IS NOT NULL "
            "AND reversed_at IS NOT NULL AND reversed_by_user_id IS NOT NULL)",
            name="ck_settlement_account_entries_reversal_state",
        ),
        sa.CheckConstraint(
            "status <> 'reversed' OR "
            "(direction = 'incoming' AND reversal_balance_after = reversal_balance_before - amount) OR "
            "(direction = 'outgoing' AND reversal_balance_after = reversal_balance_before + amount)",
            name="ck_settlement_account_entries_reversal_math",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["currency"], ["currencies.code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reversed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["settlement_id"], ["settlements.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trip_member_id"], ["trip_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settlement_id", "user_id", name="uq_settlement_account_entries_user"),
    )
    op.create_index(
        "ix_settlement_account_entries_account_date",
        "settlement_account_entries",
        ["account_id", "posted_at"],
    )
    op.create_index(
        "ix_settlement_account_entries_user_status",
        "settlement_account_entries",
        ["user_id", "status"],
    )


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "settlement_account_entries" in tables:
        op.drop_table("settlement_account_entries")
