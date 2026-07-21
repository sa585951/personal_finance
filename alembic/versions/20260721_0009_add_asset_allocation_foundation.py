"""add asset allocation foundation

Revision ID: 20260721_0009
Revises: 20260626_0008
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260721_0009"
down_revision = "20260626_0008"
branch_labels = None
depends_on = None


def _has_table(bind, table_name):
    return table_name in sa.inspect(bind).get_table_names()


def upgrade():
    bind = op.get_bind()

    if not _has_table(bind, "portfolios"):
        op.create_table(
            "portfolios",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column(
                "base_currency",
                sa.String(length=3),
                sa.ForeignKey("currencies.code", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("archived_at", sa.DateTime(timezone=True)),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
            sa.Column("purge_after", sa.DateTime(timezone=True)),
            sa.CheckConstraint(
                "char_length(trim(name)) > 0",
                name="ck_portfolios_name_not_blank",
            ),
        )
        op.create_index("ix_portfolios_user_active", "portfolios", ["user_id", "is_active"])
        op.create_index(
            "uq_portfolios_user_currency_name_active",
            "portfolios",
            ["user_id", "base_currency", "name"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    if not _has_table(bind, "holdings"):
        op.create_table(
            "holdings",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "portfolio_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("portfolios.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "account_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("symbol", sa.String(length=50)),
            sa.Column("asset_class", sa.String(length=50)),
            sa.Column("target_weight", sa.Numeric(9, 8)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("archived_at", sa.DateTime(timezone=True)),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
            sa.Column("purge_after", sa.DateTime(timezone=True)),
            sa.CheckConstraint(
                "char_length(trim(name)) > 0",
                name="ck_holdings_name_not_blank",
            ),
            sa.CheckConstraint(
                "target_weight IS NULL OR (target_weight >= 0 AND target_weight <= 1)",
                name="ck_holdings_target_weight_range",
            ),
        )
        op.create_index("ix_holdings_portfolio_active", "holdings", ["portfolio_id", "is_active"])
        op.create_index("ix_holdings_account", "holdings", ["account_id"])
        op.create_index(
            "uq_holdings_portfolio_account_name_active",
            "holdings",
            ["portfolio_id", "account_id", "name"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    if not _has_table(bind, "holding_cost_entries"):
        op.create_table(
            "holding_cost_entries",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "holding_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("holdings.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "source_transfer_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("transfers.id", ondelete="RESTRICT"),
            ),
            sa.Column("entry_type", sa.String(length=30), nullable=False),
            sa.Column("amount", sa.Numeric(18, 4), nullable=False),
            sa.Column(
                "currency",
                sa.String(length=3),
                sa.ForeignKey("currencies.code", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("occurred_on", sa.Date(), nullable=False),
            sa.Column("note", sa.Text()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
            sa.Column("purge_after", sa.DateTime(timezone=True)),
            sa.CheckConstraint(
                "entry_type in ('transfer', 'manual_adjustment')",
                name="ck_holding_cost_entries_type",
            ),
            sa.CheckConstraint(
                "amount > 0",
                name="ck_holding_cost_entries_amount_positive",
            ),
            sa.CheckConstraint(
                "(entry_type = 'transfer' AND source_transfer_id IS NOT NULL) OR "
                "(entry_type = 'manual_adjustment' AND source_transfer_id IS NULL)",
                name="ck_holding_cost_entries_source",
            ),
        )
        op.create_index(
            "ix_holding_cost_entries_holding_date",
            "holding_cost_entries",
            ["holding_id", "occurred_on"],
        )
        op.create_index(
            "ix_holding_cost_entries_transfer",
            "holding_cost_entries",
            ["source_transfer_id"],
        )
        op.create_index(
            "uq_holding_cost_entries_holding_transfer_active",
            "holding_cost_entries",
            ["holding_id", "source_transfer_id"],
            unique=True,
            postgresql_where=sa.text(
                "deleted_at IS NULL AND source_transfer_id IS NOT NULL"
            ),
        )

    if not _has_table(bind, "portfolio_snapshots"):
        op.create_table(
            "portfolio_snapshots",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "portfolio_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("portfolios.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column(
                "currency",
                sa.String(length=3),
                sa.ForeignKey("currencies.code", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("note", sa.Text()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
            sa.Column("purge_after", sa.DateTime(timezone=True)),
        )
        op.create_index(
            "ix_portfolio_snapshots_portfolio_date",
            "portfolio_snapshots",
            ["portfolio_id", "snapshot_date"],
        )
        op.create_index(
            "uq_portfolio_snapshots_portfolio_date_active",
            "portfolio_snapshots",
            ["portfolio_id", "snapshot_date"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    if not _has_table(bind, "portfolio_snapshot_items"):
        op.create_table(
            "portfolio_snapshot_items",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "snapshot_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("portfolio_snapshots.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "holding_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("holdings.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("value", sa.Numeric(18, 4), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "snapshot_id",
                "holding_id",
                name="uq_portfolio_snapshot_items_holding",
            ),
            sa.CheckConstraint(
                "value >= 0",
                name="ck_portfolio_snapshot_items_value_non_negative",
            ),
        )
        op.create_index(
            "ix_portfolio_snapshot_items_snapshot",
            "portfolio_snapshot_items",
            ["snapshot_id"],
        )


def downgrade():
    bind = op.get_bind()

    for table_name in (
        "portfolio_snapshot_items",
        "portfolio_snapshots",
        "holding_cost_entries",
        "holdings",
        "portfolios",
    ):
        if _has_table(bind, table_name):
            op.drop_table(table_name)
