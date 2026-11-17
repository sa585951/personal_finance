"""A plain, human-readable Excel export of the person's own ledger.

The full data export (`AccountPrivacyService.export_zip`) stays as the data-portability
copy. This workbook is the everyday one: names instead of ids, no internal columns, and
only what the person recorded themselves. Rows other members created in a shared trip
are not included, and neither are the person's typed sentences.
"""
import io
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from sqlalchemy import or_, select

from .schema import (
    accounts_table, budgets_table, categories_table, transactions_table, transfers_table,
    trip_members_table, trips_table,
)

TYPE_LABELS = {"expense": "支出", "income": "收入"}
ACCOUNT_TYPE_LABELS = {
    "cash": "現金", "bank": "銀行帳戶", "credit_card": "信用卡", "e_wallet": "電子錢包",
    "prepaid_card": "預付卡", "external": "外部帳戶", "investment": "投資", "other": "其他",
}
BUDGET_SCOPE_LABELS = {"monthly": "每月", "trip": "旅行"}
TRIP_STATUS_LABELS = {"active": "進行中", "archived": "已封存"}
ROLE_LABELS = {"owner": "建立者", "editor": "可編輯", "viewer": "僅檢視"}
MONEY_FORMAT = "#,##0.00"

SHEETS = ("交易明細", "帳戶", "轉帳", "預算", "旅行")


def _number(value):
    return float(value) if isinstance(value, Decimal) else value


def _put(sheet, row_values):
    """Append a row. Text is always stored as text so a value like "=SUM(A1)" never runs."""
    sheet.append([_number(v) for v in row_values])
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"
        elif isinstance(cell.value, float):
            cell.number_format = MONEY_FORMAT
        elif isinstance(cell.value, datetime):
            cell.number_format = "yyyy-mm-dd hh:mm"
        elif isinstance(cell.value, date):
            cell.number_format = "yyyy-mm-dd"
        elif isinstance(cell.value, time):
            cell.number_format = "hh:mm"


def _finish(sheet):
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(vertical="center")
    sheet.freeze_panes = "A2"
    for index, column in enumerate(sheet.columns, start=1):
        longest = max((len(str(c.value)) for c in column if c.value is not None), default=0)
        sheet.column_dimensions[get_column_letter(index)].width = min(max(longest + 2, 8), 40)


def _names(db_session, table, ids, column="name"):
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = db_session.execute(select(table.c.id, table.c[column]).where(table.c.id.in_(ids))).all()
    return {row[0]: row[1] for row in rows}


