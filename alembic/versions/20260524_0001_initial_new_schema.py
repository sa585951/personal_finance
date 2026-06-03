"""initial new schema

Revision ID: 20260524_0001
Revises: None
Create Date: 2026-05-24
"""

from alembic import op
from sqlalchemy import text

from models.schema import metadata
from models.seed_data import seed_reference_data

revision = "20260524_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    bind.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    metadata.create_all(bind=bind)
    seed_reference_data(bind)


def downgrade():
    bind = op.get_bind()
    metadata.drop_all(bind=bind)
