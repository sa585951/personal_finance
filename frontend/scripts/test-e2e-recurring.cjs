// Fixed monthly entries, run by test-e2e.cjs after the ledger smoke on the same dev user.
// The rule starts long ago on day 1, so three months are due; confirming one must move the
// balance once, skipping another must not.
const assert = require('node:assert/strict');

module.exports = async function testRecurring({ page, web, stamp, accountName, accountByName, expectEventually }) {
  const title = `E2E 訂閱 ${stamp}`;
  const before = (await accountByName(page, accountName)).balance;

  await page.goto(`${web}/recurring?new=1`);
  await page.getByLabel('項目').fill(title);
  await page.getByLabel('金額（NT$）').fill('100');
  await page.getByLabel('分類').selectOption({ index: 1 });
  await page.getByLabel('帳戶').selectOption({ label: accountName });
  await page.getByLabel('每月幾號').fill('1');
  await page.getByLabel('開始日').fill('2020-01-01');
  await page.getByRole('button', { name: '儲存', exact: true }).click();
  await page.getByText(title).first().waitFor();

  // Nothing reaches the ledger until a month is confirmed.
  assert.equal((await accountByName(page, accountName)).balance, before, 'pending items do not move the balance');
  const listing = (await (await page.request.get(`${web}/api/recurring`)).json()).data;
  assert.equal(listing.pending.length, 3, 'the last three months are waiting');

  // Home shows them, and confirming one books it once.
  await page.goto(`${web}/`);
  await page.getByText('待確認的固定收支').waitFor();
  const confirmed = page.waitForResponse(response => /\/confirm$/.test(response.url()));
  await page.getByRole('button', { name: '確認', exact: true }).first().click();
  assert.equal((await confirmed).status(), 200);
  await expectEventually(async () => (await accountByName(page, accountName)).balance === before - 100,
    'confirming a month books it once');

  // Skipping removes a month without booking it.
  const skipped = page.waitForResponse(response => /\/skip$/.test(response.url()));
  await page.getByRole('button', { name: '略過', exact: true }).first().click();
  await page.getByRole('button', { name: '略過', exact: true }).last().click(); // confirm dialog
  assert.equal((await skipped).status(), 200);
  assert.equal((await accountByName(page, accountName)).balance, before - 100, 'skipping books nothing');
  assert.equal((await (await page.request.get(`${web}/api/recurring`)).json()).data.pending.length, 1);
};
