"""Parse only the fixed header of a Taiwan electronic invoice left QR code.

This validates structure, not authenticity or whether the invoice was voided.
"""
import re
from datetime import date
from decimal import Decimal


def parse_invoice_qr(payload, *, today=None):
    if not isinstance(payload, str) or not 77 <= len(payload) <= 8192:
        raise ValueError("請掃描台灣電子發票左側 QR Code")
    header = payload[:77]
    if not re.fullmatch(r"[A-Z]{2}[0-9]{8}", header[:10]):
        raise ValueError("發票號碼格式不正確")
    if not re.fullmatch(r"[0-9]{7}", header[10:17]):
        raise ValueError("發票日期格式不正確")
    try:
        issued_on = date(int(header[10:13]) + 1911, int(header[13:15]), int(header[15:17]))
    except ValueError as exc:
        raise ValueError("發票日期不正確") from exc
    if issued_on < date(2010, 1, 1) or issued_on > (today or date.today()):
        raise ValueError("發票日期超出支援範圍")
    if not re.fullmatch(r"[0-9]{4}", header[17:21]):
        raise ValueError("發票 QR 格式不正確")
    if not re.fullmatch(r"[0-9A-Fa-f]{16}", header[21:37]):
        raise ValueError("發票金額格式不正確")
    amount = int(header[29:37], 16)
    if amount <= 0:
        raise ValueError("發票總額必須大於零")
    if not re.fullmatch(r"[0-9]{16}", header[37:53]) or header[45:53] == "00000000":
        raise ValueError("賣方統編格式不正確")
    if not re.fullmatch(r"[A-Za-z0-9+/]{22}==", header[53:77]):
        raise ValueError("發票 QR 驗證區格式不正確")
    if len(payload) > 77 and payload[77] != ":":
        raise ValueError("發票 QR 延伸區格式不正確")
    return {
        "invoice_number": header[:10], "issued_on": issued_on,
        "seller_identifier": header[45:53], "total_amount": Decimal(amount),
        "currency": "TWD",
    }
