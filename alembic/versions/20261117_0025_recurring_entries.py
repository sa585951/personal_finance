"""Fixed monthly income and expenses: rules and the pending items they generate."""
from alembic import op
from sqlalchemy import inspect, text

from models.schema import recurring_occurrences_table, recurring_rules_table

revision = "20261117_0025"
down_revision = "20261116_0024"
branch_labels = None
depends_on = None

TABLES = (recurring_rules_table, recurring_occurrences_table)


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