def build_workbook(db_session, user_id):
    owner = UUID(str(user_id))

    transactions = db_session.execute(
        select(transactions_table).where(
            transactions_table.c.user_id == owner,
            transactions_table.c.deleted_at.is_(None),
            transactions_table.c.voided_at.is_(None),
            transactions_table.c.type.in_(tuple(TYPE_LABELS)),
        ).order_by(transactions_table.c.transaction_date, transactions_table.c.transaction_time,
                   transactions_table.c.created_at)
    ).mappings().all()
    transfers = db_session.execute(
        select(transfers_table).where(transfers_table.c.user_id == owner, transfers_table.c.deleted_at.is_(None))
        .order_by(transfers_table.c.transfer_date, transfers_table.c.created_at)
    ).mappings().all()
    budgets = db_session.execute(
        select(budgets_table).where(budgets_table.c.user_id == owner, budgets_table.c.deleted_at.is_(None))
        .order_by(budgets_table.c.period_start, budgets_table.c.created_at)
    ).mappings().all()
    # Accounts include deleted ones only so old rows can still show a name.
    all_accounts = db_session.execute(
        select(accounts_table).where(accounts_table.c.user_id == owner)
        .order_by(accounts_table.c.created_at)
    ).mappings().all()
    account_names = {a["id"]: a["name"] for a in all_accounts}

    member_trip_ids = select(trip_members_table.c.trip_id).where(
        trip_members_table.c.user_id == owner,
        trip_members_table.c.status == "active",
        trip_members_table.c.deleted_at.is_(None),
    )
    trips = db_session.execute(
        select(trips_table).where(
            trips_table.c.deleted_at.is_(None),
            or_(trips_table.c.owner_user_id == owner, trips_table.c.id.in_(member_trip_ids)),
        ).order_by(trips_table.c.start_date, trips_table.c.created_at)
    ).mappings().all()
    roles = {
        row.trip_id: row.role for row in db_session.execute(
            select(trip_members_table.c.trip_id, trip_members_table.c.role).where(
                trip_members_table.c.user_id == owner, trip_members_table.c.deleted_at.is_(None))
        ).all()
    }
    trip_names = {t["id"]: t["name"] for t in trips}
    referenced = {r["trip_id"] for r in (*transactions, *transfers, *budgets) if r["trip_id"]}
    trip_names.update(_names(db_session, trips_table, referenced - set(trip_names)))
    category_names = _names(db_session, categories_table,
                            {r["category_id"] for r in (*transactions, *budgets)})

    book = Workbook()
    sheet = book.active
    sheet.title = SHEETS[0]
    sheet.append(["日期", "時間", "類型", "分類", "項目", "商家", "帳戶", "金額", "幣別",
                  "折合金額", "折合幣別", "旅行", "備註", "狀態"])
    for row in transactions:
        _put(sheet, [
            row["transaction_date"], row["transaction_time"], TYPE_LABELS[row["type"]],
            category_names.get(row["category_id"], ""), row["title"] or "", row["merchant"] or "",
            account_names.get(row["account_id"], ""), row["original_amount"], row["original_currency"],
            row["converted_amount"], row["base_currency"], trip_names.get(row["trip_id"], ""),
            row["description"] or "", "待確認" if row["review_status"] == "pending" else "",
        ])
    _finish(sheet)

    sheet = book.create_sheet(SHEETS[1])
    sheet.append(["名稱", "類型", "幣別", "餘額", "狀態"])
    for account in all_accounts:
        if account["deleted_at"] is not None:
            continue
        _put(sheet, [
            account["name"], ACCOUNT_TYPE_LABELS.get(account["type"], account["type"]), account["currency"],
            account["balance"] if account["track_balance"] else None,
            "已封存" if account["archived_at"] or not account["is_active"] else "使用中",
        ])
    _finish(sheet)

    sheet = book.create_sheet(SHEETS[2])
    sheet.append(["日期", "轉出帳戶", "轉入帳戶", "轉出金額", "轉出幣別", "轉入金額", "轉入幣別",
                  "手續費", "手續費幣別", "旅行", "備註"])
    for row in transfers:
        _put(sheet, [
            row["transfer_date"], account_names.get(row["source_account_id"], ""),
            account_names.get(row["target_account_id"], ""), row["source_amount"], row["source_currency"],
            row["target_amount"], row["target_currency"], row["fee_amount"] or None,
            row["fee_currency"] or "", trip_names.get(row["trip_id"], ""), row["note"] or "",
        ])
    _finish(sheet)

    sheet = book.create_sheet(SHEETS[3])
    sheet.append(["範圍", "開始日", "結束日", "分類", "旅行", "金額", "幣別", "備註"])
    for row in budgets:
        _put(sheet, [
            BUDGET_SCOPE_LABELS.get(row["scope"], row["scope"]), row["period_start"], row["period_end"],
            category_names.get(row["category_id"], "整體"), trip_names.get(row["trip_id"], ""),
            row["amount"], row["currency"], row["notes"] or "",
        ])
    _finish(sheet)

    sheet = book.create_sheet(SHEETS[4])
    sheet.append(["名稱", "目的地", "開始日", "結束日", "幣別", "狀態", "我的角色"])
    for trip in trips:
        role = "owner" if trip["owner_user_id"] == owner else roles.get(trip["id"], "editor")
        _put(sheet, [
            trip["name"], trip["destination"] or "", trip["start_date"], trip["end_date"],
            trip["base_currency"], TRIP_STATUS_LABELS.get(trip["status"], trip["status"]),
            ROLE_LABELS.get(role, role),
        ])
    _finish(sheet)

    out = io.BytesIO()
    book.save(out)
    return out.getvalue()
