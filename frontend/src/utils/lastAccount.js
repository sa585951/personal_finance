// Remembers the account a person last used per transaction type so new entries
// default to a real account instead of silently skipping balance updates.
// "none" records an explicit choice of 不連動帳戶.
const NONE = "none";
const key = (type) => `nomica:last-account:${type}`;

export function rememberLastAccount(type, accountId) {
  try {
    localStorage.setItem(key(type), accountId || NONE);
  } catch {
    // Private mode or blocked storage: the next entry falls back to the default rule.
  }
}

function storedAccount(type) {
  try {
    return localStorage.getItem(key(type));
  } catch {
    return null;
  }
}

/**
 * Pick the default account id for a new entry.
 * 1. The last account used for this type, if it is still among the options.
 * 2. An explicit earlier choice of 不連動帳戶 stays respected.
 * 3. Otherwise the first account in the preferred currency.
 * With requiredCurrency (an entry whose currency is already known, e.g. a parsed
 * "20 USD"), only accounts in that currency qualify: picking another would
 * silently relabel the amount in the account's currency.
 * Returns "" when nothing safe can be chosen.
 */
export function defaultAccountId(type, accounts, { preferredCurrency = "TWD", requiredCurrency = "" } = {}) {
  const options = (accounts || []).filter((account) => account && account.is_active !== false
    && (!requiredCurrency || account.currency === requiredCurrency));
  preferredCurrency = requiredCurrency || preferredCurrency;
  const last = storedAccount(type);
  if (last === NONE) return "";
  if (last && options.some((account) => account.id === last)) return last;
  return options.find((account) => account.currency === preferredCurrency)?.id || "";
}
