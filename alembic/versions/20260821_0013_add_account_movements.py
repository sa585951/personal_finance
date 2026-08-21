"""add append-only account movements and reconciliation baseline

Revision ID: 20260821_0013
Revises: 20260821_0012
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260821_0013"
down_revision = "20260821_0012"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "account_movements" not in tables:
        op.create_table(
            "account_movements",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("source_type", sa.String(length=20), nullable=False),
            sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("operation", sa.String(length=30), nullable=False),
            sa.Column("amount_delta", sa.Numeric(18, 4), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("balance_before", sa.Numeric(18, 4), nullable=False),
            sa.Column("balance_after", sa.Numeric(18, 4), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.CheckConstraint(
                "source_type in ('transaction', 'transfer')",
                name="ck_account_movements_source_type",
            ),
            sa.CheckConstraint(
                "operation in ('create', 'update_reversal', 'update_apply', 'delete_reversal')",
                name="ck_account_movements_operation",
            ),
            sa.CheckConstraint("amount_delta <> 0", name="ck_account_movements_non_zero"),
            sa.CheckConstraint(
                "balance_after = balance_before + amount_delta",
                name="ck_account_movements_balance_math",
            ),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["currency"], ["currencies.code"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_account_movements_account_date",
            "account_movements",
            ["account_id", "occurred_at"],
        )
        op.create_index(
            "ix_account_movements_source",
            "account_movements",
            ["source_type", "source_id"],
        )

    anchor_checks = {check["name"] for check in inspector.get_check_constraints("account_balance_anchors")}
    if "ck_account_balance_anchors_source" in anchor_checks:
        op.drop_constraint(
            "ck_account_balance_anchors_source",
            "account_balance_anchors",
            type_="check",
        )
    op.create_check_constraint(
        "ck_account_balance_anchors_source",
        "account_balance_anchors",
        "source in ('account_created', 'migration', 'user_confirmed', 'reconciliation_baseline')",
    )

    # This anchor freezes the current snapshot. Only movements written by the new
    # backend after this point are replayed by reconciliation.
    op.execute(
        sa.text(
            """
            INSERT INTO account_balance_anchors
                (user_id, account_id, balance, currency, source, anchored_at)
            SELECT
                accounts.user_id,
                accounts.id,
                accounts.balance,
                accounts.currency,
                'reconciliation_baseline',
                now()
            FROM accounts
            WHERE accounts.track_balance = true
              AND accounts.balance IS NOT NULL
              AND accounts.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM account_balance_anchors anchors
                  WHERE anchors.account_id = accounts.id
                    AND anchors.source = 'reconciliation_baseline'
              )
            """
        )
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "account_balance_anchors" in tables:
        op.execute(
            sa.text(
                "DELETE FROM account_balance_anchors WHERE source = 'reconciliation_baseline'"
            )
        )
        anchor_checks = {
            check["name"] for check in sa.inspect(bind).get_check_constraints("account_balance_anchors")
        }
        if "ck_account_balance_anchors_source" in anchor_checks:
            op.drop_constraint(
                "ck_account_balance_anchors_source",
                "account_balance_anchors",
                type_="check",
            )
        op.create_check_constraint(
            "ck_account_balance_anchors_source",
            "account_balance_anchors",
            "source in ('account_created', 'migration', 'user_confirmed')",
        )

    if "account_movements" in tables:
        op.drop_table("account_movements")
