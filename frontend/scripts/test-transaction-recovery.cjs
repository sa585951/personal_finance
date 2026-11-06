/* global window, sessionStorage, Storage */
const assert = require('node:assert/strict');

module.exports = async function testTransactionRecovery(browser, base, installMocks) {
  const failures = [];
  let browserErrors = [];
  async function check(name, test) {
    if (process.env.RECOVERY_CASE && !name.includes(process.env.RECOVERY_CASE)) return;
    browserErrors = [];
    try { await test(); assert.deepEqual(browserErrors, [], 'no uncaught browser exceptions'); console.log(`request recovery: ${name} passed`); }
    catch (error) { failures.push(`${name}: ${error.message}`); }
  }
  const trip = { id: 'trip', name: 'Recovery trip', start_date: '2026-11-01', end_date: '2026-11-30',
    base_currency: 'TWD', default_currency: 'TWD', timezone: 'Asia/Taipei', status: 'active',
    current_member_id: 'member', members: [{ id: 'member', user_id: 'test', display_name: 'Owner', role: 'owner', status: 'active' }] };
  async function setup(page) {
    await installMocks(page);
    page.on('pageerror', error => browserErrors.push(error.message));
    await page.route('**/api/budgets/categories*', route => route.fulfill({ json: { success: true, data: [{ name: '伙食', code: 'food', kind: 'expense' }] } }));
    await page.route('**/api/trips', route => route.fulfill({ json: { success: true, data: [trip] } }));
    await page.route('**/api/trips/trip/overview', route => route.fulfill({ json: { success: true, data: {
      trip, transactions: [], transaction_summary: {}, split_summary: [], settlements: [], settlement_suggestions: [],
    } } }));
  }
  async function fill(page, kind) {
    if (kind === 'daily') {
      await page.getByRole('button', { name: '手動新增支出', exact: true }).click();
      await page.locator('#transactionCategory').fill('Recovery expense');
      await page.locator('#transactionAmount').fill('100');
      await page.locator('#budgetCategory').selectOption('伙食');
    } else {
      const form = page.locator('.expense-form');
      await form.locator('input[type=text]').first().fill('Recovery expense');
      await form.locator('input[type=number]').first().fill('100');
    }
  }
  async function storage(page, kind) {
    return page.evaluate(scope => {
      const key = `nomica-pending:test:${scope}`;
      const raw = sessionStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    }, kind === 'daily' ? 'transaction:daily' : 'transaction:trip:trip');
  }
  for (const kind of ['daily', 'trip']) {
    const url = kind === 'daily' ? '/add' : '/trips/trip';
    for (const status of ['lost', 500, 401, 409, 'legacy', 400, 'success']) {
      await check(`${kind} ${status}`, async () => {
        const context = await browser.newContext();
        try {
          const page = await context.newPage(); await setup(page);
          const sends = [];
          await page.route('**/api/transactions', async route => {
            if (route.request().method() !== 'POST') return route.fallback();
            sends.push(route.request().postDataJSON());
            if (sends.length > 1 || status === 'success') return route.fulfill({ status: sends.length > 1 ? 200 : 201,
              json: { success: true, message: 'Saved', data: { transaction_id: 'saved' }, replayed: sends.length > 1 } });
            if (status === 'lost') return route.abort('failed');
            return route.fulfill({ status: status === 'legacy' ? 409 : status,
              json: { success: false, message: 'Controlled failure', ...(status === 'legacy' ? {
                code: 'LEGACY_REQUEST_UNVERIFIABLE', data: { transaction_id: 'existing-transaction' },
              } : {}) } });
          });
          await page.goto(new URL(url, base).href, { waitUntil: 'networkidle' });
          await fill(page, kind);
          await page.locator(kind === 'daily' ? '.form-container form button[type=submit]' : '.expense-form button[type=submit]').click();
          await page.waitForFunction(() => !document.querySelector('button[type=submit]:disabled'));
          assert.equal(sends.length, 1, 'one click sends once');
          assert.match(sends[0].client_request_id || '', /^[0-9a-f-]{36}$/, 'must send stable UUID');
          if (status === 400 || status === 'success') {
            assert.equal(await storage(page, kind), null, 'definitive rejection/success clears pending');
            return;
          }
          await page.getByRole('status', { name: '待確認交易' }).waitFor({ timeout: 3000 });
          const first = await storage(page, kind);
          assert.equal(first?.requestId, sends[0].client_request_id, 'pending key preserved');
          assert.equal(first.payload.item, 'Recovery expense');
          if (status === 'legacy') {
            const panel = page.getByRole('status', { name: '待確認交易' });
            await panel.waitFor({ timeout: 3000 });
            assert((await panel.innerText()).includes('existing-transaction'));
            assert.equal(await panel.locator('input[type=checkbox]').isChecked(), false);
            assert.equal(await panel.getByRole('button', { name: '結束這次待確認請求' }).isDisabled(), true);
            await panel.getByLabel('我已核對既有紀錄').check();
            await panel.getByRole('button', { name: '結束這次待確認請求' }).click();
            assert.equal(await storage(page, kind), null);
            assert.equal(sends.length, 1, 'acknowledgement never posts');
            await page.reload({ waitUntil: 'networkidle' });
            await fill(page, kind);
            await page.locator(kind === 'daily' ? '.form-container form button[type=submit]' : '.expense-form button[type=submit]').click();
            await page.waitForFunction(() => !document.querySelector('button[type=submit]:disabled'));
            assert.equal(sends.length, 2);
            assert.notEqual(sends[1].client_request_id, sends[0].client_request_id, 'only a new explicit submit gets a new key');
          } else {
            await page.reload({ waitUntil: 'networkidle' });
            const panel = page.getByRole('status', { name: '待確認交易' });
            await panel.waitFor({ timeout: 3000 });
            assert.equal(sends.length, 1, 'reload must not automatically post');
            assert.equal(await panel.getByRole('button', { name: '結束這次待確認請求' }).count(), 0);
            await panel.getByRole('button', { name: '以原資料重試' }).click();
            await panel.waitFor({ state: 'detached' });
            assert.deepEqual(sends[1], sends[0], 'retry must use exactly the frozen original payload/key');
            assert.equal(await storage(page, kind), null);
          }
        } finally { await context.close(); }
      });
    }
  }
  await check('reactive snapshot and owner/scope separation', async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage(); await setup(page);
      await page.goto(new URL('/login', base).href, { waitUntil: 'networkidle' });
      const result = await page.evaluate(async () => {
        const { reactive } = await import('/node_modules/.vite/deps/vue.js');
        const { openPendingCommand } = await import('/src/utils/pendingFinancialCommand.js');
        const command = await openPendingCommand('transaction:trip:A');
        const value = reactive({ amount: 100, split_member_ids: ['a'], split_allocations: [{ trip_member_id: 'a', amount: 100 }] });
        const sent = command.prepare(value);
        value.split_member_ids.push('b'); value.split_allocations[0].amount = 50;
        sent.split_member_ids.push('c');
        const restored = await openPendingCommand('transaction:trip:A');
        const other = await openPendingCommand('transaction:trip:B');
        return { frozen: restored.pending.payload, local: command.pending.payload, other: other.pending };
      });
      assert.deepEqual(result, { frozen: { amount: 100, split_member_ids: ['a'], split_allocations: [{ trip_member_id: 'a', amount: 100 }] },
        local: { amount: 100, split_member_ids: ['a'], split_allocations: [{ trip_member_id: 'a', amount: 100 }] }, other: null });
      await page.route('**/api/auth/me', route => route.fulfill({ json: { success: true, data: { user_id: 'other' } } }));
      assert.equal(await page.evaluate(async () => (await (await import('/src/utils/pendingFinancialCommand.js')).openPendingCommand('transaction:trip:A')).pending), null);
    } finally { await context.close(); }
  });
  await check('late response cannot clear a newer pending intent', async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage(); await setup(page);
      await page.goto(new URL('/login', base).href, { waitUntil: 'networkidle' });
      const value = await page.evaluate(async () => {
        const { openPendingCommand } = await import('/src/utils/pendingFinancialCommand.js');
        const old = await openPendingCommand('transaction:daily');
        const first = old.prepare({ amount: 100 });
        const current = await openPendingCommand('transaction:daily');
        current.clear();
        const second = current.prepare({ amount: 200 });
        old.clear(first.client_request_id);
        return { pending: (await openPendingCommand('transaction:daily')).pending, second };
      });
      assert.equal(value.pending?.payload.amount, 200);
      assert.equal(value.pending.requestId, value.second.client_request_id);
    } finally { await context.close(); }
  });
  await check('stale view cannot overwrite a newer intent', async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage(); await setup(page);
      await page.goto(new URL('/login', base).href, { waitUntil: 'networkidle' });
      const result = await page.evaluate(async () => {
        const { openPendingCommand } = await import('/src/utils/pendingFinancialCommand.js');
        const stale = await openPendingCommand('transaction:daily');
        const current = await openPendingCommand('transaction:daily');
        current.prepare({ amount: 200 });
        let blocked = false;
        try { stale.prepare({ amount: 100 }); } catch { blocked = true; }
        return { blocked, pending: (await openPendingCommand('transaction:daily')).pending.payload };
      });
      assert.deepEqual(result, { blocked: true, pending: { amount: 200 } });
    } finally { await context.close(); }
  });
  for (const kind of ['daily', 'trip']) await check(`${kind} changed signed-in owner blocks a stale form before POST`, async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage(); await setup(page); let sends = 0;
      await page.route('**/api/transactions', route => { if (route.request().method() === 'POST') sends++; return route.fallback(); });
      await page.goto(new URL(kind === 'daily' ? '/add' : '/trips/trip', base).href, { waitUntil: 'networkidle' });
      await fill(page, kind);
      await page.route('**/api/auth/me', route => route.fulfill({ json: { success: true, data: { user_id: 'other' } } }));
      await page.locator(kind === 'daily' ? '.form-container form button[type=submit]' : '.expense-form button[type=submit]').click();
      await page.getByRole('alert').first().waitFor({ timeout: 3000 });
      assert.equal(sends, 0);
      assert.equal(await storage(page, kind), null);
    } finally { await context.close(); }
  });
  await check('auth rejection cannot discard an unknown transaction', async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage(); await setup(page); let sends = 0;
      await page.route('**/api/transactions', route => { if (route.request().method() === 'POST') sends++; return route.fallback(); });
      await page.goto(new URL('/login', base).href, { waitUntil: 'networkidle' });
      await page.evaluate(() => sessionStorage.setItem('nomica-pending:test:transaction:daily', JSON.stringify({
        requestId: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', payload: { item: 'Unknown', amount: 100, type: 'expense' },
      })));
      await page.goto(new URL('/add', base).href, { waitUntil: 'networkidle' });
      await page.route('**/api/auth/me', route => route.fulfill({ status: 400, json: { success: false, message: 'Auth rejection' } }));
      const panel = page.getByRole('status', { name: '待確認交易' });
      await panel.getByRole('button', { name: '以原資料重試' }).click();
      await page.waitForFunction(() => !Array.from(document.querySelectorAll('button')).some(el => el.textContent === '核對中'));
      assert.equal(sends, 0);
      assert.equal((await storage(page, 'daily'))?.requestId, 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
      await panel.waitFor();
    } finally { await context.close(); }
  });
  for (const kind of ['daily', 'trip']) for (const failure of ['read', 'write']) await check(`${kind} storage ${failure} fails closed`, async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage(); await setup(page); let sends = 0;
      await page.route('**/api/transactions', route => { if (route.request().method() === 'POST') sends++; return route.fallback(); });
      await page.addInitScript(failure => {
        const method = failure === 'read' ? 'getItem' : 'setItem';
        const original = Storage.prototype[method];
        Storage.prototype[method] = function(key, ...args) {
          if (key.startsWith('nomica-pending:')) throw new DOMException('Controlled storage failure', 'SecurityError');
          return original.call(this, key, ...args);
        };
      }, failure);
      await page.goto(new URL(kind === 'daily' ? '/add' : '/trips/trip', base).href, { waitUntil: 'networkidle' });
      if (failure === 'write') {
        await fill(page, kind);
        await page.locator(kind === 'daily' ? '.form-container form button[type=submit]' : '.expense-form button[type=submit]').click();
        await page.getByRole('alert').first().waitFor({ timeout: 3000 });
      } else {
        await page.getByRole('alert').first().waitFor({ timeout: 3000 });
        assert.equal(await page.locator(kind === 'daily' ? '.form-container' : '.expense-form').count(), 0);
      }
      assert.equal(sends, 0);
    } finally { await context.close(); }
  });
  await check('pending layout across five widths and both themes', async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage(); await setup(page);
      await page.route('**/api/transactions', route => route.request().method() === 'POST'
        ? route.fulfill({ status: 409, json: { success: false, code: 'LEGACY_REQUEST_UNVERIFIABLE', message: '請先核對既有交易', data: { transaction_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' } } }) : route.fallback());
      await page.goto(new URL('/login', base).href, { waitUntil: 'networkidle' });
      await page.evaluate(() => sessionStorage.setItem('nomica-pending:test:transaction:daily', JSON.stringify({
        requestId: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', payload: { item: 'LongTitle'.repeat(28), date: '2026-11-03', amount: 100, original_currency: 'TWD', budget_category: '伙食', type: 'expense' },
      })));
      for (const width of [320, 390, 430, 768, 1280]) for (const theme of ['light', 'dark']) {
        await page.setViewportSize({ width, height: 900 });
        await page.evaluate(theme => localStorage.setItem('nomica-theme', theme), theme);
        await page.goto(new URL('/add', base).href, { waitUntil: 'networkidle' });
        const panel = page.getByRole('status', { name: '待確認交易' });
        await panel.getByRole('button', { name: '以原資料重試' }).click();
        await panel.getByLabel('我已核對既有紀錄').waitFor();
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), theme);
        await panel.getByLabel('我已核對既有紀錄').check();
        const acknowledge = panel.getByRole('button', { name: '結束這次待確認請求' });
        await acknowledge.scrollIntoViewIfNeeded();
        await acknowledge.click({ trial: true });
        await panel.screenshot({ path: require('node:path').resolve(__dirname, `../test-results/ui/recovery-${width}-${theme}.png`) });
      }
    } finally { await context.close(); }
  });
  for (const change of ['amount', 'edit mode']) await check(`trip freezes clicked intent before delayed auth: ${change}`, async () => {
    const context = await browser.newContext();
    let release;
    try {
      const page = await context.newPage(); await setup(page);
      const existing = { id: 'existing', date: '2026-11-03', category: 'Existing edit', amount: 7, currency: 'TWD', base_currency: 'TWD', converted_amount: 7, exchange_rate: 1,
        budget_category: '伙食', paid_by_member_id: 'member', account_id: '', can_edit: true, can_delete: false, splits: [{ trip_member_id: 'member', share_amount: 7, split_method: 'equal' }] };
      await page.route('**/api/trips/trip/overview', route => route.fulfill({ json: { success: true, data: { trip, transactions: [existing], transaction_summary: {}, split_summary: [], settlements: [] } } }));
      await page.route('**/api/transactions/existing', route => route.fulfill({ json: { success: true, data: existing } }));
      const sends = [];
      await page.route('**/api/transactions', route => {
        if (route.request().method() !== 'POST') return route.fallback();
        sends.push(route.request().postDataJSON()); return route.abort('failed');
      });
      await page.goto(new URL('/trips/trip', base).href, { waitUntil: 'networkidle' }); await fill(page, 'trip');
      let waiting; const entered = new Promise(resolve => { waiting = resolve; });
      const gate = new Promise(resolve => { release = resolve; });
      await page.route('**/api/auth/me', async route => { waiting(); await gate; return route.fulfill({ json: { success: true, data: { user_id: 'test' } } }); });
      await page.locator('.expense-form button[type=submit]').click(); await entered;
      if (change === 'amount') await page.locator('.expense-form input[type=number]').first().fill('999');
      else {
        await page.locator('.trip-tabs').getByRole('button', { name: '交易', exact: true }).click();
        await page.getByTitle('編輯交易', { exact: true }).click();
        await page.waitForFunction(() => document.querySelector('.expense-form input[type=text]')?.value === 'Existing edit');
      }
      release();
      await page.waitForFunction(() => !document.querySelector('.expense-form button[type=submit]:disabled'));
      assert.equal(sends.length, 1);
      assert.equal(sends[0].amount, 100);
      assert.equal(sends[0].item, 'Recovery expense');
      assert.equal((await storage(page, 'trip')).payload.amount, 100);
      if (change === 'edit mode') assert.equal(await page.locator('.expense-form input[type=text]').first().inputValue(), 'Existing edit');
    } finally { release?.(); await context.close(); }
  });
  for (const kind of ['daily', 'trip']) await check(`${kind} POST binds expected owner to server auth`, async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage(); await setup(page);
      let binding;
      await page.route('**/api/transactions', route => {
        if (route.request().method() !== 'POST') return route.fallback();
        binding = route.request().headers()['x-nomica-request-owner'];
        return route.fulfill({ status: 409, json: { success: false, code: 'REQUEST_OWNER_CHANGED', message: '本次未建立交易，請回原帳號核對紀錄。' } });
      });
      await page.goto(new URL(kind === 'daily' ? '/add' : '/trips/trip', base).href, { waitUntil: 'networkidle' }); await fill(page, kind);
      await page.locator(kind === 'daily' ? '.form-container form button[type=submit]' : '.expense-form button[type=submit]').click();
      await page.getByRole('alert').first().waitFor({ timeout: 3000 });
      assert.equal(binding, 'test');
      assert((await storage(page, kind))?.requestId);
    } finally { await context.close(); }
  });
  assert.deepEqual(failures, [], failures.join('\n'));
};
