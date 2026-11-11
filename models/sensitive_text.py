"""One place that decides whether text may be parsed, stored or sent to a model.

It is a safety net, not a guarantee: it catches obvious card numbers, bank-account-length digit
runs, Taiwan ID numbers and the usual secret keywords. People are still told not to type them.
"""
import re
from unicodedata import normalize

SENSITIVE_MESSAGE = "請移除卡號、密碼、帳號或身分證字號等敏感資料，再重新輸入記帳文字。"

SENSITIVE_TEXT = re.compile(
    # Words that introduce a secret.
    r"密碼|驗證碼|安全碼|背面三碼|身分證|身份證|卡號|(?i:\b(?:cvv|cvc|otp|password|api[ -]?key)\b)"
    # Card numbers: 13-19 digits, optionally grouped with spaces or hyphens.
    r"|(?<!\d)(?:\d[ -]?){13,19}(?!\d)"
    # Bank accounts and phone numbers: 10-12 digits in a row (no real bookkeeping amount is that long).
    r"|(?<!\d)\d{10,12}(?!\d)"
    # Taiwan ID / resident certificate number: one letter, 1 or 2, then 8 digits.
    r"|(?<![A-Za-z0-9])[A-Za-z][12]\d{8}(?!\d)"
)


def contains_sensitive(text):
    return bool(SENSITIVE_TEXT.search(normalize("NFKC", str(text or ""))))
