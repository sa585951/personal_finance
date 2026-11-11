"""Per-trip shared exchange rates and their change history."""
from alembic import op
from sqlalchemy import inspect, text

from models.schema import trip_exchange_rate_changes_table, trip_exchange_rates_table

revision = "20261112_0023"
down_revision = "20261111_0022"
branch_labels = None
depends_on = None

TABLES = (trip_exchange_rates_table, trip_exchange_rate_changes_table)


def upgrade():
    connection = op.get_bind()
    api_roles = connection.scalars(text(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
    )).all()
    grantees = ", ".join(["PUBLIC", *api_roles])
    for table in TABLES:
        # The historical baseline may already have created current metadata.
        if not inspect(connection).has_table(table.name):
            table.create(connection)
        op.execute(text(f"ALTER TABLE {table.name} ENABLE ROW LEVEL SECURITY"))
        op.execute(text(f"REVOKE ALL ON TABLE {table.name} FROM {grantees}"))


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table.name)
