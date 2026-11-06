/* global sessionStorage, Storage */
const assert = require('node:assert/strict');

const path = '/assets';
const panel = page => page.getByRole('status', {name: '待確認校正'});
const storageKey = 'nomica-pending:test:account:adjust:card';
const stored = page => page.evaluate(key => JSON.parse(sessionStorage.getItem(key)), storageKey);

async function openAdjustment(page) {
  await page.locator('.group-header').filter({hasText: '信用卡'}).click();
  await page.getByRole('button', {name: '校正餘額', exact: true}).click();
  await page.locator('.swal2-input').fill('-250.50');
  await page.locator('#balance-adjustment-note').fill('QA balance note');
}

module.exports = async function testAdjustmentRecovery(browser, base, installMocks) {
  const failures = [];
  async function check(name, test) {
    try {
      await test();
      console.log(`adjustment recovery: ${name} passed`);
    } catch (error) { failures.push(`${name}: ${error.message}`); }
  }
  async function setup(page) {
    await installMocks(page);
    await page.goto(new URL(path, base).href, {waitUntil: 'networkidle'});
  }
  for (const status of ['lost', 400, 401, 409, 500, 'success']) {
    await check(String(status), async () => {
      const context = await browser.newContext();
      try {
        const page = await context.newPage();
        await setup(page);
        const sends = [];
        await page.route('**/api/assets/card/adjustments', route => {
          const request = route.request();
          if (request.method() !== 'POST') return route.fallback();
          sends.push({body: request.postDataJSON(), owner: request.headers()['x-nomica-request-owner']});
          if (sends.length > 1 || status === 'success') {
            return route.fulfill({status: sends.length > 1 ? 200 : 201, json: {success: true, data: {id: 'saved'}}});
          }
          if (status === 'lost') return route.abort('failed');
          return route.fulfill({status, json: {success: false, message: 'Controlled adjustment failure'}});
        });
        await openAdjustment(page);
        await page.getByRole('button', {name: '確認校正', exact: true}).click();
        if (status === 400 || status === 'success') {
          await page.getByText(status === 400 ? 'Controlled adjustment failure' : '校正完成', {exact: true}).waitFor({timeout: 4000});
          assert.equal(sends.length, 1);
          assert.match(sends[0].body.client_request_id, /^[a-f0-9-]{36}$/);
          assert.equal(sends[0].owner, 'test');
          assert.equal(await stored(page), null);
        } else {
          await panel(page).waitFor({timeout: 4000});
          assert.equal((await stored(page)).requestId, sends[0].body.client_request_id);
          await page.reload({waitUntil: 'networkidle'});
          await panel(page).waitFor({timeout: 4000});
          assert.equal(sends.length, 1, 'reload never posts');
          assert.match(await panel(page).innerText(), /-250\.50?|QA balance note/);
          await panel(page).getByRole('button', {name: '以原資料重試'}).dblclick();
          await panel(page).waitFor({state: 'detached', timeout: 4000});
          assert.equal(sends.length, 2);
          assert.deepEqual(sends[1], sends[0]);
          assert.equal(sends[0].owner, 'test');
          assert.equal(await stored(page), null);
        }
      } finally { await context.close(); }
    });
  }
  await check('owner change while a confirmation is open blocks the write', async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage();
      let writes = 0;
      await setup(page);
      await page.route('**/api/assets/card/adjustments', route => {
        if (route.request().method() === 'POST') writes++;
        return route.fallback();
      });
      await openAdjustment(page);
      await page.route('**/api/auth/me', route => route.fulfill({json: {success: true, data: {user_id: 'other'}}}));
      await page.getByRole('button', {name: '確認校正', exact: true}).click();
      await page.getByRole('alert').filter({hasText: '登入使用者已變更'}).waitFor({timeout: 4000});
      assert.equal(writes, 0);
      assert.equal(await stored(page), null);
    } finally { await context.close(); }
  });
  await check('storage write failure blocks without POST', async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage();
      await page.addInitScript(() => {
        const old = Storage.prototype.setItem;
        Storage.prototype.setItem = function(key, ...args) {
          if (key.includes(':account:adjust:')) throw new DOMException('Controlled storage failure', 'SecurityError');
          return old.call(this, key, ...args);
        };
      });
      await setup(page);
      let writes = 0;
      await page.route('**/api/assets/card/adjustments', route => {
        if (route.request().method() === 'POST') writes++;
        return route.fallback();
      });
      await openAdjustment(page);
      await page.getByRole('button', {name: '確認校正', exact: true}).click();
      await page.getByRole('alert').filter({hasText: '無法保存'}).waitFor({timeout: 4000});
      assert.equal(writes, 0);
      assert.equal(await stored(page), null);
    } finally { await context.close(); }
  });
  await check('reload separates account scopes and preserves recovery even if the account is absent', async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage();
      await setup(page);
      await page.evaluate(() => {
        function seed(owner, account, suffix, amount) {
          sessionStorage.setItem(`nomica-pending:${owner}:account:adjust:${account}`, JSON.stringify({
            requestId: `11c4f632-a77c-4619-ae82-963bced6d00${suffix}`,
            payload: {new_balance: amount, reason: 'other', note: null},
          }));
        }
        seed('test', 'card', '1', 200);
        seed('test', 'retired-account', '2', 300);
        seed('other', 'investment', '3', 400);
      });
      await page.reload({waitUntil: 'networkidle'});
      assert.equal(await panel(page).count(), 2);
      assert.equal(await panel(page).filter({hasText: 'retired-account'}).count(), 1);
      assert.equal(await panel(page).filter({hasText: '400'}).count(), 0);
      let sent;
      await page.route('**/api/assets/retired-account/adjustments', route => {
        sent = route.request().postDataJSON();
        return route.fulfill({json: {success: true, replayed: true, data: {id: 'saved'}}});
      });
      await panel(page).filter({hasText: 'retired-account'}).getByRole('button', {name: '以原資料重試'}).click();
      await panel(page).filter({hasText: 'retired-account'}).waitFor({state: 'detached', timeout: 4000});
      assert.equal(sent.new_balance, 300);
      assert.equal(sent.client_request_id, '11c4f632-a77c-4619-ae82-963bced6d002');
      assert.equal((await stored(page)).payload.new_balance, 200);
    } finally { await context.close(); }
  });
  assert.deepEqual(failures, [], failures.join('\n'));
};
