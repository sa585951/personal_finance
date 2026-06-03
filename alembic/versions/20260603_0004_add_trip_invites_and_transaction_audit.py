"""add trip invites and transaction audit fields

Revision ID: 20260603_0004
Revises: 20260526_0003
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260603_0004"
down_revision = "20260526_0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "trip_invites" not in tables:
        op.create_table(
            "trip_invites",
            sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("role", sa.String(length=20), server_default=sa.text("'editor'"), nullable=False),
            sa.Column("status", sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("role in ('editor', 'viewer')", name="ck_trip_invites_role"),
            sa.CheckConstraint("status in ('active', 'closed')", name="ck_trip_invites_status"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_trip_invites_trip_status", "trip_invites", ["trip_id", "status"], unique=False)
        op.create_index("ix_trip_invites_token_hash", "trip_invites", ["token_hash"], unique=True)
        op.create_index(
            "uq_trip_invites_one_active",
            "trip_invites",
            ["trip_id"],
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
        )

    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    if "created_by_user_id" not in transaction_columns:
        op.add_column("transactions", sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_transactions_created_by_user_id_users",
            "transactions",
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        bind.execute(sa.text("UPDATE transactions SET created_by_user_id = user_id WHERE created_by_user_id IS NULL"))
        op.alter_column("transactions", "created_by_user_id", nullable=False)

    if "updated_by_user_id" not in transaction_columns:
        op.add_column("transactions", sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_transactions_updated_by_user_id_users",
            "transactions",
            "users",
            ["updated_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        bind.execute(sa.text("UPDATE transactions SET updated_by_user_id = user_id WHERE updated_by_user_id IS NULL"))

    if "deleted_by_user_id" not in transaction_columns:
        op.add_column("transactions", sa.Column("deleted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_transactions_deleted_by_user_id_users",
            "transactions",
            "users",
            ["deleted_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    if "review_status" not in transaction_columns:
        op.add_column(
            "transactions",
            sa.Column("review_status", sa.String(length=20), server_default=sa.text("'confirmed'"), nullable=False),
        )
        op.create_check_constraint(
            "ck_transactions_review_status",
            "transactions",
            "review_status in ('pending', 'confirmed')",
        )

    indexes = {index["name"] for index in inspector.get_indexes("transactions")}
    if "ix_transactions_created_by_date" not in indexes:
        op.create_index("ix_transactions_created_by_date", "transactions", ["created_by_user_id", "transaction_date"])
    if "ix_transactions_trip_date" not in indexes:
        op.create_index("ix_transactions_trip_date", "transactions", ["trip_id", "transaction_date"])

    member_indexes = {index["name"] for index in inspector.get_indexes("trip_members")}
    if "ix_trip_members_user_status" not in member_indexes:
        op.create_index("ix_trip_members_user_status", "trip_members", ["user_id", "status"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    transaction_indexes = {index["name"] for index in inspector.get_indexes("transactions")}
    if "ix_transactions_trip_date" in transaction_indexes:
        op.drop_index("ix_transactions_trip_date", table_name="transactions")
    if "ix_transactions_created_by_date" in transaction_indexes:
        op.drop_index("ix_transactions_created_by_date", table_name="transactions")

    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    if "review_status" in transaction_columns:
        op.drop_constraint("ck_transactions_review_status", "transactions", type_="check")
        op.drop_column("transactions", "review_status")
    if "deleted_by_user_id" in transaction_columns:
        op.drop_constraint("fk_transactions_deleted_by_user_id_users", "transactions", type_="foreignkey")
        op.drop_column("transactions", "deleted_by_user_id")
    if "updated_by_user_id" in transaction_columns:
        op.drop_constraint("fk_transactions_updated_by_user_id_users", "transactions", type_="foreignkey")
        op.drop_column("transactions", "updated_by_user_id")
    if "created_by_user_id" in transaction_columns:
        op.drop_constraint("fk_transactions_created_by_user_id_users", "transactions", type_="foreignkey")
        op.drop_column("transactions", "created_by_user_id")

    member_indexes = {index["name"] for index in inspector.get_indexes("trip_members")}
    if "ix_trip_members_user_status" in member_indexes:
        op.drop_index("ix_trip_members_user_status", table_name="trip_members")

    if "trip_invites" in inspector.get_table_names():
        invite_indexes = {index["name"] for index in inspector.get_indexes("trip_invites")}
        if "uq_trip_invites_one_active" in invite_indexes:
            op.drop_index("uq_trip_invites_one_active", table_name="trip_invites")
        if "ix_trip_invites_token_hash" in invite_indexes:
            op.drop_index("ix_trip_invites_token_hash", table_name="trip_invites")
        if "ix_trip_invites_trip_status" in invite_indexes:
            op.drop_index("ix_trip_invites_trip_status", table_name="trip_invites")
        op.drop_table("trip_invites")
