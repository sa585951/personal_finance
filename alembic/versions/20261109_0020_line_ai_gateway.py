"""Add LINE AI consent, usage accounting and a live stop switch."""
from alembic import op
from sqlalchemy import inspect, text

from models.schema import line_ai_attempts, line_ai_consents, line_ai_control

revision = "20261109_0020"
down_revision = "20261030_0019"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    api_roles = connection.scalars(text(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
    )).all()
    grantees = ", ".join(["PUBLIC", *api_roles])
    for table in (line_ai_consents, line_ai_control, line_ai_attempts):
        # The historical baseline may have created current metadata already.
        if not inspect(connection).has_table(table.name):
            table.create(connection)
        op.execute(text(f"ALTER TABLE {table.name} ENABLE ROW LEVEL SECURITY"))
        # RLS does not cover privileges such as TRUNCATE granted by API defaults.
        op.execute(text(f"REVOKE ALL ON TABLE {table.name} FROM {grantees}"))
    op.execute(text("INSERT INTO line_ai_control (id, enabled) VALUES (1, true) ON CONFLICT DO NOTHING"))


def downgrade():
    for table in (line_ai_attempts, line_ai_control, line_ai_consents):
        op.drop_table(table.name)
