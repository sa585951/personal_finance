const ZERO_DECIMAL = new Set(["TWD", "JPY", "KRW"]);

export function minorUnits(currency = "TWD") {
  return ZERO_DECIMAL.has(currency) ? 0 : 2;
}

/** "1,234" for TWD/JPY/KRW, "12.50" for USD/EUR. Sign is the caller's choice. */
export function formatAmount(amount, currency = "TWD") {
  const digits = minorUnits(currency);
  return Math.abs(Number(amount || 0)).toLocaleString("zh-TW", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatSigned(amount, type, currency = "TWD") {
  const sign = type === "income" ? "+" : "−";
  return `${sign}${formatAmount(amount, currency)}`;
}

const WEEKDAYS = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"];

export function localDateKey(date = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** "今天" / "昨天" / "11/8 週日" for a YYYY-MM-DD string. */
export function friendlyDate(value, today = new Date()) {
  if (!value) return "";
  const [y, m, d] = value.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  const todayKey = localDateKey(today);
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (value === todayKey) return "今天";
  if (value === localDateKey(yesterday)) return "昨天";
  return `${m}/${d} ${WEEKDAYS[date.getDay()]}`;
}
