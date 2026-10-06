"""add credit card billing profiles

Revision ID: 20260925_0015
Revises: 20260826_0014
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260925_0015"
down_revision = "20260826_0014"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    # See revision 0014: a fresh database may already have this current-schema
    # table after revision 0001, but deployed databases at 0014 still need it.
    if "credit_card_billing_profiles" not in table_names:
        op.create_table(
            "credit_card_billing_profiles",
            sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("closing_day", sa.Integer(), nullable=False),
            sa.Column("due_day", sa.Integer(), nullable=False),
            sa.Column("due_month_offset", sa.Integer(), nullable=False),
            sa.Column("override_closing_date", sa.Date()),
            sa.Column("override_due_date", sa.Date()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.CheckConstraint("closing_day between 1 and 31", name="ck_credit_card_billing_closing_day"),
            sa.CheckConstraint("due_day between 1 and 31", name="ck_credit_card_billing_due_day"),
            sa.CheckConstraint("due_month_offset in (0, 1)", name="ck_credit_card_billing_due_month_offset"),
            sa.CheckConstraint(
                "(override_closing_date is null) = (override_due_date is null)",
                name="ck_credit_card_billing_override_pair",
            ),
            sa.CheckConstraint(
                "override_due_date > override_closing_date or override_due_date is null",
                name="ck_credit_card_billing_override_after_close",
            ),
        )
        op.create_index("ix_credit_card_billing_profiles_user", "credit_card_billing_profiles", ["user_id"])
        return

    indexes = {
        index["name"] for index in inspector.get_indexes("credit_card_billing_profiles")
    }
    if "ix_credit_card_billing_profiles_user" not in indexes:
        op.create_index("ix_credit_card_billing_profiles_user", "credit_card_billing_profiles", ["user_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "credit_card_billing_profiles" not in inspector.get_table_names():
        return

    indexes = {
        index["name"] for index in inspector.get_indexes("credit_card_billing_profiles")
    }
    if "ix_credit_card_billing_profiles_user" in indexes:
        op.drop_index("ix_credit_card_billing_profiles_user", table_name="credit_card_billing_profiles")
    op.drop_table("credit_card_billing_profiles")
