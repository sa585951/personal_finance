"""add investment account type

Revision ID: 20260611_0005
Revises: 20260603_0004
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260611_0005"
down_revision = "20260603_0004"
branch_labels = None
depends_on = None


OLD_ACCOUNT_TYPE_CHECK = (
    "type in ('cash', 'bank', 'credit_card', 'e_wallet', 'prepaid_card', 'external', 'other')"
)
NEW_ACCOUNT_TYPE_CHECK = (
    "type in ('cash', 'bank', 'credit_card', 'e_wallet', 'prepaid_card', 'external', 'investment', 'other')"
)


def _has_accounts_table(bind):
    inspector = sa.inspect(bind)
    return "accounts" in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    if not _has_accounts_table(bind):
        return

    op.drop_constraint("ck_accounts_type", "accounts", type_="check")
    op.create_check_constraint("ck_accounts_type", "accounts", NEW_ACCOUNT_TYPE_CHECK)


def downgrade():
    bind = op.get_bind()
    if not _has_accounts_table(bind):
        return

    bind.execute(sa.text("UPDATE accounts SET type = 'other' WHERE type = 'investment'"))
    op.drop_constraint("ck_accounts_type", "accounts", type_="check")
    op.create_check_constraint("ck_accounts_type", "accounts", OLD_ACCOUNT_TYPE_CHECK)
