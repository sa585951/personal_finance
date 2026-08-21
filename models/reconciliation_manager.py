from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, select

from .schema import (
    account_adjustments_table,
    account_balance_anchors_table,
    account_movements_table,
    accounts_table,
    settlement_account_entries_table,
)


ZERO = Decimal("0")


class ReconciliationManager:
    """Read-only Expected Balance reconciliation for tracked accounts."""

    def __init__(self, db_session):
        self.db_session = db_session

    def reconcile(self, *, user_id=None, account_id=None):
        parsed_user_id = self._parse_optional_uuid(user_id, "user_id")
        parsed_account_id = self._parse_optional_uuid(account_id, "account_id")

        stmt = select(accounts_table).where(
            accounts_table.c.track_balance.is_(True),
            accounts_table.c.balance.isnot(None),
            accounts_table.c.deleted_at.is_(None),
        )
        if parsed_user_id:
            stmt = stmt.where(accounts_table.c.user_id == parsed_user_id)
        if parsed_account_id:
            stmt = stmt.where(accounts_table.c.id == parsed_account_id)
        stmt = stmt.order_by(accounts_table.c.user_id, accounts_table.c.currency, accounts_table.c.name)

        reports = [self._reconcile_account(dict(row._mapping)) for row in self.db_session.execute(stmt)]
        return {
            "accounts": reports,
            "summary": {
                "total": len(reports),
                "matched": sum(report["status"] == "matched" for report in reports),
                "mismatched": sum(report["status"] == "mismatch" for report in reports),
                "missing_anchor": sum(report["status"] == "missing_anchor" for report in reports),
            },
        }

    def _reconcile_account(self, account):
        anchor_row = self.db_session.execute(
            select(account_balance_anchors_table)
            .where(account_balance_anchors_table.c.account_id == account["id"])
            .order_by(
                desc(account_balance_anchors_table.c.anchored_at),
                desc(account_balance_anchors_table.c.created_at),
                desc(account_balance_anchors_table.c.id),
            )
            .limit(1)
        ).first()

        base = {
            "account_id": str(account["id"]),
            "user_id": str(account["user_id"]),
            "name": account["name"],
            "type": account["type"],
            "currency": account["currency"],
            "stored_balance": Decimal(str(account["balance"])),
        }
        if not anchor_row:
            return {
                **base,
                "status": "missing_anchor",
                "anchor": None,
                "movements": None,
                "expected_balance": None,
                "difference": None,
            }

        anchor = dict(anchor_row._mapping)
        anchored_at = anchor["anchored_at"]
        movement_totals = self._account_movement_totals(account["id"], anchored_at)
        settlement_totals = self._settlement_totals(account["id"], anchored_at)
        adjustment_totals = self._adjustment_totals(account["id"], anchored_at)

        expected_balance = (
            Decimal(str(anchor["balance"]))
            + movement_totals["amount_delta"]
            + settlement_totals["amount_delta"]
            + adjustment_totals["amount_delta"]
        )
        difference = expected_balance - base["stored_balance"]

        return {
            **base,
            "status": "matched" if difference == ZERO else "mismatch",
            "anchor": {
                "id": str(anchor["id"]),
                "balance": Decimal(str(anchor["balance"])),
                "source": anchor["source"],
                "anchored_at": anchored_at,
            },
            "movements": {
                "transaction": movement_totals["transaction"],
                "transfer": movement_totals["transfer"],
                "settlement": settlement_totals,
                "adjustment": adjustment_totals,
            },
            "expected_balance": expected_balance,
            "difference": difference,
        }

    def _account_movement_totals(self, account_id, anchored_at):
        totals = {
            "amount_delta": ZERO,
            "transaction": {"count": 0, "amount_delta": ZERO},
            "transfer": {"count": 0, "amount_delta": ZERO},
        }
        rows = self.db_session.execute(
            select(
                account_movements_table.c.source_type,
                account_movements_table.c.amount_delta,
            ).where(
                account_movements_table.c.account_id == account_id,
                account_movements_table.c.occurred_at > anchored_at,
            )
        )
        for row in rows:
            amount_delta = Decimal(str(row.amount_delta))
            totals["amount_delta"] += amount_delta
            totals[row.source_type]["count"] += 1
            totals[row.source_type]["amount_delta"] += amount_delta
        return totals

    def _settlement_totals(self, account_id, anchored_at):
        result = {"count": 0, "amount_delta": ZERO}
        rows = self.db_session.execute(
            select(settlement_account_entries_table).where(
                settlement_account_entries_table.c.account_id == account_id,
                (
                    (settlement_account_entries_table.c.posted_at > anchored_at)
                    | (settlement_account_entries_table.c.reversed_at > anchored_at)
                ),
            )
        )
        for row in rows:
            entry = dict(row._mapping)
            amount = Decimal(str(entry["amount"]))
            posting_delta = amount if entry["direction"] == "incoming" else -amount
            if entry["posted_at"] > anchored_at:
                result["count"] += 1
                result["amount_delta"] += posting_delta
            if entry["reversed_at"] and entry["reversed_at"] > anchored_at:
                result["count"] += 1
                result["amount_delta"] -= posting_delta
        return result

    def _adjustment_totals(self, account_id, anchored_at):
        result = {"count": 0, "amount_delta": ZERO}
        rows = self.db_session.execute(
            select(account_adjustments_table.c.amount_delta).where(
                account_adjustments_table.c.account_id == account_id,
                account_adjustments_table.c.adjusted_at > anchored_at,
            )
        )
        for row in rows:
            result["count"] += 1
            result["amount_delta"] += Decimal(str(row.amount_delta))
        return result

    def _parse_optional_uuid(self, value, field_name):
        if value in {None, ""}:
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} 格式不正確") from exc
