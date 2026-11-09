"""Permanently remove data of accounts deleted more than 30 days ago.

Dry run by default: everything happens inside a transaction that is rolled
back, and the would-be counts are printed. Pass --apply to commit.

    DATABASE_URL=... python -m scripts.purge_deleted_users            # dry run
    DATABASE_URL=... python -m scripts.purge_deleted_users --apply    # commit

Safe to schedule daily (for example as a Render Cron Job): a run with nothing
due deletes nothing.
"""
import argparse
import json

from models.database import SessionLocal
from models.purge import PurgeService


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="commit the deletion (default: dry run)")
    args = parser.parse_args(argv)
    session = SessionLocal()
    try:
        result = PurgeService(session).run()
        if args.apply:
            session.commit()
        else:
            session.rollback()
        print(json.dumps({"applied": args.apply, **result}, ensure_ascii=False, indent=2))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
