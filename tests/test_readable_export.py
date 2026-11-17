"""The everyday Excel export: readable names, only the person's own records."""
import io

from openpyxl import load_workbook
import pytest
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from models.account_privacy import AccountPrivacyService
from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.readable_export import SHEETS, build_workbook
from models.user_manager import UserManager
from tests.test_ai_parse_api import _load_web_app
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def _sheet(blob, name):
    book = load_workbook(io.BytesIO(blob))
    rows = list(book[name].iter_rows(values_only=True))
    header, body = rows[0], rows[1:]
    return [dict(zip(header, row)) for row in body]


def test_workbook_has_the_expected_sheets_and_readable_names(command_db):
    engine, data = command_db
    with Session(engine) as s:
        blob = build_workbook(s, data["a"])
    assert tuple(load_workbook(io.BytesIO(blob)).sheetnames) == SHEETS
    [dinner] = _sheet(blob, "交易明細")
    assert dinner["項目"] == "Dinner"
    assert dinner["類型"] == "支出"
    assert dinner["分類"] == "伙食"
    assert dinner["旅行"] == "Commands"
    assert dinner["金額"] == 1000
    assert {a["名稱"] for a in _sheet(blob, "帳戶")} == {"cash", "bank"}
    # No raw ids or internal columns in any sheet.
    book = load_workbook(io.BytesIO(blob))
    headers = {cell.value for sheet in book for cell in sheet[1]}
    assert not {h for h in headers if h and (h.endswith("_id") or h in {"purge_after", "client_request_id"})}


def test_member_sees_the_trip_but_not_other_peoples_records(command_db):
    engine, data = command_db
    with Session(engine) as s:
        blob = build_workbook(s, data["b"])
    assert _sheet(blob, "交易明細") == []
    assert [t["名稱"] for t in _sheet(blob, "旅行")] == ["Commands"]
    assert [t["我的角色"] for t in _sheet(blob, "旅行")] == ["可編輯"]
    assert {a["名稱"] for a in _sheet(blob, "帳戶")} == {"B cash"}


def test_transfers_show_account_names(command_db):
    engine, data = command_db
    with Session(engine) as s:
        AssetManager(s).create_transfer(data["a"], data["cash"], data["bank"], 100)
        s.commit()
        blob = build_workbook(s, data["a"])
    [row] = _sheet(blob, "轉帳")
    assert (row["轉出帳戶"], row["轉入帳戶"], row["轉出金額"]) == ("cash", "bank", 100)


def test_text_that_looks_like_a_formula_stays_text(command_db):
    engine, data = command_db
    with Session(engine) as s:
        BudgetManager(s).add_transaction(data["a"], "2026-10-02", "=1+1", 50, "expense", "伙食")
        s.commit()
        blob = build_workbook(s, data["a"])
    sheet = load_workbook(io.BytesIO(blob))["交易明細"]
    cell = next(c for row in sheet.iter_rows(min_row=2) for c in row if c.value == "=1+1")
    assert cell.data_type == "s"


def test_the_workbook_never_contains_typed_sentences(command_db):
    engine, data = command_db
    with Session(engine) as s:
        blob = build_workbook(s, data["a"])
    book = load_workbook(io.BytesIO(blob))
    assert not any("ai" in name.lower() or "句" in name for name in book.sheetnames)


@pytest.fixture
def api(command_db, monkeypatch):
    engine, _ = command_db
    app = _load_web_app(monkeypatch)
    db = scoped_session(sessionmaker(bind=engine))
    monkeypatch.setattr(app, "db_session", db)
    monkeypatch.setattr(app, "user_manager", UserManager(db))
    monkeypatch.setattr(app, "account_privacy_service", AccountPrivacyService(db))
    monkeypatch.setattr(app, "DEV_AUTH_BYPASS", True)
    yield app.app.test_client()
    db.remove()


def _get(client, path):
    return client.get(path, base_url="http://localhost", environ_base={"REMOTE_ADDR": "127.0.0.1"})


def test_endpoint_defaults_to_excel_and_keeps_the_full_zip(api):
    excel = _get(api, "/api/account/export")
    assert excel.status_code == 200
    assert excel.headers["Content-Disposition"].endswith('.xlsx"')
    assert tuple(load_workbook(io.BytesIO(excel.data)).sheetnames) == SHEETS

    full = _get(api, "/api/account/export?kind=full")
    assert full.status_code == 200 and full.mimetype == "application/zip"
    assert full.data[:2] == b"PK"

    assert _get(api, "/api/account/export?kind=nope").status_code == 400
