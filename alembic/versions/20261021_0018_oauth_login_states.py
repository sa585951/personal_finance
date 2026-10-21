"""Browser-bound one-time OAuth login challenges, without user data."""
from alembic import op
import sqlalchemy as sa

revision = "20261021_0018"
down_revision = "20261020_0017"
branch_labels = None
depends_on = None


def upgrade():
    # The historical baseline imports current metadata on a fresh database.
    if "oauth_login_states" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "oauth_login_states",
            sa.Column("state_hash", sa.String(64), primary_key=True),
            sa.Column("browser_hash", sa.String(64), nullable=False),
            sa.Column("redirect_path", sa.String(2048), nullable=False),
            sa.Column("nonce", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_oauth_login_states_expiry", "oauth_login_states", ["expires_at"])


def downgrade():
    op.drop_table("oauth_login_states")
