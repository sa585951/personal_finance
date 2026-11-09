"""Beta measurement: product events and whether a parsed draft was saved unchanged."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

from models.schema import product_events_table

revision = "20261110_0022"
down_revision = "20261110_0021"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = inspect(connection)
    # Earlier migrations may build tables from current metadata on a fresh database.
    if not inspector.has_table(product_events_table.name):
        product_events_table.create(connection)
    api_roles = connection.scalars(text(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
    )).all()
    grantees = ", ".join(["PUBLIC", *api_roles])
    op.execute(text(f"ALTER TABLE {product_events_table.name} ENABLE ROW LEVEL SECURITY"))
    op.execute(text(f"REVOKE ALL ON TABLE {product_events_table.name} FROM {grantees}"))
    columns = {column["name"] for column in inspector.get_columns("ai_parse_events")}
    if "confirmed_unchanged" not in columns:
        op.add_column("ai_parse_events", sa.Column("confirmed_unchanged", sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column("ai_parse_events", "confirmed_unchanged")
    op.drop_table(product_events_table.name)
