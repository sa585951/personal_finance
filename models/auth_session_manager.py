from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import insert, select, update

from .schema import auth_sessions_table, user_identities_table


class AuthSessionManager:
    """管理可撤銷的登入 session。"""

    def __init__(self, db_session):
        self.db_session = db_session

    def create_session(self, user_id, provider, expires_at):
        stmt = (
            insert(auth_sessions_table)
            .values(
                user_id=self._to_uuid(user_id),
                provider=provider,
                expires_at=expires_at,
                last_used_at=datetime.now(timezone.utc),
            )
            .returning(auth_sessions_table)
        )
        row = self.db_session.execute(stmt).first()
        return dict(row._mapping)

    def validate_session(self, session_id, user_id):
        now = datetime.now(timezone.utc)
        stmt = select(auth_sessions_table).where(
            auth_sessions_table.c.id == self._to_uuid(session_id),
            auth_sessions_table.c.user_id == self._to_uuid(user_id),
        )
        row = self.db_session.execute(stmt).first()
        if not row:
            return None

        session = dict(row._mapping)
        if session.get("revoked_at") is not None:
            return None
        if self._as_aware_datetime(session["expires_at"]) <= now:
            return None

        self.db_session.execute(
            update(auth_sessions_table)
            .where(auth_sessions_table.c.id == session["id"])
            .values(last_used_at=now)
        )
        session["last_used_at"] = now
        return session

    def revoke_session(self, session_id, user_id):
        now = datetime.now(timezone.utc)
        result = self.db_session.execute(
            update(auth_sessions_table)
            .where(
                auth_sessions_table.c.id == self._to_uuid(session_id),
                auth_sessions_table.c.user_id == self._to_uuid(user_id),
                auth_sessions_table.c.revoked_at.is_(None),
            )
            .values(revoked_at=now, updated_at=now)
        )
        return result.rowcount > 0

    def list_user_identities(self, user_id):
        rows = self.db_session.execute(
            select(
                user_identities_table.c.provider,
                user_identities_table.c.provider_email,
                user_identities_table.c.provider_display_name,
                user_identities_table.c.created_at,
            ).where(user_identities_table.c.user_id == self._to_uuid(user_id))
        ).all()
        return [dict(row._mapping) for row in rows]

    def _to_uuid(self, value):
        return value if isinstance(value, UUID) else UUID(str(value))

    def _as_aware_datetime(self, value):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
