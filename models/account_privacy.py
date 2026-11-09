"""S5 minimum: personal data export, account deletion and sign-out everywhere.

Deletion is a soft delete with a 30-day purge window, consistent with the rest of
the ledger. Records other people depend on (shared trip expenses, splits and
settlements) stay for them, but the deleted person's name is anonymised.
"""
import csv
import io
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select, update

from .schema import (
    account_adjustments_table, accounts_table, ai_parse_events_table, auth_sessions_table,
    budgets_table, categories_table, credit_card_billing_profiles_table, line_ai_consents,
    portfolios_table, product_events_table, receipt_documents_table, transactions_table, transfers_table,
    trip_invites_table, trip_members_table, trips_table, user_identities_table, users_table,
)

PURGE_DAYS = 30
DELETE_CONFIRMATION = "刪除我的帳號"
DELETED_NAME = "已刪除的使用者"

# (file name, table, owner column). Only rows the person owns; nothing secret is
# stored in these tables (OAuth and session secrets live elsewhere as hashes).
EXPORTS = (
    ("accounts.csv", accounts_table, "user_id"),
    ("credit_card_billing_profiles.csv", credit_card_billing_profiles_table, "user_id"),
    ("account_adjustments.csv", account_adjustments_table, "user_id"),
    ("transactions.csv", transactions_table, "user_id"),
    ("transfers.csv", transfers_table, "user_id"),
    ("budgets.csv", budgets_table, "user_id"),
    ("categories.csv", categories_table, "user_id"),
    ("portfolios.csv", portfolios_table, "user_id"),
    ("receipt_documents.csv", receipt_documents_table, "user_id"),
    ("trip_memberships.csv", trip_members_table, "user_id"),
    ("ai_parse_events.csv", ai_parse_events_table, "user_id"),
    ("line_ai_consents.csv", line_ai_consents, "user_id"),
    ("usage_events.csv", product_events_table, "user_id"),
)
# Columns never exported even though they belong to the person's rows.
EXCLUDED_COLUMNS = {"token_hash", "qr_secret", "random_code"}


class SharedTripOwnershipError(ValueError):
    def __init__(self, trip_names):
        self.trip_names = trip_names
        super().__init__("仍有其他成員的共享旅行：" + "、".join(trip_names) + "。請先刪除這些旅行或請成員結束使用後再刪除帳號。")


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, (dict, list)):
        import json
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


