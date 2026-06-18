"""add work expense category

Revision ID: 20260618_0006
Revises: 20260611_0005
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_0006"
down_revision = "20260611_0005"
branch_labels = None
depends_on = None


def _has_categories_table(bind):
    inspector = sa.inspect(bind)
    return "categories" in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    if not _has_categories_table(bind):
        return

    bind.execute(
        sa.text(
            """
            INSERT INTO categories (
                kind,
                scope,
                code,
                name,
                is_system,
                sort_order
            )
            VALUES (
                'expense',
                'transaction',
                'work',
                '工作',
                true,
                7
            )
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade():
    bind = op.get_bind()
    if not _has_categories_table(bind):
        return

    bind.execute(
        sa.text(
            """
            DELETE FROM categories
            WHERE user_id IS NULL
              AND parent_id IS NULL
              AND kind = 'expense'
              AND scope = 'transaction'
              AND code = 'work'
              AND name = '工作'
              AND NOT EXISTS (
                  SELECT 1
                  FROM transactions
                  WHERE transactions.category_id = categories.id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM budgets
                  WHERE budgets.category_id = categories.id
              )
            """
        )
    )
