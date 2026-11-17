// S5 privacy flows, run by test-e2e.cjs after the ledger smoke on the same dev user.
const assert = require('node:assert/strict');
const fs = require('node:fs');

module.exports = async function testPrivacy({ page, web, stamp, accountName, expectEventually }) {
  const before = (await (await page.request.get(`${web}/api/auth/me`)).json()).data.user_id;

  // Export: the everyday Excel file and the full backup ZIP both download.
  await page.goto(`${web}/account`);
  const excelEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: '下載 Excel', exact: true }).click();
  const excel = await excelEvent;
  assert.match(excel.suggestedFilename(), /^nomica-\d{8}\.xlsx$/);
  const sheet = fs.readFileSync(await excel.path());
  assert.equal(sheet.subarray(0, 2).toString(), 'PK', 'an .xlsx file is a ZIP container');
  assert(sheet.includes(Buffer.from('xl/workbook.xml')), 'export is an Excel workbook');

  await page.getByText('進階：完整原始資料', { exact: true }).click(); // collapsed by default
  const fullEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: '下載完整備份（ZIP）', exact: true }).click();
  const full = await fullEvent;
  assert.match(full.suggestedFilename(), /^nomica-full-export-\d{8}\.zip$/);
  const archive = fs.readFileSync(await full.path());
  assert.equal(archive.subarray(0, 2).toString(), 'PK', 'full export is a ZIP');
  assert(archive.includes(Buffer.from('transactions.csv')), 'full export lists transactions.csv');

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
