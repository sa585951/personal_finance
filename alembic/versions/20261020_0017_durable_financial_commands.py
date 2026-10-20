"""Durable transfer/settlement requests and LINE event results."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '20261020_0017'
down_revision = '20261008_0016'
branch_labels = None
depends_on = None


def upgrade():
    # 0001 creates current metadata on fresh installs; support deployed0016 too.
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'financial_commands' not in tables:
        op.create_table('financial_commands',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('operation', sa.String(40), nullable=False),
            sa.Column('request_id', UUID(as_uuid=True), nullable=False),
            sa.Column('payload_hash', sa.String(64), nullable=False),
            sa.Column('result', JSONB),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.UniqueConstraint('user_id', 'operation', 'request_id', name='uq_financial_commands_request'))
    if 'line_webhook_events' not in tables:
        op.create_table('line_webhook_events',
            sa.Column('event_id', sa.String(255), primary_key=True),
            sa.Column('payload_hash', sa.String(64), nullable=False),
            sa.Column('reply_payload', JSONB),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')))


def downgrade():
    # Removes replay protection; never downgrade automatically after an error.
    op.drop_table('line_webhook_events')
    op.drop_table('financial_commands')
