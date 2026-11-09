"""Read-only weekly beta numbers, computed from the database.

    DATABASE_URL=... python -m scripts.beta_metrics            # last 4 weeks
    DATABASE_URL=... python -m scripts.beta_metrics --weeks 8

Weeks start on Monday, Asia/Taipei. Prints counts only, never entry text.
"""
import argparse
import json
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select

from models.database import SessionLocal
from models.schema import (
    ai_parse_events_table, line_ai_attempts, product_events_table, transactions_table, trip_members_table,
    users_table,
)

TZ = ZoneInfo("Asia/Taipei")


def _week_bounds(weeks):
    today = datetime.now(TZ).date()
    monday = today - timedelta(days=today.weekday())
    for back in range(weeks - 1, -1, -1):
        start = monday - timedelta(weeks=back)
        yield start, datetime.combine(start, time(), TZ), datetime.combine(start + timedelta(days=7), time(), TZ)


def weekly(session, start, end):
    tx = transactions_table
    local_day = func.date(func.timezone("Asia/Taipei", tx.c.created_at))
    days = session.execute(
        select(tx.c.created_by_user_id, func.count(func.distinct(local_day)))
        .where(tx.c.created_at >= start, tx.c.created_at < end, tx.c.deleted_at.is_(None))
        .group_by(tx.c.created_by_user_id)
    ).all()
    per_user_days = sorted((count for _, count in days), reverse=True)

    ev = ai_parse_events_table
    in_week = and_(ev.c.created_at >= start, ev.c.created_at < end)
    web_confirmed = session.scalar(select(func.count()).where(in_week, ev.c.source == "web", ev.c.status == "confirmed"))
    web_unchanged = session.scalar(select(func.count()).where(
        in_week, ev.c.source == "web", ev.c.status == "confirmed", ev.c.confirmed_unchanged.is_(True)))
    line_status = dict(session.execute(
        select(ev.c.status, func.count()).where(in_week, ev.c.source == "line_bot").group_by(ev.c.status)).all())

    tm, u = trip_members_table, users_table
    joined = session.execute(
        select(tm.c.user_id, tm.c.created_at, u.c.created_at.label("user_created"))
        .join(u, u.c.id == tm.c.user_id)
        .where(tm.c.created_at >= start, tm.c.created_at < end, tm.c.role != "owner", tm.c.user_id.is_not(None))
    ).all()
    # A person who joined a trip within a day of creating their account came in through the invite.
    new_via_invite = len({row.user_id for row in joined if row.created_at - row.user_created < timedelta(days=1)})

    pe = product_events_table
    home = dict(session.execute(
        select(func.coalesce(pe.c.props["target"].astext, pe.c.name), func.count())
        .where(pe.c.created_at >= start, pe.c.created_at < end)
        .group_by(func.coalesce(pe.c.props["target"].astext, pe.c.name))).all())

    return {
        "active_people": len(per_user_days),
        "people_with_2plus_days": sum(1 for count in per_user_days if count >= 2),
        "entry_days_per_person": per_user_days,
        "web_sentence_confirmed": web_confirmed,
        "web_sentence_unchanged_ratio": round(web_unchanged / web_confirmed, 2) if web_confirmed else None,
        "line_drafts": line_status,
        "trip_joins": len(joined),
        "new_people_via_trip_invite": new_via_invite,
        "home_events": home,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--weeks", type=int, default=4)
    args = parser.parse_args(argv)
    session = SessionLocal()
    try:
        report = {start.isoformat(): weekly(session, lo, hi) for start, lo, hi in _week_bounds(args.weeks)}
        month = date.today().replace(day=1)
        report["line_ai_usd_this_month"] = str(session.scalar(
            select(func.coalesce(func.sum(line_ai_attempts.c.charge_usd), 0)).where(line_ai_attempts.c.month == month)))
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    finally:
        session.rollback()
        session.close()


if __name__ == "__main__":
    main()
