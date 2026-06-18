import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, func, insert, or_, select, update

from .schema import (
    settlements_table,
    transaction_splits_table,
    transactions_table,
    trip_invites_table,
    trip_members_table,
    trips_table,
    users_table,
)


class TripManager:
    """管理旅行帳本與旅伴。"""

    MONTHLY_REPORT_PREFERENCES = {"pending", "include", "exclude"}

    def __init__(self, db_session):
        self.db_session = db_session

    def _parse_uuid(self, value, field_name):
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} 格式不正確") from exc

    def _parse_user_id(self, user_id):
        return self._parse_uuid(user_id, "user_id")

    def _parse_date(self, value, field_name):
        if isinstance(value, date):
            return value
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} 必須是 YYYY-MM-DD") from exc

    def _get_user_display_name(self, user_id):
        stmt = select(users_table.c.display_name).where(users_table.c.id == user_id)
        return self.db_session.execute(stmt).scalar_one_or_none() or "我"

    def _normalize_monthly_report_preference(self, value):
        if value not in self.MONTHLY_REPORT_PREFERENCES:
            raise ValueError("monthly_report_preference 僅支援 pending、include 或 exclude")
        return value

    def _preference_from_legacy_flag(self, include_in_monthly_report):
        return "include" if include_in_monthly_report else "exclude"

    def _hash_invite_token(self, token):
        return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

    def _to_trip_dict(self, row):
        trip = dict(row)
        trip["id"] = str(trip["id"])
        trip["owner_user_id"] = str(trip["owner_user_id"])
        trip["start_date"] = trip["start_date"].isoformat()
        trip["end_date"] = trip["end_date"].isoformat()
        for key in ["created_at", "updated_at", "deleted_at", "purge_after", "archived_at"]:
            if trip.get(key):
                trip[key] = trip[key].isoformat()
        return trip

    def _to_member_dict(self, row):
        member = dict(row)
        member["id"] = str(member["id"])
        member["trip_id"] = str(member["trip_id"])
        member["user_id"] = str(member["user_id"]) if member["user_id"] else None
        for key in ["created_at", "updated_at", "removed_at", "deleted_at", "purge_after"]:
            if member.get(key):
                member[key] = member[key].isoformat()
        return member

    def _to_invite_dict(self, row, token=None):
        invite = dict(row)
        invite["id"] = str(invite["id"])
        invite["trip_id"] = str(invite["trip_id"])
        invite["created_by_user_id"] = str(invite["created_by_user_id"])
        for key in ["expires_at", "created_at", "updated_at", "closed_at"]:
            if invite.get(key):
                invite[key] = invite[key].isoformat()
        if token:
            invite["token"] = token
        invite.pop("token_hash", None)
        return invite

    def _ensure_trip_access(self, user_id, trip_id, include_deleted=False):
        parsed_user_id = self._parse_user_id(user_id)
        parsed_trip_id = self._parse_uuid(trip_id, "trip_id")
        member_trip_ids = select(trip_members_table.c.trip_id).where(
            trip_members_table.c.user_id == parsed_user_id,
            trip_members_table.c.status == "active",
            trip_members_table.c.deleted_at.is_(None),
        )
        conditions = [
            trips_table.c.id == parsed_trip_id,
            or_(
                trips_table.c.owner_user_id == parsed_user_id,
                trips_table.c.id.in_(member_trip_ids),
            ),
        ]
        if not include_deleted:
            conditions.append(trips_table.c.deleted_at.is_(None))

        stmt = select(trips_table).where(
            *conditions
        )
        row = self.db_session.execute(stmt).first()
        if not row:
            raise ValueError("找不到旅行或權限不足")
        return dict(row._mapping)

    def _get_current_member(self, user_id, trip_id):
        parsed_user_id = self._parse_user_id(user_id)
        parsed_trip_id = self._parse_uuid(trip_id, "trip_id")
        row = self.db_session.execute(
            select(trip_members_table).where(
                trip_members_table.c.trip_id == parsed_trip_id,
                trip_members_table.c.user_id == parsed_user_id,
                trip_members_table.c.status == "active",
                trip_members_table.c.deleted_at.is_(None),
            )
        ).first()
        return dict(row._mapping) if row else None

    def get_current_member(self, user_id, trip_id):
        self._ensure_trip_access(user_id, trip_id)
        member = self._get_current_member(user_id, trip_id)
        return self._to_member_dict(member) if member else None

    def _ensure_owner(self, user_id, trip_id, include_deleted=False):
        trip = self._ensure_trip_access(user_id, trip_id, include_deleted=include_deleted)
        if trip["owner_user_id"] != self._parse_user_id(user_id):
            raise ValueError("只有旅行 owner 可以執行此操作")
        return trip

    def _active_member_count(self, trip_id):
        return self.db_session.execute(
            select(func.count()).where(
                trip_members_table.c.trip_id == trip_id,
                trip_members_table.c.status == "active",
                trip_members_table.c.deleted_at.is_(None),
            )
        ).scalar_one()

    def list_trips(self, user_id, include_archived=False, include_deleted=False):
        parsed_user_id = self._parse_user_id(user_id)
        member_trip_ids = select(trip_members_table.c.trip_id).where(
            trip_members_table.c.user_id == parsed_user_id,
            trip_members_table.c.status == "active",
            trip_members_table.c.deleted_at.is_(None),
        )
        conditions = [
            or_(
                trips_table.c.owner_user_id == parsed_user_id,
                trips_table.c.id.in_(member_trip_ids),
            ),
        ]
        if not include_deleted:
            conditions.append(trips_table.c.deleted_at.is_(None))

        stmt = (
            select(trips_table)
            .where(*conditions)
            .order_by(trips_table.c.start_date.desc(), trips_table.c.created_at.desc())
        )
        if not include_archived:
            stmt = stmt.where(trips_table.c.status == "active")

        trips = []
        for row in self.db_session.execute(stmt):
            trip = self._to_trip_dict(row._mapping)
            members = self._list_trip_members_for_trip(trip["id"])
            current_member = next(
                (member for member in members if member.get("user_id") == str(parsed_user_id)),
                None,
            )
            trips.append({
                **trip,
                "members": members,
                "current_member_id": current_member["id"] if current_member else None,
            })
        return trips

    def get_trip(self, user_id, trip_id):
        trip = self._ensure_trip_access(user_id, trip_id)
        members = self._list_trip_members_for_trip(trip["id"])
        parsed_user_id = self._parse_user_id(user_id)
        current_member = next(
            (member for member in members if member.get("user_id") == str(parsed_user_id)),
            None,
        )
        return {
            **self._to_trip_dict(trip),
            "members": members,
            "current_member_id": current_member["id"] if current_member else None,
        }

    def _list_trip_members_for_trip(self, trip_id):
        stmt = (
            select(trip_members_table)
            .where(
                trip_members_table.c.trip_id == trip_id,
                trip_members_table.c.deleted_at.is_(None),
            )
            .order_by(trip_members_table.c.created_at)
        )
        return [self._to_member_dict(row._mapping) for row in self.db_session.execute(stmt)]

    def create_trip(
        self,
        user_id,
        name,
        start_date,
        end_date,
        destination=None,
        timezone_name="Asia/Taipei",
        base_currency="TWD",
        default_currency="TWD",
        include_in_monthly_report=False,
    ):
        parsed_user_id = self._parse_user_id(user_id)
        if not str(name).strip():
            raise ValueError("旅行名稱不可為空")
        parsed_start_date = self._parse_date(start_date, "start_date")
        parsed_end_date = self._parse_date(end_date, "end_date")
        if parsed_end_date < parsed_start_date:
            raise ValueError("end_date 不可早於 start_date")

        trip_row = self.db_session.execute(
            insert(trips_table)
            .values(
                owner_user_id=parsed_user_id,
                name=str(name).strip(),
                destination=destination,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                timezone=timezone_name,
                base_currency=base_currency,
                default_currency=default_currency,
                include_in_monthly_report=include_in_monthly_report,
            )
            .returning(trips_table)
        ).first()
        trip = dict(trip_row._mapping)

        self.db_session.execute(
            insert(trip_members_table).values(
                trip_id=trip["id"],
                user_id=parsed_user_id,
                display_name=self._get_user_display_name(parsed_user_id),
                role="owner",
                status="active",
                monthly_report_preference=self._preference_from_legacy_flag(include_in_monthly_report),
            )
        )
        return self.get_trip(parsed_user_id, trip["id"])

    def update_trip(self, user_id, trip_id, include_in_monthly_report=None):
        trip = self._ensure_owner(user_id, trip_id)
        parsed_user_id = self._parse_user_id(user_id)
        values = {}
        member_preference = None
        if include_in_monthly_report is not None:
            include_flag = bool(include_in_monthly_report)
            values["include_in_monthly_report"] = include_flag
            member_preference = self._preference_from_legacy_flag(include_flag)

        if not values:
            raise ValueError("缺少可更新欄位")

        values["updated_at"] = datetime.now(timezone.utc)
        self.db_session.execute(
            update(trips_table)
            .where(trips_table.c.id == trip["id"])
            .values(**values)
        )
        if member_preference is not None:
            self.db_session.execute(
                update(trip_members_table)
                .where(
                    and_(
                        trip_members_table.c.trip_id == trip["id"],
                        trip_members_table.c.user_id == parsed_user_id,
                        trip_members_table.c.status == "active",
                        trip_members_table.c.deleted_at.is_(None),
                    )
                )
                .values(
                    monthly_report_preference=member_preference,
                    updated_at=datetime.now(timezone.utc),
                )
            )
        return self.get_trip(user_id, trip["id"])

    def list_trip_members(self, user_id, trip_id):
        trip = self._ensure_trip_access(user_id, trip_id)
        return self._list_trip_members_for_trip(trip["id"])

    def update_current_member_monthly_report_preference(self, user_id, trip_id, preference):
        trip = self._ensure_trip_access(user_id, trip_id)
        parsed_user_id = self._parse_user_id(user_id)
        normalized_preference = self._normalize_monthly_report_preference(preference)
        member = self._get_current_member(parsed_user_id, trip["id"])
        if not member or member["user_id"] is None:
            raise ValueError("找不到可更新的登入旅伴")

        row = self.db_session.execute(
            update(trip_members_table)
            .where(trip_members_table.c.id == member["id"])
            .values(
                monthly_report_preference=normalized_preference,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(trip_members_table)
        ).first()

        return {
            "trip": self.get_trip(parsed_user_id, trip["id"]),
            "member": self._to_member_dict(row._mapping),
        }

    def add_external_member(self, user_id, trip_id, display_name, role="viewer"):
        trip = self._ensure_trip_access(user_id, trip_id)
        if trip["owner_user_id"] != self._parse_user_id(user_id):
            raise ValueError("只有旅行 owner 可以新增旅伴")
        if not str(display_name).strip():
            raise ValueError("旅伴名稱不可為空")
        if role not in {"editor", "viewer"}:
            raise ValueError("外部旅伴 role 僅支援 editor 或 viewer")

        row = self.db_session.execute(
            insert(trip_members_table)
            .values(
                trip_id=trip["id"],
                user_id=None,
                display_name=str(display_name).strip(),
                role=role,
                status="active",
                monthly_report_preference=None,
            )
            .returning(trip_members_table)
        ).first()
        return self._to_member_dict(row._mapping)

    def update_member_role(self, user_id, trip_id, member_id, role):
        trip = self._ensure_owner(user_id, trip_id)
        if role not in {"editor", "viewer"}:
            raise ValueError("role 僅支援 editor 或 viewer")

        parsed_member_id = self._parse_uuid(member_id, "member_id")
        member_row = self.db_session.execute(
            select(trip_members_table).where(
                trip_members_table.c.id == parsed_member_id,
                trip_members_table.c.trip_id == trip["id"],
                trip_members_table.c.deleted_at.is_(None),
            )
        ).first()
        if not member_row:
            raise ValueError("找不到旅伴")
        member = dict(member_row._mapping)
        if member["role"] == "owner":
            raise ValueError("不能調整旅行 owner 權限")

        row = self.db_session.execute(
            update(trip_members_table)
            .where(trip_members_table.c.id == parsed_member_id)
            .values(role=role, updated_at=datetime.now(timezone.utc))
            .returning(trip_members_table)
        ).first()
        return self._to_member_dict(row._mapping)

    def leave_trip(self, user_id, trip_id):
        trip = self._ensure_trip_access(user_id, trip_id)
        parsed_user_id = self._parse_user_id(user_id)
        if trip["owner_user_id"] == parsed_user_id:
            raise ValueError("旅行 owner 不可退出自己的帳本")

        member = self._get_current_member(parsed_user_id, trip["id"])
        if not member:
            raise ValueError("找不到目前使用者在此旅行中的 member")

        now = datetime.now(timezone.utc)
        row = self.db_session.execute(
            update(trip_members_table)
            .where(trip_members_table.c.id == member["id"])
            .values(
                status="removed",
                removed_at=now,
                deleted_at=now,
                purge_after=now + timedelta(days=30),
                updated_at=now,
            )
            .returning(trip_members_table)
        ).first()
        return self._to_member_dict(row._mapping)

    def get_active_invite(self, user_id, trip_id):
        trip = self._ensure_owner(user_id, trip_id)
        row = self.db_session.execute(
            select(trip_invites_table).where(
                trip_invites_table.c.trip_id == trip["id"],
                trip_invites_table.c.status == "active",
            )
        ).first()
        return self._to_invite_dict(row._mapping) if row else None

    def create_invite(self, user_id, trip_id, role="editor", expires_in_days=30):
        trip = self._ensure_owner(user_id, trip_id)
        if role not in {"editor", "viewer"}:
            raise ValueError("邀請 role 僅支援 editor 或 viewer")

        existing = self.db_session.execute(
            select(trip_invites_table.c.id).where(
                trip_invites_table.c.trip_id == trip["id"],
                trip_invites_table.c.status == "active",
            )
        ).first()
        if existing:
            raise ValueError("此旅行已有有效邀請連結，請先關閉後再重新產生")

        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        row = self.db_session.execute(
            insert(trip_invites_table)
            .values(
                trip_id=trip["id"],
                created_by_user_id=self._parse_user_id(user_id),
                token_hash=self._hash_invite_token(token),
                role=role,
                status="active",
                expires_at=now + timedelta(days=expires_in_days),
            )
            .returning(trip_invites_table)
        ).first()
        return self._to_invite_dict(row._mapping, token=token)

    def close_invite(self, user_id, trip_id):
        trip = self._ensure_owner(user_id, trip_id)
        now = datetime.now(timezone.utc)
        row = self.db_session.execute(
            update(trip_invites_table)
            .where(
                trip_invites_table.c.trip_id == trip["id"],
                trip_invites_table.c.status == "active",
            )
            .values(status="closed", closed_at=now, updated_at=now)
            .returning(trip_invites_table)
        ).first()
        if not row:
            raise ValueError("找不到有效邀請連結")
        return self._to_invite_dict(row._mapping)

    def accept_invite(self, user_id, token, member_limit=15):
        parsed_user_id = self._parse_user_id(user_id)
        token_hash = self._hash_invite_token(token)
        invite_row = self.db_session.execute(
            select(
                trip_invites_table.c.id.label("invite_id"),
                trip_invites_table.c.trip_id.label("invite_trip_id"),
                trip_invites_table.c.created_by_user_id.label("invite_created_by_user_id"),
                trip_invites_table.c.token_hash,
                trip_invites_table.c.role.label("invite_role"),
                trip_invites_table.c.status.label("invite_status"),
                trip_invites_table.c.expires_at,
                trips_table.c.id.label("trip_id"),
                trips_table.c.status.label("trip_status"),
                trips_table.c.deleted_at.label("trip_deleted_at"),
            )
            .join(trips_table, trip_invites_table.c.trip_id == trips_table.c.id)
            .where(trip_invites_table.c.token_hash == token_hash)
        ).first()
        if not invite_row:
            raise ValueError("邀請連結不存在或已失效")

        invite = dict(invite_row._mapping)
        now = datetime.now(timezone.utc)
        if invite["invite_status"] != "active":
            raise ValueError("邀請連結已關閉")
        if invite["expires_at"] <= now:
            raise ValueError("邀請連結已過期")
        if invite["trip_deleted_at"] is not None or invite["trip_status"] != "active":
            raise ValueError("旅行帳本目前不可加入")

        existing_member_row = self.db_session.execute(
            select(trip_members_table).where(
                trip_members_table.c.trip_id == invite["trip_id"],
                trip_members_table.c.user_id == parsed_user_id,
            )
        ).first()
        if existing_member_row:
            existing_member = dict(existing_member_row._mapping)
            if existing_member["status"] == "active" and existing_member["deleted_at"] is None:
                return {
                    "trip": self.get_trip(parsed_user_id, invite["trip_id"]),
                    "member": self._to_member_dict(existing_member),
                    "already_joined": True,
                }

        if self._active_member_count(invite["trip_id"]) >= member_limit:
            raise ValueError("旅行帳本成員已達上限")

        if existing_member_row:
            row = self.db_session.execute(
                update(trip_members_table)
                .where(trip_members_table.c.id == existing_member["id"])
                .values(
                    role=existing_member["role"] if existing_member["role"] == "owner" else invite["invite_role"],
                    status="active",
                    monthly_report_preference=existing_member["monthly_report_preference"] or "pending",
                    removed_at=None,
                    deleted_at=None,
                    purge_after=None,
                    updated_at=now,
                )
                .returning(trip_members_table)
            ).first()
            member = self._to_member_dict(row._mapping)
        else:
            row = self.db_session.execute(
                insert(trip_members_table)
                .values(
                    trip_id=invite["trip_id"],
                    user_id=parsed_user_id,
                    display_name=self._get_user_display_name(parsed_user_id),
                    role=invite["invite_role"],
                    status="active",
                    monthly_report_preference="pending",
                )
                .returning(trip_members_table)
            ).first()
            member = self._to_member_dict(row._mapping)

        return {
            "trip": self.get_trip(parsed_user_id, invite["trip_id"]),
            "member": member,
            "already_joined": False,
        }

    def remove_member(self, user_id, trip_id, member_id):
        trip = self._ensure_trip_access(user_id, trip_id)
        parsed_user_id = self._parse_user_id(user_id)
        if trip["owner_user_id"] != parsed_user_id:
            raise ValueError("只有旅行 owner 可以刪除旅伴")

        parsed_member_id = self._parse_uuid(member_id, "member_id")
        member_row = self.db_session.execute(
            select(trip_members_table).where(
                trip_members_table.c.id == parsed_member_id,
                trip_members_table.c.trip_id == trip["id"],
                trip_members_table.c.deleted_at.is_(None),
            )
        ).first()
        if not member_row:
            raise ValueError("找不到旅伴")

        member = dict(member_row._mapping)
        if member["role"] == "owner":
            raise ValueError("不能刪除旅行 owner")

        has_references = any(
            self.db_session.execute(stmt).first()
            for stmt in [
                select(transactions_table.c.id).where(
                    transactions_table.c.trip_id == trip["id"],
                    transactions_table.c.paid_by_member_id == parsed_member_id,
                    transactions_table.c.deleted_at.is_(None),
                ).limit(1),
                select(transaction_splits_table.c.id)
                .join(transactions_table, transaction_splits_table.c.transaction_id == transactions_table.c.id)
                .where(
                    transactions_table.c.trip_id == trip["id"],
                    transaction_splits_table.c.trip_member_id == parsed_member_id,
                    transactions_table.c.deleted_at.is_(None),
                )
                .limit(1),
                select(settlements_table.c.id).where(
                    settlements_table.c.trip_id == trip["id"],
                    or_(
                        settlements_table.c.from_member_id == parsed_member_id,
                        settlements_table.c.to_member_id == parsed_member_id,
                    ),
                    settlements_table.c.deleted_at.is_(None),
                ).limit(1),
            ]
        )
        if has_references:
            raise ValueError("此旅伴已有付款、分攤或結算紀錄，暫時不能刪除")

        now = datetime.now(timezone.utc)
        row = self.db_session.execute(
            update(trip_members_table)
            .where(trip_members_table.c.id == parsed_member_id)
            .values(
                status="removed",
                removed_at=now,
                deleted_at=now,
                purge_after=now + timedelta(days=30),
                updated_at=now,
            )
            .returning(trip_members_table)
        ).first()
        return self._to_member_dict(row._mapping)

    def archive_trip(self, user_id, trip_id):
        trip = self._ensure_trip_access(user_id, trip_id)
        if trip["owner_user_id"] != self._parse_user_id(user_id):
            raise ValueError("只有旅行 owner 可以封存旅行")

        now = datetime.now(timezone.utc)
        row = self.db_session.execute(
            update(trips_table)
            .where(trips_table.c.id == trip["id"])
            .values(status="archived", archived_at=now, updated_at=now)
            .returning(trips_table)
        ).first()
        return self._to_trip_dict(row._mapping)

    def unarchive_trip(self, user_id, trip_id):
        trip = self._ensure_trip_access(user_id, trip_id)
        if trip["owner_user_id"] != self._parse_user_id(user_id):
            raise ValueError("只有旅行 owner 可以解除封存旅行")

        now = datetime.now(timezone.utc)
        row = self.db_session.execute(
            update(trips_table)
            .where(trips_table.c.id == trip["id"])
            .values(status="active", archived_at=None, updated_at=now)
            .returning(trips_table)
        ).first()
        return self._to_trip_dict(row._mapping)

    def delete_trip(self, user_id, trip_id):
        trip = self._ensure_trip_access(user_id, trip_id)
        if trip["owner_user_id"] != self._parse_user_id(user_id):
            raise ValueError("只有旅行 owner 可以刪除旅行")

        now = datetime.now(timezone.utc)
        row = self.db_session.execute(
            update(trips_table)
            .where(trips_table.c.id == trip["id"])
            .values(deleted_at=now, purge_after=now + timedelta(days=30), updated_at=now)
            .returning(trips_table)
        ).first()
        return self._to_trip_dict(row._mapping)

    def restore_trip(self, user_id, trip_id):
        trip = self._ensure_trip_access(user_id, trip_id, include_deleted=True)
        if trip["owner_user_id"] != self._parse_user_id(user_id):
            raise ValueError("只有旅行 owner 可以復原旅行")
        if not trip.get("deleted_at"):
            return self._to_trip_dict(trip)

        now = datetime.now(timezone.utc)
        row = self.db_session.execute(
            update(trips_table)
            .where(trips_table.c.id == trip["id"])
            .values(deleted_at=None, purge_after=None, updated_at=now)
            .returning(trips_table)
        ).first()
        return self._to_trip_dict(row._mapping)
