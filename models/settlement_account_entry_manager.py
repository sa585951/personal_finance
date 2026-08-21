from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import insert, select, update

from .schema import (
    accounts_table,
    settlement_account_entries_table,
    settlements_table,
    trip_members_table,
)


class SettlementAccountEntryManager:
    """管理使用者自己那一側的 Settlement 私人帳戶 movement。"""

    def __init__(self, db_session):
        self.db_session = db_session

    def create_entry(self, user_id, trip_id, settlement_id, account_id):
        parsed_user_id = self._parse_uuid(user_id, "user_id")
        parsed_trip_id = self._parse_uuid(trip_id, "trip_id")
        parsed_settlement_id = self._parse_uuid(settlement_id, "settlement_id")
        parsed_account_id = self._parse_uuid(account_id, "account_id")

        settlement = self._get_settlement_context(
            parsed_user_id,
            parsed_trip_id,
            parsed_settlement_id,
            for_update=True,
        )
        existing = self._get_entry(parsed_user_id, parsed_settlement_id)
        if existing:
            if existing["status"] == "posted" and existing["account_id"] == str(parsed_account_id):
                existing["replayed"] = True
                return existing
            if existing["status"] == "reversed":
                raise ValueError("這筆私人帳戶入帳已反轉，不能再次入帳")
            raise ValueError("這筆結算已記入其他帳戶；請先取消原入帳")

        account = self._get_account(parsed_user_id, parsed_account_id, for_update=True)
        self._validate_account(account, settlement["currency"])

        direction, member_id = self._resolve_user_side(settlement, parsed_user_id)
        amount = Decimal(str(settlement["amount"]))
        balance_before = Decimal(str(account["balance"]))
        delta = amount if direction == "incoming" else -amount
        balance_after = balance_before + delta
        if balance_after < 0 and account["type"] != "credit_card":
            raise ValueError("帳戶餘額不足，無法記錄這筆付款")

        now = datetime.now(timezone.utc)
        entry_id = self.db_session.execute(
            insert(settlement_account_entries_table)
            .values(
                settlement_id=parsed_settlement_id,
                user_id=parsed_user_id,
                trip_member_id=member_id,
                account_id=parsed_account_id,
                direction=direction,
                amount=amount,
                currency=settlement["currency"],
                status="posted",
                balance_before=balance_before,
                balance_after=balance_after,
                posted_at=now,
            )
            .returning(settlement_account_entries_table.c.id)
        ).scalar_one()
        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == parsed_account_id)
            .values(balance=balance_after, updated_at=now)
        )

        entry = self._get_entry(parsed_user_id, parsed_settlement_id, entry_id=entry_id)
        entry["replayed"] = False
        return entry

    def reverse_entry(self, user_id, trip_id, settlement_id, reason=None):
        parsed_user_id = self._parse_uuid(user_id, "user_id")
        parsed_trip_id = self._parse_uuid(trip_id, "trip_id")
        parsed_settlement_id = self._parse_uuid(settlement_id, "settlement_id")
        self._get_settlement_context(
            parsed_user_id,
            parsed_trip_id,
            parsed_settlement_id,
            require_confirmed=False,
            require_active_member=False,
        )

        row = self.db_session.execute(
            select(settlement_account_entries_table)
            .where(
                settlement_account_entries_table.c.settlement_id == parsed_settlement_id,
                settlement_account_entries_table.c.user_id == parsed_user_id,
            )
            .with_for_update()
        ).first()
        if not row:
            raise ValueError("這筆結算尚未記入你的帳戶")

        entry = dict(row._mapping)
        if entry["status"] == "reversed":
            replayed = self._serialize_entry(entry)
            replayed["account_name"] = self._get_account_name(entry["account_id"])
            replayed["replayed"] = True
            return replayed

        account = self._get_account(parsed_user_id, entry["account_id"], for_update=True, include_deleted=True)
        if not account or not account["track_balance"] or account["balance"] is None:
            raise ValueError("原帳戶目前無法追蹤餘額，不能反轉此入帳")

        amount = Decimal(str(entry["amount"]))
        reversal_balance_before = Decimal(str(account["balance"]))
        reversal_delta = -amount if entry["direction"] == "incoming" else amount
        reversal_balance_after = reversal_balance_before + reversal_delta
        if reversal_balance_after < 0 and account["type"] != "credit_card":
            raise ValueError("帳戶餘額不足，無法取消這筆收款入帳")

        now = datetime.now(timezone.utc)
        normalized_reason = str(reason or "使用者取消私人帳戶入帳").strip()[:500]
        self.db_session.execute(
            update(settlement_account_entries_table)
            .where(
                settlement_account_entries_table.c.id == entry["id"],
                settlement_account_entries_table.c.status == "posted",
            )
            .values(
                status="reversed",
                reversal_balance_before=reversal_balance_before,
                reversal_balance_after=reversal_balance_after,
                reversed_at=now,
                reversed_by_user_id=parsed_user_id,
                reversal_reason=normalized_reason or None,
                updated_at=now,
            )
        )
        self.db_session.execute(
            update(accounts_table)
            .where(accounts_table.c.id == account["id"])
            .values(balance=reversal_balance_after, updated_at=now)
        )

        reversed_entry = self._get_entry(parsed_user_id, parsed_settlement_id)
        reversed_entry["replayed"] = False
        return reversed_entry

    def _get_settlement_context(
        self,
        user_id,
        trip_id,
        settlement_id,
        *,
        for_update=False,
        require_confirmed=True,
        require_active_member=True,
    ):
        from_member = trip_members_table.alias("settlement_from_member")
        to_member = trip_members_table.alias("settlement_to_member")
        filters = [
            settlements_table.c.id == settlement_id,
            settlements_table.c.trip_id == trip_id,
        ]
        if require_confirmed:
            filters.extend([
                settlements_table.c.status == "confirmed",
                settlements_table.c.deleted_at.is_(None),
            ])

        stmt = (
            select(
                settlements_table.c.id,
                settlements_table.c.trip_id,
                settlements_table.c.from_member_id,
                settlements_table.c.to_member_id,
                settlements_table.c.amount,
                settlements_table.c.currency,
                settlements_table.c.status,
                from_member.c.user_id.label("from_user_id"),
                to_member.c.user_id.label("to_user_id"),
            )
            .join(from_member, settlements_table.c.from_member_id == from_member.c.id)
            .join(to_member, settlements_table.c.to_member_id == to_member.c.id)
            .where(*filters)
        )
        if for_update:
            stmt = stmt.with_for_update(of=settlements_table)
        row = self.db_session.execute(stmt).first()
        if not row:
            raise ValueError("找不到可入帳的結算紀錄")

        settlement = dict(row._mapping)
        if user_id not in {settlement["from_user_id"], settlement["to_user_id"]}:
            raise ValueError("你不是這筆結算的付款方或收款方")

        if require_active_member:
            active_member = self.db_session.execute(
                select(trip_members_table.c.id).where(
                    trip_members_table.c.trip_id == trip_id,
                    trip_members_table.c.user_id == user_id,
                    trip_members_table.c.status == "active",
                    trip_members_table.c.deleted_at.is_(None),
                )
            ).scalar_one_or_none()
            if not active_member:
                raise ValueError("你目前不是此旅行的有效成員")
        return settlement

    def _resolve_user_side(self, settlement, user_id):
        if settlement["from_user_id"] == user_id:
            return "outgoing", settlement["from_member_id"]
        if settlement["to_user_id"] == user_id:
            return "incoming", settlement["to_member_id"]
        raise ValueError("你不是這筆結算的付款方或收款方")

    def _get_account(self, user_id, account_id, *, for_update=False, include_deleted=False):
        stmt = select(accounts_table).where(
            accounts_table.c.id == account_id,
            accounts_table.c.user_id == user_id,
        )
        if not include_deleted:
            stmt = stmt.where(
                accounts_table.c.deleted_at.is_(None),
                accounts_table.c.is_active.is_(True),
            )
        if for_update:
            stmt = stmt.with_for_update()
        row = self.db_session.execute(stmt).first()
        return dict(row._mapping) if row else None

    def _validate_account(self, account, currency):
        if not account:
            raise ValueError("找不到帳戶或權限不足")
        if not account["track_balance"] or account["balance"] is None:
            raise ValueError("此帳戶未啟用餘額追蹤")
        if account["currency"] != currency:
            raise ValueError("帳戶幣別必須與結算幣別相同")

    def _get_entry(self, user_id, settlement_id, entry_id=None):
        stmt = (
            select(
                settlement_account_entries_table,
                accounts_table.c.name.label("account_name"),
            )
            .join(accounts_table, settlement_account_entries_table.c.account_id == accounts_table.c.id)
            .where(
                settlement_account_entries_table.c.user_id == user_id,
                settlement_account_entries_table.c.settlement_id == settlement_id,
            )
        )
        if entry_id:
            stmt = stmt.where(settlement_account_entries_table.c.id == entry_id)
        row = self.db_session.execute(stmt).first()
        if not row:
            return None
        entry = dict(row._mapping)
        serialized = self._serialize_entry(entry)
        serialized["account_name"] = entry["account_name"]
        return serialized

    def _get_account_name(self, account_id):
        return self.db_session.execute(
            select(accounts_table.c.name).where(accounts_table.c.id == account_id)
        ).scalar_one_or_none()

    def _serialize_entry(self, entry):
        return {
            "id": str(entry["id"]),
            "settlement_id": str(entry["settlement_id"]),
            "user_id": str(entry["user_id"]),
            "trip_member_id": str(entry["trip_member_id"]),
            "account_id": str(entry["account_id"]),
            "direction": entry["direction"],
            "amount": float(entry["amount"]),
            "currency": entry["currency"],
            "status": entry["status"],
            "balance_before": float(entry["balance_before"]),
            "balance_after": float(entry["balance_after"]),
            "posted_at": entry["posted_at"].isoformat() if entry.get("posted_at") else None,
            "reversal_balance_before": (
                float(entry["reversal_balance_before"])
                if entry.get("reversal_balance_before") is not None
                else None
            ),
            "reversal_balance_after": (
                float(entry["reversal_balance_after"])
                if entry.get("reversal_balance_after") is not None
                else None
            ),
            "reversed_at": entry["reversed_at"].isoformat() if entry.get("reversed_at") else None,
            "reversal_reason": entry.get("reversal_reason"),
        }

    def _parse_uuid(self, value, field_name):
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} 格式不正確") from exc
