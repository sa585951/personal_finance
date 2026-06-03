"""add trip settlement confirmations

Revision ID: 20260526_0003
Revises: 20260526_0002
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260526_0003"
down_revision = "20260526_0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    if "settlements" in existing_tables:
        existing_indexes = {index["name"] for index in inspector.get_indexes("settlements")}
        if "ix_settlements_from_member" not in existing_indexes:
            op.create_index("ix_settlements_from_member", "settlements", ["from_member_id"], unique=False)
        if "ix_settlements_to_member" not in existing_indexes:
            op.create_index("ix_settlements_to_member", "settlements", ["to_member_id"], unique=False)
        if "ix_settlements_trip_status" not in existing_indexes:
            op.create_index("ix_settlements_trip_status", "settlements", ["trip_id", "status"], unique=False)
        return

    op.create_table(
        "settlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'confirmed'"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_settlements_amount_positive"),
        sa.CheckConstraint("from_member_id <> to_member_id", name="ck_settlements_different_members"),
        sa.CheckConstraint("status in ('confirmed', 'voided')", name="ck_settlements_status"),
        sa.ForeignKeyConstraint(["currency"], ["currencies.code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["from_member_id"], ["trip_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_member_id"], ["trip_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_settlements_from_member", "settlements", ["from_member_id"], unique=False)
    op.create_index("ix_settlements_to_member", "settlements", ["to_member_id"], unique=False)
    op.create_index("ix_settlements_trip_status", "settlements", ["trip_id", "status"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "settlements" not in inspector.get_table_names():
        return
    existing_indexes = {index["name"] for index in inspector.get_indexes("settlements")}
    if "ix_settlements_trip_status" in existing_indexes:
        op.drop_index("ix_settlements_trip_status", table_name="settlements")
    if "ix_settlements_to_member" in existing_indexes:
        op.drop_index("ix_settlements_to_member", table_name="settlements")
    if "ix_settlements_from_member" in existing_indexes:
        op.drop_index("ix_settlements_from_member", table_name="settlements")
    op.drop_table("settlements")
