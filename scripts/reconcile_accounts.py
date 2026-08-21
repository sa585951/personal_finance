import argparse
import json
from datetime import date, datetime
from decimal import Decimal

from models.database import SessionLocal
from models.reconciliation_manager import ReconciliationManager


def _json_default(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _money(value):
    return "-" if value is None else format(value, ",.4f")


def _print_text_report(report):
    print("Nomica account reconciliation (read-only)")
    print("difference = expected_balance - stored_balance")
    print()
    for account in report["accounts"]:
        print(f"[{account['status'].upper()}] {account['name']} ({account['currency']})")
        print(f"  account_id: {account['account_id']}")
        if not account["anchor"]:
            print(f"  stored: {_money(account['stored_balance'])}; anchor: missing")
            print()
            continue
        movements = account["movements"]
        print(
            "  anchor: "
            f"{_money(account['anchor']['balance'])} at {account['anchor']['anchored_at'].isoformat()} "
            f"({account['anchor']['source']})"
        )
        print(
            "  deltas: "
            f"transaction={_money(movements['transaction']['amount_delta'])}, "
            f"transfer={_money(movements['transfer']['amount_delta'])}, "
            f"settlement={_money(movements['settlement']['amount_delta'])}, "
            f"adjustment={_money(movements['adjustment']['amount_delta'])}"
        )
        print(
            f"  expected: {_money(account['expected_balance'])}; "
            f"stored: {_money(account['stored_balance'])}; "
            f"difference: {_money(account['difference'])}"
        )
        print()

    summary = report["summary"]
    print(
        "Summary: "
        f"total={summary['total']}, matched={summary['matched']}, "
        f"mismatched={summary['mismatched']}, missing_anchor={summary['missing_anchor']}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Read-only comparison of Nomica Expected Balance and stored account balance."
    )
    parser.add_argument("--user-id", help="Only reconcile one Nomica user UUID.")
    parser.add_argument("--account-id", help="Only reconcile one account UUID.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit 1 when a mismatch or missing anchor is found.",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        report = ReconciliationManager(session).reconcile(
            user_id=args.user_id,
            account_id=args.account_id,
        )
    finally:
        session.close()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
    else:
        _print_text_report(report)

    has_issues = report["summary"]["mismatched"] or report["summary"]["missing_anchor"]
    return 1 if args.fail_on_issues and has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
