"""Read-only usage overview for the operator, who is identified by NOMICA_ADMIN_LINE_USER_ID.

Shows only who is using the app and how much: join date, last time something was recorded and
record counts. It never returns amounts, titles, notes or any financial content.
"""
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from .schema import transactions_table, user_identities_table, users_table

RECENT_DAYS = 7
USER_LIMIT = 200


def is_admin(session, user_id):
    admin_line_id = (os.getenv("NOMICA_ADMIN_LINE_USER_ID") or "").strip()
    if not admin_line_id:
        return False
    found = session.execute(
        select(user_identities_table.c.id).where(
            user_identities_table.c.user_id == user_id,
            user_identities_table.c.provider == "line",
            user_identities_table.c.provider_user_id == admin_line_id,
        ).limit(1)
    ).first()
    return found is not None


def usage_overview(session, now=None):
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=RECENT_DAYS)
    t = transactions_table
    recorded = (
        select(
            t.c.created_by_user_id.label("user_id"),
            func.count().label("total"),
            func.count().filter(t.c.created_at >= since).label("recent"),
            func.max(t.c.created_at).label("last_at"),
        )
        .where(t.c.deleted_at.is_(None))
        .group_by(t.c.created_by_user_id)
        .subquery()
    )
    rows = session.execute(
        select(users_table.c.id, users_table.c.display_name, users_table.c.created_at,
               recorded.c.total, recorded.c.recent, recorded.c.last_at)
        .select_from(users_table.outerjoin(recorded, recorded.c.user_id == users_table.c.id))
        .where(users_table.c.deleted_at.is_(None))
        .order_by(recorded.c.last_at.desc().nulls_last(), users_table.c.created_at.desc())
        .limit(USER_LIMIT)
    ).all()
    users = [{
        "name": row.display_name,
        "joined_at": row.created_at.isoformat(),
        "last_record_at": row.last_at.isoformat() if row.last_at else None,
        "total_records": int(row.total or 0),
        "recent_records": int(row.recent or 0),
    } for row in rows]
    return {
        "recent_days": RECENT_DAYS,
        "total_users": session.scalar(select(func.count()).select_from(users_table).where(users_table.c.deleted_at.is_(None))),
        "active_users": sum(1 for user in users if user["recent_records"] > 0),
        "users": users,
    }
