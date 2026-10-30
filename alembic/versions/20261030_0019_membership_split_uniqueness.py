"""R09 membership/split identity constraints; refuse ambiguous duplicate history."""
from alembic import op
import sqlalchemy as sa

revision = '20261030_0019'
down_revision = '20261021_0018'
branch_labels = None
depends_on = None

PAIRS = (
    ('trip_members', 'uq_trip_members_trip_user', ('trip_id', 'user_id'), 'WHERE user_id IS NOT NULL'),
    ('transaction_splits', 'uq_transaction_splits_transaction_member', ('transaction_id', 'trip_member_id'), ''),
)


def upgrade():
    connection = op.get_bind()
    # Check both before DDL. Never guess which member or split financial history to retain.
    for table, _, columns, where in PAIRS:
        grouped = ', '.join(columns)
        duplicate = connection.execute(sa.text(
            f'SELECT 1 FROM {table} {where} GROUP BY {grouped} HAVING count(*) > 1 LIMIT 1'
        )).first()
        if duplicate is not None:
            raise RuntimeError('R09 migration blocked by duplicate identity pairs; review a backup and approve a cleanup plan before retrying')
    for table, name, columns, _ in PAIRS:
        # The old initial migration imports current metadata on empty databases.
        existing = {c['name'] for c in sa.inspect(connection).get_unique_constraints(table)}
        if name not in existing:
            op.create_unique_constraint(name, table, list(columns))


def downgrade():
    for table, name, _, _ in reversed(PAIRS):
        op.drop_constraint(name, table, type_='unique')
