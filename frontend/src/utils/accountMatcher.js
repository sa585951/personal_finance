const ACCOUNT_TYPE_LABELS = {
  cash: "現金",
  bank: "銀行",
  credit_card: "信用卡",
  e_wallet: "電子錢包",
  prepaid_card: "預付卡",
  external: "外部帳戶",
  investment: "投資",
  other: "其他",
};

const GENERIC_ACCOUNT_WORDS = [
  "電子錢包",
  "信用卡",
  "預付卡",
  "銀行",
  "帳戶",
  "活存",
  "定存",
  "現金",
  "錢包",
  "投資",
  "券商",
  "卡",
];

function normalizeAccountText(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, "");
}

function meaningfulAccountToken(value) {
  return GENERIC_ACCOUNT_WORDS.reduce(
    (token, word) => token.replaceAll(normalizeAccountText(word), ""),
    normalizeAccountText(value)
  );
}

function detectAccountType(hint) {
  const normalizedHint = normalizeAccountText(hint);
  if (normalizedHint.includes("信用卡") || normalizedHint.includes("刷卡")) return "credit_card";
  if (normalizedHint.includes("現金")) return "cash";
  if (normalizedHint.includes("電子錢包") || normalizedHint.includes("錢包")) return "e_wallet";
  if (normalizedHint.includes("預付卡")) return "prepaid_card";
  if (normalizedHint.includes("投資") || normalizedHint.includes("券商")) return "investment";
  if (normalizedHint.includes("銀行") || normalizedHint.includes("活存") || normalizedHint.includes("定存")) return "bank";
  return null;
}

function scoreAccount(account, hint) {
  const normalizedHint = normalizeAccountText(hint);
  const normalizedName = normalizeAccountText(account.bank_name || account.name);
  const meaningfulHint = meaningfulAccountToken(normalizedHint);
  const typeHint = detectAccountType(normalizedHint);
  const accountType = account.account_type || account.type || "other";
  let score = 0;

  if (meaningfulHint) {
    if (normalizedName === normalizedHint) score += 120;
    else if (normalizedHint.includes(normalizedName)) score += 90;
    else if (normalizedName.includes(normalizedHint)) score += 80;
    if (normalizedName.includes(meaningfulHint)) score += 70;
  }

  if (typeHint && accountType === typeHint) score += 20;
  if (!meaningfulHint && typeHint && accountType !== typeHint) return 0;
  if (!meaningfulHint && typeHint && accountType === typeHint) return score || 10;
  return score;
}

export function findAccountByHint(assets, accountHint, currencyHint = null) {
  if (!accountHint) return null;
  const currency = currencyHint ? String(currencyHint).trim().toUpperCase() : "";
  const candidates = Object.values(assets || {}).filter((account) => (
    !currency || String(account.currency || "").toUpperCase() === currency
  ));
  const scored = candidates
    .map((account) => ({ account, score: scoreAccount(account, accountHint) }))
    .filter(({ score }) => score > 0)
    .sort((left, right) => right.score - left.score);

  if (!scored.length) return null;
  if (scored.length > 1 && scored[0].score === scored[1].score) return null;
  return scored[0].account;
}

export { ACCOUNT_TYPE_LABELS };
