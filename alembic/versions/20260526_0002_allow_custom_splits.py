"""allow custom transaction splits

Revision ID: 20260526_0002
Revises: 20260524_0001
Create Date: 2026-05-26
"""

from alembic import op


revision = "20260526_0002"
down_revision = "20260524_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_transaction_splits_method", "transaction_splits", type_="check")
    op.create_check_constraint(
        "ck_transaction_splits_method",
        "transaction_splits",
        "split_method in ('equal', 'custom')",
    )


def downgrade():
    op.drop_constraint("ck_transaction_splits_method", "transaction_splits", type_="check")
    op.create_check_constraint(
        "ck_transaction_splits_method",
        "transaction_splits",
        "split_method in ('equal')",
    )
