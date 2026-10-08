"""Add receipt documents without changing existing financial records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20261008_0016"
down_revision = "20260925_0015"
branch_labels = None
depends_on = None


def upgrade():
    # Initial migration creates current metadata; checkfirst supports that path.
    bind = op.get_bind()
    if "receipt_documents" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "receipt_documents",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("invoice_number", sa.String(10), nullable=False),
            sa.Column("issued_on", sa.Date(), nullable=False),
            sa.Column("seller_identifier", sa.String(8), nullable=False),
            sa.Column("total_amount", sa.Numeric(18, 4), nullable=False),
            sa.Column("currency", sa.String(3), sa.ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
            sa.Column("merchant_name", sa.String(255)),
            sa.Column("transaction_id", UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("first_source", sa.String(20), nullable=False),
            sa.Column("last_source", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
            sa.Column("purge_after", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("user_id", "invoice_number", "issued_on", "seller_identifier", name="uq_receipt_identity"),
            sa.CheckConstraint("total_amount > 0", name="ck_receipt_amount"),
            sa.CheckConstraint("status in ('pending', 'linked', 'ignored')", name="ck_receipt_status"),
            sa.CheckConstraint("(status = 'linked') = (transaction_id is not null)", name="ck_receipt_link"),
            sa.CheckConstraint("first_source in ('qr_camera', 'qr_image', 'carrier')", name="ck_receipt_first_source"),
            sa.CheckConstraint("last_source in ('qr_camera', 'qr_image', 'carrier')", name="ck_receipt_last_source"),
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("receipt_documents")}
    if "ix_receipts_user_date" not in indexes:
        op.create_index("ix_receipts_user_date", "receipt_documents", ["user_id", "issued_on"])


def downgrade():
    if "receipt_documents" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("receipt_documents")
