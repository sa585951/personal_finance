"""add trip member monthly report preference

Revision ID: 20260618_0007
Revises: 20260618_0006
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_0007"
down_revision = "20260618_0006"
branch_labels = None
depends_on = None


def _has_trip_members_table(bind):
    inspector = sa.inspect(bind)
    return "trip_members" in inspector.get_table_names()


def _has_trips_table(bind):
    inspector = sa.inspect(bind)
    return "trips" in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    if not _has_trip_members_table(bind):
        return

    columns = {column["name"] for column in sa.inspect(bind).get_columns("trip_members")}
    if "monthly_report_preference" not in columns:
        op.add_column(
            "trip_members",
            sa.Column("monthly_report_preference", sa.String(length=20), nullable=True),
        )

    if _has_trips_table(bind):
        bind.execute(
            sa.text(
                """
                UPDATE trip_members
                SET monthly_report_preference = CASE
                    WHEN trips.include_in_monthly_report THEN 'include'
                    ELSE 'exclude'
                END
                FROM trips
                WHERE trip_members.trip_id = trips.id
                  AND trip_members.role = 'owner'
                  AND trip_members.user_id IS NOT NULL
                  AND trip_members.monthly_report_preference IS NULL
                """
            )
        )

    bind.execute(
        sa.text(
            """
            UPDATE trip_members
            SET monthly_report_preference = 'pending'
            WHERE user_id IS NOT NULL
              AND role <> 'owner'
              AND status = 'active'
              AND deleted_at IS NULL
              AND monthly_report_preference IS NULL
            """
        )
    )

    op.create_check_constraint(
        "ck_trip_members_monthly_report_preference",
        "trip_members",
        "monthly_report_preference in ('pending', 'include', 'exclude')",
    )


def downgrade():
    bind = op.get_bind()
    if not _has_trip_members_table(bind):
        return

    op.drop_constraint(
        "ck_trip_members_monthly_report_preference",
        "trip_members",
        type_="check",
    )
    columns = {column["name"] for column in sa.inspect(bind).get_columns("trip_members")}
    if "monthly_report_preference" in columns:
        op.drop_column("trip_members", "monthly_report_preference")
