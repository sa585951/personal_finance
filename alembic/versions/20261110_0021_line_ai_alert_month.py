"""Remember which month the LINE AI 80% budget alert was sent."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261110_0021"
down_revision = "20261109_0020"
branch_labels = None
depends_on = None


def upgrade():
    # 0020 builds tables from current metadata, so a fresh database may already have it.
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("line_ai_control")}
    if "alert_month" not in columns:
        op.add_column("line_ai_control", sa.Column("alert_month", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("line_ai_control", "alert_month")
