"""add semantic account appearance

Revision ID: 20260826_0014
Revises: 20260821_0013
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0014"
down_revision = "20260821_0013"
branch_labels = None
depends_on = None


ICON_KEYS = "'bank', 'wallet', 'card', 'investment', 'savings', 'deposit', 'digital', 'external', 'other'"
COLOR_KEYS = "'teal', 'blue', 'green', 'amber', 'rose', 'purple', 'slate'"


def upgrade():
    op.add_column(
        "accounts",
        sa.Column(
            "icon_key",
            sa.String(length=30),
            server_default=sa.text("'other'"),
            nullable=False,
        ),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "color_key",
            sa.String(length=20),
            server_default=sa.text("'slate'"),
            nullable=False,
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE accounts
            SET
                icon_key = CASE type
                    WHEN 'bank' THEN 'bank'
                    WHEN 'cash' THEN 'wallet'
                    WHEN 'credit_card' THEN 'card'
                    WHEN 'e_wallet' THEN 'digital'
                    WHEN 'prepaid_card' THEN 'card'
                    WHEN 'external' THEN 'external'
                    WHEN 'investment' THEN 'investment'
                    ELSE 'other'
                END,
                color_key = CASE type
                    WHEN 'bank' THEN 'blue'
                    WHEN 'cash' THEN 'green'
                    WHEN 'credit_card' THEN 'rose'
                    WHEN 'e_wallet' THEN 'purple'
                    WHEN 'prepaid_card' THEN 'amber'
                    WHEN 'investment' THEN 'teal'
                    ELSE 'slate'
                END
            """
        )
    )

    op.create_check_constraint(
        "ck_accounts_icon_key",
        "accounts",
        f"icon_key in ({ICON_KEYS})",
    )
    op.create_check_constraint(
        "ck_accounts_color_key",
        "accounts",
        f"color_key in ({COLOR_KEYS})",
    )


def downgrade():
    op.drop_constraint("ck_accounts_color_key", "accounts", type_="check")
    op.drop_constraint("ck_accounts_icon_key", "accounts", type_="check")
    op.drop_column("accounts", "color_key")
    op.drop_column("accounts", "icon_key")
