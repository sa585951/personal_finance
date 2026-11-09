// S5 privacy flows, run by test-e2e.cjs after the ledger smoke on the same dev user.
const assert = require('node:assert/strict');
const fs = require('node:fs');

module.exports = async function testPrivacy({ page, web, stamp, accountName, expectEventually }) {
  const before = (await (await page.request.get(`${web}/api/auth/me`)).json()).data.user_id;

  // Export: a real ZIP that carries this run's data.
  await page.goto(`${web}/account`);
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: '下載資料', exact: true }).click();
  const download = await downloadEvent;
  assert.match(download.suggestedFilename(), /^nomica-export-\d{8}\.zip$/);
  const archive = fs.readFileSync(await download.path());
  assert.equal(archive.subarray(0, 2).toString(), 'PK', 'export is a ZIP');
  assert(archive.includes(Buffer.from('transactions.csv')), 'export lists transactions.csv');

  // Delete: the button stays disabled until the exact phrase is typed.
  const remove = page.getByRole('button', { name: '永久刪除帳號', exact: true });
  await page.locator('#deleteConfirmation').fill('刪除');
  assert.equal(await remove.isDisabled(), true);
  await page.locator('#deleteConfirmation').fill('刪除我的帳號');
  const deleted = page.waitForResponse(response => response.url().endsWith('/api/account/delete'));
  await remove.click();
  assert.equal((await deleted).status(), 200);

  // The identity is unlinked: the same login now reaches a fresh, empty account.
  await expectEventually(async () => {
    const me = (await (await page.request.get(`${web}/api/auth/me`)).json()).data;
    return me.user_id !== before;
  }, 'deleted identity resolves to a new user');
  const assets = Object.values((await (await page.request.get(`${web}/api/assets`)).json()).data || {});
  assert(!assets.some(account => account.bank_name === accountName), `deleted account ${stamp} is gone`);
};
