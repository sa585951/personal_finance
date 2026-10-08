"""Receipt staging and user-confirmed posting; callers own commit/rollback."""
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert

from .schema import receipt_documents_table as receipts, transactions_table as transactions, users_table
from .taiwan_invoice import parse_invoice_qr


class ReceiptImportService:
    def __init__(self, session, transaction_service):
        self.session = session
        self.transaction_service = transaction_service

    @staticmethod
    def _uuid(value):
        try:
            return UUID(str(value))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("識別碼格式不正確") from exc

    @staticmethod
    def _merchant(value):
        if not isinstance(value, str) or len(value) > 255:
            raise ValueError("店名必須是 255 字以內的文字")
        return value.strip()

    @staticmethod
    def serialize(row):
        return {
            "id": str(row["id"]), "invoice_number": row["invoice_number"],
            "issued_on": row["issued_on"].isoformat(), "seller_identifier": row["seller_identifier"],
            "total_amount": float(row["total_amount"]), "currency": row["currency"],
            "merchant_name": row["merchant_name"], "status": row["status"],
            "transaction_id": str(row["transaction_id"]) if row["transaction_id"] else None,
        }

    def _receipt(self, user_id, receipt_id):
        # Always scope before locking; receipt IDs never confer access.
        row = self.session.execute(select(receipts).where(
            receipts.c.id == self._uuid(receipt_id), receipts.c.user_id == self._uuid(user_id),
            receipts.c.deleted_at.is_(None),
        ).with_for_update()).mappings().one_or_none()
        if row is None:
            raise ValueError("找不到發票或權限不足")
        row = dict(row)
        if row["transaction_id"]:
            active = self.session.execute(select(transactions.c.id).where(
                transactions.c.id == row["transaction_id"], transactions.c.user_id == self._uuid(user_id),
                transactions.c.deleted_at.is_(None),
            )).scalar_one_or_none()
            if active is None:
                self._update(row, status="pending", transaction_id=None)
        return row

    def _update(self, row, **values):
        self.session.execute(update(receipts).where(receipts.c.id == row["id"]).values(
            **values, updated_at=func.now(),
        ))
        row.update(values)

    def import_qr(self, user_id, payload):
        source = payload.get("input_method")
        if source not in {"qr_camera", "qr_image"}:
            raise ValueError("不支援此發票輸入方式")
        uid = self._uuid(user_id)
        tz = self.session.execute(select(users_table.c.timezone).where(users_table.c.id == uid)).scalar_one()
        fields = parse_invoice_qr(payload.get("qr_payload"), today=datetime.now(ZoneInfo(tz)).date())
        new_id = uuid4()
        # PostgreSQL handles concurrent identity collisions without aborting the session.
        rid = self.session.execute(insert(receipts).values(
            id=new_id, user_id=uid, first_source=source, last_source=source, **fields,
        ).on_conflict_do_nothing(constraint="uq_receipt_identity").returning(receipts.c.id)).scalar_one_or_none()
        duplicate = rid is None
        if duplicate:
            rid = self.session.execute(select(receipts.c.id).where(
                receipts.c.user_id == uid,
                *(getattr(receipts.c, key) == fields[key] for key in ("invoice_number", "issued_on", "seller_identifier")),
            )).scalar_one()
        row = self._receipt(user_id, rid)
        if row["total_amount"] != fields["total_amount"]:
            raise ValueError("相同發票的金額不一致，請確認 QR Code")
        self._update(row, last_source=source)
        return {"receipt": self.serialize(row), "duplicate": duplicate}

    def matches(self, user_id, receipt_id, merchant=""):
        row = self._receipt(user_id, receipt_id)
        return {"receipt": self.serialize(row), "candidates": self._candidates(user_id, row, self._merchant(merchant))}

    def _candidates(self, user_id, row, merchant):
        rows = self.session.execute(select(transactions).where(
            transactions.c.user_id == self._uuid(user_id), transactions.c.deleted_at.is_(None),
            transactions.c.trip_id.is_(None), transactions.c.type == "expense",
            transactions.c.original_currency == row["currency"], transactions.c.original_amount == row["total_amount"],
            transactions.c.transaction_date.between(row["issued_on"] - timedelta(days=1), row["issued_on"] + timedelta(days=1)),
            ~select(receipts.c.id).where(receipts.c.transaction_id == transactions.c.id).exists(),
        )).mappings().all()
        def similarity(candidate):
            normalize = lambda text: "".join((text or "").casefold().split())
            return SequenceMatcher(None, normalize(merchant), normalize(candidate["merchant"])).ratio() if merchant and candidate["merchant"] else 0
        rows.sort(key=lambda candidate: (
            candidate["transaction_date"] != row["issued_on"], -similarity(candidate),
            abs((candidate["transaction_date"] - row["issued_on"]).days),
            -candidate["created_at"].timestamp(), str(candidate["id"]),
        ))
        return [{
            "id": str(candidate["id"]), "date": candidate["transaction_date"].isoformat(),
            "amount": float(candidate["original_amount"]), "currency": candidate["original_currency"],
            "title": candidate["title"], "merchant": candidate["merchant"],
            "reasons": ["相同金額與幣別", "同一天" if candidate["transaction_date"] == row["issued_on"] else "日期相差一天"]
            + (["店名相似"] if similarity(candidate) >= .6 else []),
        } for candidate in rows[:5]]

    def resolve(self, user_id, receipt_id, payload):
        row = self._receipt(user_id, receipt_id)
        action = payload.get("action")
        if action not in {"create", "link", "ignore", "reopen"}:
            raise ValueError("不支援此發票處理方式")
        if row["status"] == "linked":
            return {"receipt": self.serialize(row), "replayed": True}
        merchant = self._merchant(payload.get("merchant", row["merchant_name"] or ""))
        if action == "ignore":
            self._update(row, status="ignored", merchant_name=merchant or None)
        elif action == "reopen":
            self._update(row, status="pending")
        elif action == "link":
            tid = self._uuid(payload.get("transaction_id"))
            # Lock the transaction too, so competing receipts cannot link it concurrently.
            self.session.execute(select(transactions.c.id).where(
                transactions.c.id == tid, transactions.c.user_id == self._uuid(user_id),
            ).with_for_update()).scalar_one_or_none()
            if str(tid) not in {candidate["id"] for candidate in self._candidates(user_id, row, merchant)}:
                raise ValueError("此交易不符合候選條件或已連結發票")
            self._update(row, status="linked", transaction_id=tid, merchant_name=merchant or None)
        else:
            for field in ("item", "budget_category"):
                value = payload.get(field)
                if not isinstance(value, str) or not value.strip() or len(value) > 255:
                    raise ValueError("請補上項目與分類")
            description = payload.get("description", "")
            if not isinstance(description, str) or len(description) > 10000:
                raise ValueError("備註格式不正確")
            # Row lock handles retries; each posting gets its own server request key,
            # so re-creating after soft deletion cannot replay the deleted posting.
            result = self.transaction_service.create_transaction(user_id, {
                "date": row["issued_on"].isoformat(), "amount": row["total_amount"],
                "original_currency": row["currency"], "exchange_rate": 1, "type": "expense",
                "item": payload["item"].strip(), "budget_category": payload["budget_category"],
                "account_id": payload.get("account_id"), "merchant": merchant or None,
                "description": description, "client_request_id": str(uuid4()),
            })
            if not result["success"]:
                raise ValueError(result["message"])
            self._update(row, status="linked", transaction_id=self._uuid(result["transaction_id"]), merchant_name=merchant or None)
        return {"receipt": self.serialize(row), "replayed": False}
