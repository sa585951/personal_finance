"""Permanent removal of data for accounts deleted more than 30 days ago.

Scope: only users whose account deletion (AccountPrivacyService.delete_account)
has passed purge_after. Ordinary soft-deleted ledger rows of active users are
not touched here; their audit trail stays.

Method: delete candidate rows children-first, skipping any row still referenced
by data that must stay (another member's shared trip, a settlement, ...), and
repeat until a pass deletes nothing. What remains is anonymised. Re-running is
safe: a second run finds nothing more to delete.
"""
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import exists, or_, select, update

from .account_privacy import DELETED_NAME
from .schema import (
    account_adjustments_table, account_balance_anchors_table, account_movements_table, accounts_table,
    ai_parse_events_table, attachments_table, auth_sessions_table, budgets_table, categories_table,
    credit_card_billing_profiles_table, financial_commands_table, holding_cost_entries_table, holdings_table,
    line_ai_attempts, line_ai_consents, metadata, portfolio_snapshot_items_table, portfolio_snapshots_table,
    portfolios_table, product_events_table, receipt_documents_table, settlement_account_entries_table,
    settlements_table,
    transaction_splits_table, transactions_table, transfers_table, trip_invites_table, trip_members_table,
    trips_table, user_identities_table, users_table,
)

DELETED_ACCOUNT_NAME = "已刪除的帳戶"
MAX_PASSES = 20


class PurgeService:
    def __init__(self, session):
        self.session = session

    def _candidates(self, now):
        users = select(users_table.c.id).where(
            users_table.c.deleted_at.is_not(None), users_table.c.purge_after <= now,
        ).scalar_subquery()
        # Solo trips were soft-deleted with the account; shared trips belong to others.
        trips = select(trips_table.c.id).where(
            trips_table.c.owner_user_id.in_(users), trips_table.c.deleted_at.is_not(None),
        ).scalar_subquery()
        portfolios = select(portfolios_table.c.id).where(portfolios_table.c.user_id.in_(users)).scalar_subquery()
        holdings = select(holdings_table.c.id).where(holdings_table.c.portfolio_id.in_(portfolios)).scalar_subquery()

        def own(table):
            return table.c.user_id.in_(users)

        def own_outside_shared_trips(table):
            return own(table) & or_(table.c.trip_id.is_(None), table.c.trip_id.in_(trips))

        return users, {
            users_table: users_table.c.id.in_(users),
            user_identities_table: own(user_identities_table),
            auth_sessions_table: own(auth_sessions_table),
            line_ai_consents: own(line_ai_consents),
            product_events_table: own(product_events_table),
            ai_parse_events_table: own(ai_parse_events_table),
            financial_commands_table: own(financial_commands_table),
            attachments_table: own(attachments_table),
            receipt_documents_table: own(receipt_documents_table),
            settlement_account_entries_table: own(settlement_account_entries_table),
            account_movements_table: own(account_movements_table),
            account_adjustments_table: own(account_adjustments_table),
            account_balance_anchors_table: own(account_balance_anchors_table),
            credit_card_billing_profiles_table: own(credit_card_billing_profiles_table),
            transactions_table: own_outside_shared_trips(transactions_table) | transactions_table.c.trip_id.in_(trips),
            transaction_splits_table: transaction_splits_table.c.transaction_id.in_(
                select(transactions_table.c.id).where(transactions_table.c.trip_id.in_(trips))),
            transfers_table: own_outside_shared_trips(transfers_table),
            budgets_table: own_outside_shared_trips(budgets_table),
            settlements_table: settlements_table.c.trip_id.in_(trips),
            trip_invites_table: trip_invites_table.c.trip_id.in_(trips),
            trip_members_table: trip_members_table.c.trip_id.in_(trips),
            trips_table: trips_table.c.id.in_(trips),
            portfolio_snapshot_items_table: portfolio_snapshot_items_table.c.holding_id.in_(holdings),
            portfolio_snapshots_table: portfolio_snapshots_table.c.portfolio_id.in_(portfolios),
            holding_cost_entries_table: holding_cost_entries_table.c.holding_id.in_(holdings),
            holdings_table: holdings_table.c.id.in_(holdings),
            portfolios_table: portfolios_table.c.id.in_(portfolios),
            accounts_table: own(accounts_table),
            categories_table: own(categories_table),
        }

    @staticmethod
    def _still_referenced(table):
        """Rows elsewhere that block deleting a row of `table` (cascades excluded)."""
        blockers = []
        for other in metadata.sorted_tables:
            for fk in other.foreign_keys:
                if fk.column.table is not table or (fk.ondelete or "").upper() in {"CASCADE", "SET NULL"}:
                    continue
                child = other.alias() if other is table else other
                blockers.append(exists(select(1).select_from(child).where(
                    child.c[fk.parent.name] == table.c[fk.column.name])))
        return blockers

    def run(self, now=None):
        now = now or datetime.now(timezone.utc)
        users, candidates = self._candidates(now)
        deleted = Counter()
        # Keep spend records for the shared AI budget, without the person.
        self.session.execute(update(line_ai_attempts).where(line_ai_attempts.c.user_id.in_(users))
                             .values(user_id=None))
        order = [table for table in reversed(metadata.sorted_tables) if table in candidates]
        for _ in range(MAX_PASSES):
            progress = 0
            for table in order:
                condition = candidates[table]
                for blocker in self._still_referenced(table):
                    condition = condition & ~blocker
                count = self.session.execute(table.delete().where(condition)).rowcount
                deleted[table.name] += count
                progress += count
            if not progress:
                break
        # Rows other members still rely on keep their ledger meaning but lose names.
        retained_accounts = self.session.execute(update(accounts_table).where(
            accounts_table.c.user_id.in_(users), accounts_table.c.name != DELETED_ACCOUNT_NAME,
        ).values(name=DELETED_ACCOUNT_NAME)).rowcount
        self.session.execute(update(trip_members_table).where(trip_members_table.c.user_id.in_(users))
                             .values(display_name=DELETED_NAME))
        return {"deleted": {name: count for name, count in deleted.items() if count},
                "anonymised_accounts": retained_accounts}
