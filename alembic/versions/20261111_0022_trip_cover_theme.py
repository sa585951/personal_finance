"""Optional preset cover theme for each trip."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261111_0022"
down_revision = "20261110_0021"
branch_labels = None
depends_on = None


def upgrade():
    # The initial migration builds tables from current metadata, so a fresh database may have it.
    if "cover_theme" not in {c["name"] for c in inspect(op.get_bind()).get_columns("trips")}:
        op.add_column("trips", sa.Column("cover_theme", sa.String(20), nullable=True))


def downgrade():
    op.drop_column("trips", "cover_theme")
