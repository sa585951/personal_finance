from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()
legacy_metadata = MetaData()

UUID_PK = dict(
    primary_key=True,
    server_default=text("gen_random_uuid()"),
)

AMOUNT = Numeric(18, 4)
RATE = Numeric(18, 8)


currencies_table = Table(
    "currencies",
    metadata,
    Column("code", String(3), primary_key=True),
    Column("name", String(100), nullable=False),
    Column("symbol", String(10), nullable=False),
    Column("minor_unit", Integer, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint("minor_unit >= 0", name="ck_currencies_minor_unit_non_negative"),
)


users_table = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("display_name", String(255), nullable=False),
    Column("email", String(255)),
    Column("avatar_url", Text),
    Column("locale", String(20), nullable=False, server_default=text("'zh-TW'")),
    Column("timezone", String(64), nullable=False, server_default=text("'Asia/Taipei'")),
    Column("base_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
)


user_identities_table = Table(
    "user_identities",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("provider", String(50), nullable=False),
    Column("provider_user_id", String(255), nullable=False),
    Column("provider_email", String(255)),
    Column("provider_display_name", String(255)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    UniqueConstraint("provider", "provider_user_id", name="uq_user_identities_provider_user"),
)


auth_sessions_table = Table(
    "auth_sessions",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("provider", String(50), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
    Column("last_used_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
)

Index("ix_auth_sessions_user_active", auth_sessions_table.c.user_id, auth_sessions_table.c.revoked_at)


accounts_table = Table(
    "accounts",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("type", String(50), nullable=False),
    Column("currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("track_balance", Boolean, nullable=False, server_default=text("true")),
    Column("balance", AMOUNT),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("archived_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint(
        "type in ('cash', 'bank', 'credit_card', 'e_wallet', 'prepaid_card', 'external', 'investment', 'other')",
        name="ck_accounts_type",
    ),
)


categories_table = Table(
    "categories",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")),
    Column("parent_id", UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT")),
    Column("kind", String(20), nullable=False),
    Column("scope", String(50), nullable=False, server_default=text("'transaction'")),
    Column("code", String(100), nullable=False),
    Column("name", String(100), nullable=False),
    Column("icon", String(100)),
    Column("color", String(20)),
    Column("is_system", Boolean, nullable=False, server_default=text("false")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("sort_order", Integer, nullable=False, server_default=text("0")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint("kind in ('expense', 'income', 'both')", name="ck_categories_kind"),
)


trips_table = Table(
    "trips",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("owner_user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("name", String(255), nullable=False),
    Column("destination", String(255)),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("timezone", String(64), nullable=False),
    Column("base_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("default_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("status", String(20), nullable=False, server_default=text("'active'")),
    Column("include_in_monthly_report", Boolean, nullable=False, server_default=text("false")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    Column("archived_at", DateTime(timezone=True)),
    CheckConstraint("end_date >= start_date", name="ck_trips_date_range"),
    CheckConstraint("status in ('active', 'archived')", name="ck_trips_status"),
)


trip_members_table = Table(
    "trip_members",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("trip_id", UUID(as_uuid=True), ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")),
    Column("display_name", String(255), nullable=False),
    Column("role", String(20), nullable=False),
    Column("status", String(20), nullable=False, server_default=text("'active'")),
    Column("monthly_report_preference", String(20)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("removed_at", DateTime(timezone=True)),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint("role in ('owner', 'editor', 'viewer')", name="ck_trip_members_role"),
    CheckConstraint("status in ('active', 'invited', 'removed')", name="ck_trip_members_status"),
    CheckConstraint(
        "monthly_report_preference in ('pending', 'include', 'exclude')",
        name="ck_trip_members_monthly_report_preference",
    ),
)

trip_invites_table = Table(
    "trip_invites",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("trip_id", UUID(as_uuid=True), ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False),
    Column("created_by_user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("token_hash", String(128), nullable=False),
    Column("role", String(20), nullable=False, server_default=text("'editor'")),
    Column("status", String(20), nullable=False, server_default=text("'active'")),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("closed_at", DateTime(timezone=True)),
    CheckConstraint("role in ('editor', 'viewer')", name="ck_trip_invites_role"),
    CheckConstraint("status in ('active', 'closed')", name="ck_trip_invites_status"),
)


transactions_table = Table(
    "transactions",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("created_by_user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("updated_by_user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")),
    Column("deleted_by_user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")),
    Column("trip_id", UUID(as_uuid=True), ForeignKey("trips.id", ondelete="RESTRICT")),
    Column("account_id", UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT")),
    Column("category_id", UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
    Column("paid_by_member_id", UUID(as_uuid=True), ForeignKey("trip_members.id", ondelete="RESTRICT")),
    Column("transaction_date", Date, nullable=False),
    Column("transaction_time", Time),
    Column("timezone", String(64), nullable=False),
    Column("type", String(20), nullable=False),
    Column("merchant", String(255)),
    Column("title", String(255), nullable=False),
    Column("description", Text),
    Column("original_amount", AMOUNT, nullable=False),
    Column("original_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("exchange_rate", RATE, nullable=False),
    Column("converted_amount", AMOUNT, nullable=False),
    Column("base_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    Column("voided_at", DateTime(timezone=True)),
    Column("void_reason", Text),
    Column("review_status", String(20), nullable=False, server_default=text("'confirmed'")),
    CheckConstraint("type in ('expense', 'income', 'transfer', 'adjustment')", name="ck_transactions_type"),
    CheckConstraint("original_amount >= 0", name="ck_transactions_original_amount_non_negative"),
    CheckConstraint("exchange_rate > 0", name="ck_transactions_exchange_rate_positive"),
    CheckConstraint("converted_amount >= 0", name="ck_transactions_converted_amount_non_negative"),
    CheckConstraint("review_status in ('pending', 'confirmed')", name="ck_transactions_review_status"),
)


transaction_splits_table = Table(
    "transaction_splits",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("transaction_id", UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
    Column("trip_member_id", UUID(as_uuid=True), ForeignKey("trip_members.id", ondelete="RESTRICT"), nullable=False),
    Column("split_method", String(20), nullable=False, server_default=text("'equal'")),
    Column("share_amount", AMOUNT, nullable=False),
    Column("share_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("exchange_rate", RATE, nullable=False),
    Column("converted_share_amount", AMOUNT, nullable=False),
    Column("base_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint("split_method in ('equal', 'custom')", name="ck_transaction_splits_method"),
    CheckConstraint("share_amount >= 0", name="ck_transaction_splits_share_amount_non_negative"),
    CheckConstraint("exchange_rate > 0", name="ck_transaction_splits_exchange_rate_positive"),
    CheckConstraint(
        "converted_share_amount >= 0",
        name="ck_transaction_splits_converted_share_amount_non_negative",
    ),
)


transfers_table = Table(
    "transfers",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("trip_id", UUID(as_uuid=True), ForeignKey("trips.id", ondelete="RESTRICT")),
    Column("source_account_id", UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
    Column("target_account_id", UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
    Column("source_amount", AMOUNT, nullable=False),
    Column("source_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("target_amount", AMOUNT, nullable=False),
    Column("target_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("target_per_source_rate", RATE, nullable=False),
    Column("fee_amount", AMOUNT),
    Column("fee_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT")),
    Column("transfer_date", Date, nullable=False),
    Column("note", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint("source_account_id <> target_account_id", name="ck_transfers_different_accounts"),
    CheckConstraint("source_amount > 0", name="ck_transfers_source_amount_positive"),
    CheckConstraint("target_amount > 0", name="ck_transfers_target_amount_positive"),
    CheckConstraint("target_per_source_rate > 0", name="ck_transfers_rate_positive"),
)


portfolios_table = Table(
    "portfolios",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("base_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("archived_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint("char_length(trim(name)) > 0", name="ck_portfolios_name_not_blank"),
)


holdings_table = Table(
    "holdings",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("portfolio_id", UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False),
    Column("account_id", UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("symbol", String(50)),
    Column("asset_class", String(50)),
    Column("target_weight", Numeric(9, 8)),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("archived_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint("char_length(trim(name)) > 0", name="ck_holdings_name_not_blank"),
    CheckConstraint(
        "target_weight IS NULL OR (target_weight >= 0 AND target_weight <= 1)",
        name="ck_holdings_target_weight_range",
    ),
)


holding_cost_entries_table = Table(
    "holding_cost_entries",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("holding_id", UUID(as_uuid=True), ForeignKey("holdings.id", ondelete="RESTRICT"), nullable=False),
    Column("source_transfer_id", UUID(as_uuid=True), ForeignKey("transfers.id", ondelete="RESTRICT")),
    Column("entry_type", String(30), nullable=False),
    Column("amount", AMOUNT, nullable=False),
    Column("currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("occurred_on", Date, nullable=False),
    Column("note", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint(
        "entry_type in ('transfer', 'manual_adjustment')",
        name="ck_holding_cost_entries_type",
    ),
    CheckConstraint("amount > 0", name="ck_holding_cost_entries_amount_positive"),
    CheckConstraint(
        "(entry_type = 'transfer' AND source_transfer_id IS NOT NULL) OR "
        "(entry_type = 'manual_adjustment' AND source_transfer_id IS NULL)",
        name="ck_holding_cost_entries_source",
    ),
)


portfolio_snapshots_table = Table(
    "portfolio_snapshots",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("portfolio_id", UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False),
    Column("snapshot_date", Date, nullable=False),
    Column("currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("note", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
)


portfolio_snapshot_items_table = Table(
    "portfolio_snapshot_items",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column(
        "snapshot_id",
        UUID(as_uuid=True),
        ForeignKey("portfolio_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("holding_id", UUID(as_uuid=True), ForeignKey("holdings.id", ondelete="RESTRICT"), nullable=False),
    Column("value", AMOUNT, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    UniqueConstraint("snapshot_id", "holding_id", name="uq_portfolio_snapshot_items_holding"),
    CheckConstraint("value >= 0", name="ck_portfolio_snapshot_items_value_non_negative"),
)


settlements_table = Table(
    "settlements",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("trip_id", UUID(as_uuid=True), ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False),
    Column("from_member_id", UUID(as_uuid=True), ForeignKey("trip_members.id", ondelete="RESTRICT"), nullable=False),
    Column("to_member_id", UUID(as_uuid=True), ForeignKey("trip_members.id", ondelete="RESTRICT"), nullable=False),
    Column("recorded_by_user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("amount", AMOUNT, nullable=False),
    Column("currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("status", String(20), nullable=False, server_default=text("'confirmed'")),
    Column("note", Text),
    Column("settled_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint("from_member_id <> to_member_id", name="ck_settlements_different_members"),
    CheckConstraint("amount > 0", name="ck_settlements_amount_positive"),
    CheckConstraint("status in ('confirmed', 'voided')", name="ck_settlements_status"),
)


budgets_table = Table(
    "budgets",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("trip_id", UUID(as_uuid=True), ForeignKey("trips.id", ondelete="RESTRICT")),
    Column("scope", String(20), nullable=False),
    Column("period_start", Date, nullable=False),
    Column("period_end", Date, nullable=False),
    Column("category_id", UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT")),
    Column("amount", AMOUNT, nullable=False),
    Column("currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("notes", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint("scope in ('monthly', 'trip')", name="ck_budgets_scope"),
    CheckConstraint("period_end >= period_start", name="ck_budgets_period_range"),
    CheckConstraint("amount > 0", name="ck_budgets_amount_positive"),
)


exchange_rates_table = Table(
    "exchange_rates",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("from_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("to_currency", String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False),
    Column("rate", RATE, nullable=False),
    Column("rate_date", Date, nullable=False),
    Column("source", String(100), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    UniqueConstraint("from_currency", "to_currency", "rate_date", "source", name="uq_exchange_rates_source_date"),
    CheckConstraint("from_currency <> to_currency", name="ck_exchange_rates_different_currencies"),
    CheckConstraint("rate > 0", name="ck_exchange_rates_rate_positive"),
)


ai_parse_events_table = Table(
    "ai_parse_events",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("source", String(50), nullable=False),
    Column("raw_input", Text, nullable=False),
    Column("parsed_payload", JSONB),
    Column("confidence", Numeric(5, 4)),
    Column("status", String(20), nullable=False),
    Column("result_type", String(50)),
    Column("result_id", UUID(as_uuid=True)),
    Column("error_message", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint("source in ('line_bot', 'web', 'pwa', 'ios')", name="ck_ai_parse_events_source"),
    CheckConstraint("status in ('success', 'failed', 'confirmed', 'cancelled')", name="ck_ai_parse_events_status"),
)


attachments_table = Table(
    "attachments",
    metadata,
    Column("id", UUID(as_uuid=True), **UUID_PK),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("entity_type", String(50), nullable=False),
    Column("entity_id", UUID(as_uuid=True), nullable=False),
    Column("file_url", Text, nullable=False),
    Column("file_type", String(100)),
    Column("file_name", String(255)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("deleted_at", DateTime(timezone=True)),
    Column("purge_after", DateTime(timezone=True)),
    CheckConstraint("entity_type in ('transaction', 'trip', 'transfer')", name="ck_attachments_entity_type"),
)


Index("ix_user_identities_user_id", user_identities_table.c.user_id)
Index("ix_accounts_user_id", accounts_table.c.user_id)
Index("ix_categories_user_parent_kind_scope_code", categories_table.c.user_id, categories_table.c.parent_id, categories_table.c.kind, categories_table.c.scope, categories_table.c.code)
Index("ix_trips_owner_status", trips_table.c.owner_user_id, trips_table.c.status)
Index("ix_trip_members_trip_status", trip_members_table.c.trip_id, trip_members_table.c.status)
Index("ix_trip_members_user_status", trip_members_table.c.user_id, trip_members_table.c.status)
Index("ix_trip_invites_trip_status", trip_invites_table.c.trip_id, trip_invites_table.c.status)
Index("ix_trip_invites_token_hash", trip_invites_table.c.token_hash, unique=True)
Index("ix_transactions_user_date", transactions_table.c.user_id, transactions_table.c.transaction_date)
Index("ix_transactions_user_trip_date", transactions_table.c.user_id, transactions_table.c.trip_id, transactions_table.c.transaction_date)
Index("ix_transactions_user_category_date", transactions_table.c.user_id, transactions_table.c.category_id, transactions_table.c.transaction_date)
Index("ix_transactions_user_account_date", transactions_table.c.user_id, transactions_table.c.account_id, transactions_table.c.transaction_date)
Index("ix_transactions_created_by_date", transactions_table.c.created_by_user_id, transactions_table.c.transaction_date)
Index("ix_transactions_trip_date", transactions_table.c.trip_id, transactions_table.c.transaction_date)
Index("ix_transaction_splits_transaction", transaction_splits_table.c.transaction_id)
Index("ix_transaction_splits_member", transaction_splits_table.c.trip_member_id)
Index("ix_transfers_user_date", transfers_table.c.user_id, transfers_table.c.transfer_date)
Index("ix_transfers_user_trip_date", transfers_table.c.user_id, transfers_table.c.trip_id, transfers_table.c.transfer_date)
Index("ix_portfolios_user_active", portfolios_table.c.user_id, portfolios_table.c.is_active)
Index("ix_holdings_portfolio_active", holdings_table.c.portfolio_id, holdings_table.c.is_active)
Index("ix_holdings_account", holdings_table.c.account_id)
Index(
    "ix_holding_cost_entries_holding_date",
    holding_cost_entries_table.c.holding_id,
    holding_cost_entries_table.c.occurred_on,
)
Index("ix_holding_cost_entries_transfer", holding_cost_entries_table.c.source_transfer_id)
Index(
    "ix_portfolio_snapshots_portfolio_date",
    portfolio_snapshots_table.c.portfolio_id,
    portfolio_snapshots_table.c.snapshot_date,
)
Index("ix_portfolio_snapshot_items_snapshot", portfolio_snapshot_items_table.c.snapshot_id)
Index("ix_settlements_trip_status", settlements_table.c.trip_id, settlements_table.c.status)
Index("ix_settlements_from_member", settlements_table.c.from_member_id)
Index("ix_settlements_to_member", settlements_table.c.to_member_id)
Index("ix_budgets_user_scope_period", budgets_table.c.user_id, budgets_table.c.scope, budgets_table.c.period_start, budgets_table.c.period_end)
Index("ix_budgets_trip_scope", budgets_table.c.trip_id, budgets_table.c.scope)
Index("ix_ai_parse_events_user_created", ai_parse_events_table.c.user_id, ai_parse_events_table.c.created_at)
Index("ix_ai_parse_events_source_status_created", ai_parse_events_table.c.source, ai_parse_events_table.c.status, ai_parse_events_table.c.created_at)
Index("ix_attachments_entity", attachments_table.c.entity_type, attachments_table.c.entity_id)

Index(
    "uq_categories_system_root_code",
    categories_table.c.kind,
    categories_table.c.scope,
    categories_table.c.code,
    unique=True,
    postgresql_where=categories_table.c.user_id.is_(None) & categories_table.c.parent_id.is_(None),
)
Index(
    "uq_categories_user_root_code",
    categories_table.c.user_id,
    categories_table.c.kind,
    categories_table.c.scope,
    categories_table.c.code,
    unique=True,
    postgresql_where=categories_table.c.user_id.isnot(None) & categories_table.c.parent_id.is_(None),
)
Index(
    "uq_categories_system_child_code",
    categories_table.c.parent_id,
    categories_table.c.kind,
    categories_table.c.scope,
    categories_table.c.code,
    unique=True,
    postgresql_where=categories_table.c.user_id.is_(None) & categories_table.c.parent_id.isnot(None),
)
Index(
    "uq_categories_user_child_code",
    categories_table.c.user_id,
    categories_table.c.parent_id,
    categories_table.c.kind,
    categories_table.c.scope,
    categories_table.c.code,
    unique=True,
    postgresql_where=categories_table.c.user_id.isnot(None) & categories_table.c.parent_id.isnot(None),
)

Index(
    "uq_budgets_user_monthly_category",
    budgets_table.c.user_id,
    budgets_table.c.scope,
    budgets_table.c.period_start,
    budgets_table.c.period_end,
    budgets_table.c.category_id,
    unique=True,
    postgresql_where=budgets_table.c.trip_id.is_(None) & budgets_table.c.category_id.isnot(None),
)
Index(
    "uq_budgets_trip_total",
    budgets_table.c.trip_id,
    budgets_table.c.scope,
    budgets_table.c.period_start,
    budgets_table.c.period_end,
    unique=True,
    postgresql_where=budgets_table.c.trip_id.isnot(None) & budgets_table.c.category_id.is_(None),
)

Index(
    "uq_trip_invites_one_active",
    trip_invites_table.c.trip_id,
    unique=True,
    postgresql_where=trip_invites_table.c.status == "active",
)

Index(
    "uq_portfolios_user_currency_name_active",
    portfolios_table.c.user_id,
    portfolios_table.c.base_currency,
    portfolios_table.c.name,
    unique=True,
    postgresql_where=portfolios_table.c.deleted_at.is_(None),
)
Index(
    "uq_holdings_portfolio_account_name_active",
    holdings_table.c.portfolio_id,
    holdings_table.c.account_id,
    holdings_table.c.name,
    unique=True,
    postgresql_where=holdings_table.c.deleted_at.is_(None),
)
Index(
    "uq_holding_cost_entries_holding_transfer_active",
    holding_cost_entries_table.c.holding_id,
    holding_cost_entries_table.c.source_transfer_id,
    unique=True,
    postgresql_where=holding_cost_entries_table.c.deleted_at.is_(None)
    & holding_cost_entries_table.c.source_transfer_id.isnot(None),
)
Index(
    "uq_portfolio_snapshots_portfolio_date_active",
    portfolio_snapshots_table.c.portfolio_id,
    portfolio_snapshots_table.c.snapshot_date,
    unique=True,
    postgresql_where=portfolio_snapshots_table.c.deleted_at.is_(None),
)


# Legacy table definitions kept outside the Alembic target metadata so the
# current API/manager layer can still import during the schema migration phase.
# These tables are not created by the new migration and should be removed once
# the API layer is migrated to the new MVP schema.
assets_table = Table(
    "assets",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", String(255), nullable=False, index=True),
    Column("account_key", String, unique=True, nullable=False),
    Column("bank_name", String(100), nullable=False),
    Column("account_type", String(100), nullable=False),
    Column("balance", Numeric(15, 2), nullable=False),
    Column("last_update", DateTime),
    Column("currency", String(10)),
)

budget_months_table = Table(
    "budget_months",
    legacy_metadata,
    Column("user_id", String(255), primary_key=True),
    Column("month", String(7), primary_key=True),
    Column("created_date", DateTime),
)

budget_categories_table = Table(
    "budget_categories",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", String(255), nullable=False, index=True),
    Column("month", String(7), nullable=False),
    Column("category_name", String(100), nullable=False),
    Column("amount", Numeric(10, 2), nullable=False),
    Column("notes", Text),
    Column("created_date", DateTime),
    UniqueConstraint("user_id", "month", "category_name", name="uq_user_month_category"),
)

goals_table = Table(
    "goals",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", String(255), nullable=False, index=True),
    Column("title", String(255), nullable=False),
    Column("type", String(50)),
    Column("target_amount", Numeric(10, 2), nullable=False),
    Column("target_date", Date),
    Column("current_amount", Numeric(10, 2), default=0),
    Column("created_date", DateTime),
    Column("last_update", DateTime),
    Column("status", String(50)),
    Column("description", Text),
)