class AccountPrivacyService:
    def __init__(self, db_session):
        self.db_session = db_session

    # --- export -----------------------------------------------------------
    def export_zip(self, user_id):
        owner = UUID(str(user_id))
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("profile.csv", self._csv(users_table, users_table.c.id == owner))
            archive.writestr("login_methods.csv", self._csv(
                user_identities_table, user_identities_table.c.user_id == owner,
                columns=["provider", "provider_email", "provider_display_name", "created_at"]))
            for name, table, column in EXPORTS:
                condition = table.c[column] == owner
                if "deleted_at" in table.c:
                    condition = and_(condition, table.c.deleted_at.is_(None))
                archive.writestr(name, self._csv(table, condition))
            archive.writestr("README.txt", (
                "Nomica 個人資料匯出\n"
                f"產生時間（UTC）：{datetime.now(timezone.utc).isoformat()}\n"
                "每個 CSV 對應一類資料，金額為原始精度的十進位字串。\n"
                "共享旅行中由其他成員建立的紀錄不在此匯出內。\n"
            ))
        return buffer.getvalue()

    def _csv(self, table, condition, columns=None):
        names = [c for c in (columns or [col.name for col in table.columns]) if c not in EXCLUDED_COLUMNS]
        rows = self.db_session.execute(select(*[table.c[n] for n in names]).where(condition)).all()
        out = io.StringIO()
        # BOM so Excel opens Traditional Chinese correctly.
        out.write("﻿")
        writer = csv.writer(out)
        writer.writerow(names)
        for row in rows:
            writer.writerow([_cell(v) for v in row])
        return out.getvalue()

    # --- sessions ---------------------------------------------------------
    def revoke_all_sessions(self, user_id):
        now = datetime.now(timezone.utc)
        result = self.db_session.execute(
            update(auth_sessions_table)
            .where(auth_sessions_table.c.user_id == UUID(str(user_id)),
                   auth_sessions_table.c.revoked_at.is_(None))
            .values(revoked_at=now, updated_at=now)
        )
        return result.rowcount

    # --- deletion ---------------------------------------------------------
    def delete_account(self, user_id, confirmation):
        if confirmation != DELETE_CONFIRMATION:
            raise ValueError(f"請輸入「{DELETE_CONFIRMATION}」確認刪除")
        owner = UUID(str(user_id))
        now = datetime.now(timezone.utc)
        purge = now + timedelta(days=PURGE_DAYS)
        # Serialize with concurrent writes for this person.
        user = self.db_session.execute(
            select(users_table).where(users_table.c.id == owner, users_table.c.deleted_at.is_(None))
            .with_for_update()
        ).first()
        if not user:
            raise ValueError("帳號不存在或已刪除")

        owned_trips = self.db_session.execute(
            select(trips_table.c.id, trips_table.c.name)
            .where(trips_table.c.owner_user_id == owner, trips_table.c.deleted_at.is_(None))
            .with_for_update()
        ).all()
        others = func.count().filter(and_(trip_members_table.c.user_id != owner,
                                          trip_members_table.c.status == "active",
                                          trip_members_table.c.deleted_at.is_(None)))
        shared, solo = [], []
        for trip in owned_trips:
            count = self.db_session.scalar(select(others).where(trip_members_table.c.trip_id == trip.id))
            (shared if count else solo).append(trip)
        if shared:
            raise SharedTripOwnershipError([t.name for t in shared])

        soft = dict(deleted_at=now, purge_after=purge)
        solo_ids = [t.id for t in solo]
        if solo_ids:
            self.db_session.execute(update(trips_table).where(trips_table.c.id.in_(solo_ids))
                                    .values(updated_at=now, **soft))
            self.db_session.execute(update(transactions_table)
                                    .where(transactions_table.c.trip_id.in_(solo_ids),
                                           transactions_table.c.deleted_at.is_(None))
                                    .values(updated_at=now, deleted_by_user_id=owner, **soft))
            self.db_session.execute(update(trip_invites_table)
                                    .where(trip_invites_table.c.trip_id.in_(solo_ids),
                                           trip_invites_table.c.status == "active")
                                    .values(status="closed", closed_at=now, updated_at=now))

        # Personal ledger (not shared trip records other members still rely on).
        self.db_session.execute(update(transactions_table)
                                .where(transactions_table.c.user_id == owner,
                                       transactions_table.c.trip_id.is_(None),
                                       transactions_table.c.deleted_at.is_(None))
                                .values(updated_at=now, deleted_by_user_id=owner, **soft))
        for table in (accounts_table, transfers_table, budgets_table, categories_table,
                      portfolios_table, receipt_documents_table):
            values = dict(soft)
            if "updated_at" in table.c:
                values["updated_at"] = now
            self.db_session.execute(update(table).where(table.c.user_id == owner, table.c.deleted_at.is_(None))
                                    .values(**values))

        # Memberships in other people's trips: leave, anonymised.
        self.db_session.execute(update(trip_members_table)
                                .where(trip_members_table.c.user_id == owner)
                                .values(display_name=DELETED_NAME, updated_at=now))
        self.db_session.execute(update(trip_members_table)
                                .where(trip_members_table.c.user_id == owner,
                                       trip_members_table.c.status != "removed")
                                .values(status="removed", removed_at=now, updated_at=now, **soft))

        # AI: stop any new provider calls for this person.
        self.db_session.execute(update(line_ai_consents).where(line_ai_consents.c.user_id == owner)
                                .values(consented=False, updated_at=now))

        # Identity: a later LINE login starts a fresh, empty account.
        self.db_session.execute(user_identities_table.delete().where(user_identities_table.c.user_id == owner))
        self.revoke_all_sessions(owner)
        self.db_session.execute(update(users_table).where(users_table.c.id == owner).values(
            display_name=DELETED_NAME, email=None, avatar_url=None, updated_at=now, **soft))
        return {"purge_after": purge.isoformat(), "closed_trips": len(solo_ids)}
