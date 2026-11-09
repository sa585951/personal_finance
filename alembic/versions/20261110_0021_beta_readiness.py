"""Beta readiness: LINE AI budget alert month, product events, unchanged-draft flag.

Only additions; existing data is not touched and older code keeps working.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

from models.schema import product_events_table

revision = "20261110_0021"
down_revision = "20261109_0020"
branch_labels = None
depends_on = None


def _columns(inspector, table):
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade():
    connection = op.get_bind()
    inspector = inspect(connection)
    # Earlier migrations build tables from current metadata, so a fresh database
    # may already have everything below.
    if "alert_month" not in _columns(inspector, "line_ai_control"):
        op.add_column("line_ai_control", sa.Column("alert_month", sa.Date(), nullable=True))
    if "confirmed_unchanged" not in _columns(inspector, "ai_parse_events"):
        op.add_column("ai_parse_events", sa.Column("confirmed_unchanged", sa.Boolean(), nullable=True))
    if not inspector.has_table(product_events_table.name):
        product_events_table.create(connection)
    api_roles = connection.scalars(text(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
    )).all()
    grantees = ", ".join(["PUBLIC", *api_roles])
    op.execute(text(f"ALTER TABLE {product_events_table.name} ENABLE ROW LEVEL SECURITY"))
    op.execute(text(f"REVOKE ALL ON TABLE {product_events_table.name} FROM {grantees}"))


def downgrade():
    op.drop_table(product_events_table.name)
    op.drop_column("ai_parse_events", "confirmed_unchanged")
    op.drop_column("line_ai_control", "alert_month")
