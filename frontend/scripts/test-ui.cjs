/* eslint-env browser */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');

const frontend = path.resolve(__dirname, '..');
const base = new URL(process.env.UI_BASE_URL || 'http://127.0.0.1:4174');
// UI tests must never navigate to production or send real financial mutations.
assert(['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname), 'UI_BASE_URL must be loopback');
assert.equal(base.protocol, 'http:');
const output = path.join(frontend, 'test-results/ui');
const portfolio = {
  id: 'sample', name: '測試投資組合', base_currency: 'TWD', is_active: true,
  holdings: [{ id: 'holding', name: '測試 ETF', account_id: 'investment', target_weight: 1, recorded_cost: 1000, cost_entries: [], is_active: true }],
  snapshots: [],
};
const assets = {
  card: { id: 'card', bank_name: '測試信用卡', account_type: 'credit_card', currency: 'TWD', balance: 0, track_balance: true },
  investment: { id: 'investment', bank_name: '測試投資帳戶', account_type: 'investment', currency: 'TWD', balance: 1000, track_balance: true },
};
const today = new Date().toISOString().slice(0, 10);
const trip = { id: 'trip', name: '測試旅行', destination: 'Tokyo', start_date: today, end_date: today, base_currency: 'TWD', default_currency: 'JPY', members: [], include_in_monthly_report: false };
const routes = [
  ['/', '.monthly-overview-card'], ['/assets', '.accounts-list'], ['/transactions', '.records-section'],
  ['/add?mode=receipt', '.receipt-flow'], ['/analysis', '.analysis-screen'], ['/trips', '.trip-list-view'],
  ['/account', '.account-page'], ['/budgets', '.budget-screen'], ['/allocation', '.portfolio-section'],
];

async function ready() {
  for (let attempt = 0; attempt < 60; attempt++) {
    try { if ((await fetch(base)).ok) return; } catch { /* Vite is starting. */ }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Local Vite server did not start');
}
async function noOverflow(page) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `Overflow: ${page.url()}`);
}
async function themeColor(page, selector, token, property = 'color') {
  assert.equal(await page.locator(selector).first().evaluate((el, [name, property]) => {
    const probe = document.createElement('span'); probe.style[property] = `var(${name})`; el.append(probe);
    const expected = getComputedStyle(probe)[property]; probe.remove();
    return getComputedStyle(el)[property] === expected;
  }, [token, property]), true, `${selector} ${property} must use ${token}`);
}
async function installMocks(page) {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (!url.pathname.startsWith('/api/')) return url.origin === base.origin ? route.continue() : route.abort();
    // No request under /api/ reaches Vite's production proxy, even for unknown endpoints.
    const method = route.request().method();
    if (method !== 'GET') return route.fulfill({ status: 405, json: { success: false, message: 'UI test: writes are blocked' } });
    let data = [];
    if (url.pathname === '/api/auth/me') data = { name: 'Test', user_id: 'test' };
    if (url.pathname === '/api/capabilities') data = { ai_parse: false, line_interactions: false };
    if (url.pathname === '/api/assets') data = assets;
    if (url.pathname === '/api/dashboard/overview') data = { transactions: [], monthly_report_transactions: [], trips: [] };
    if (url.pathname === '/api/portfolios') data = [portfolio];
    if (url.pathname === '/api/portfolios/sample') data = portfolio;
    if (url.pathname === '/api/trips') data = [trip];
    if (url.pathname === '/api/transactions') data = [{ id: 'transaction', date: today, type: url.searchParams.get('type') || 'expense', amount: 120, currency: 'TWD', category: '測試消費', budget_category: 'food', can_delete: false, can_edit: false }];
    return route.fulfill({ json: { success: true, data, pagination: { total_count: Array.isArray(data) ? data.length : 0, has_more: false, next_cursor: null } } });
  });
  return errors;
}

async function testCurrencyDecimalInputs(browser) {
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    await installMocks(page);
    await page.goto(`${base.origin}/login`, { waitUntil: 'networkidle' });
    await page.evaluate(async () => {
      const { createApp } = await import('/node_modules/.vite/deps/vue.js');
      const { default: Daily } = await import('/src/components/budgets/TransactionForm.vue');
      const { default: Trip } = await import('/src/components/trips/TripExpensePanel.vue');
      const dailyRoot = document.createElement('div'); dailyRoot.id = 'money-daily'; document.body.append(dailyRoot);
      const tripRoot = document.createElement('div'); tripRoot.id = 'money-trip'; document.body.append(tripRoot);
      const daily = createApp(Daily, { draft: { currency: 'USD', amount: 1.23, type: 'expense' } }).mount(dailyRoot);
      const trip = createApp(Trip, { expense: { item: 'Test', amount: 1.23, original_currency: 'USD',
        exchange_rate: 32, split_mode: 'custom', split_member_ids: ['m'], split_allocations: { m: 1.23 } },
        members: [{ id: 'm', display_name: 'Test' }] }).mount(tripRoot);
      window.moneyInputTest = { daily, trip };
    });
    await page.waitForFunction(() => window.moneyInputTest.daily.assetsLoaded && window.moneyInputTest.daily.budgetCategoriesLoaded);
    const daily = page.locator('#money-daily #transactionAmount');
    const trip = page.locator('#money-trip .expense-form input[type=number]').first();
    const share = page.locator('#money-trip .custom-split-row input');
    const valid = async (input, value) => { await input.fill(value); return input.evaluate(el => el.checkValidity()); };
    assert.deepEqual([await valid(daily, '1.23'), await valid(trip, '0.01'), await valid(share, '1.23')], [true, true, true]);
    assert.equal(await valid(share, '0'), true);
    assert.equal(await valid(daily, '0.001'), false);
    assert.equal(await valid(trip, '-1'), false);
    assert.equal(await valid(daily, '0'), false);
    await page.evaluate(() => { window.moneyInputTest.daily.newTransaction.original_currency = 'JPY'; });
    assert.equal(await valid(daily, '1.23'), false);
    assert.equal(await valid(daily, '1'), true);
    await page.evaluate(() => { window.moneyInputTest.daily.newTransaction.original_currency = 'EUR'; });
    assert.equal(await valid(daily, '0.01'), true);
  } finally { await context.close(); }
}

async function testReportCurrencyRefusal(browser) {
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    await installMocks(page);
    const message = '目前個人報表僅支援 TWD；原始資料已保留，請勿直接更改歷史幣別';
    const reject = route => route.fulfill({ status: 400, json: {
      success: false, code: 'REPORT_CURRENCY_UNSUPPORTED', message,
    } });
    await page.route('**/api/dashboard/overview', reject);
    await page.route('**/api/transactions*', route => {
      return new URL(route.request().url()).searchParams.get('monthly_report') === 'true'
        ? reject(route) : route.fallback();
    });
    await page.goto(`${base.origin}/`, { waitUntil: 'networkidle' });
    const homeHasReason = (await page.locator('body').innerText()).includes(message);
    await page.goto(`${base.origin}/analysis`, { waitUntil: 'networkidle' });
    assert((await page.locator('.state-message.error').innerText()).includes(message));
    const analysisHidesTotals = await page.locator('.summary-card').count() === 0;
    assert.deepEqual({ homeHasReason, analysisHidesTotals }, { homeHasReason: true, analysisHidesTotals: true });
  } finally {
    await context.close();
  }
}

async function testUntrustedDialogs(browser) {
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    const errors = await installMocks(page);
    await page.goto(`${base.origin}/login`, { waitUntil: 'domcontentloaded' });
    await page.evaluate(async () => {
      const { default: Swal } = await import('/node_modules/sweetalert2/dist/sweetalert2.esm.all.js');
      const { default: TripView } = await import('/src/views/TripsView.vue');
      window.dialogAttack = 0;
      const hostile = '</textarea><img src=x onerror="window.dialogAttack++"><svg onload="window.dialogAttack++">';
      window.dialogTest = { Swal, TripView, hostile };
      await TripView.methods.copySettlementSummary.call({
        buildSettlementSummaryText: () => hostile,
        writeTextToClipboard: async () => { throw new Error('clipboard unavailable'); },
        $swal: Swal,
      });
    });
    assert.equal(await page.locator('.swal-copy-textarea').inputValue(), await page.evaluate(() => window.dialogTest.hostile));
    assert.equal(await page.locator('.swal2-popup img[src=x], .swal2-popup svg[onload]').count(), 0);
    await page.evaluate(() => {
      const { Swal, TripView, hostile } = window.dialogTest;
      Swal.close();
      window.deleteDialogResult = TripView.methods.deleteSelectedTrip.call({ selectedTrip: { name: hostile }, $swal: Swal });
    });
    await page.locator('.swal2-input').waitFor();
    assert((await page.locator('.swal2-html-container').innerText()).includes(await page.evaluate(() => window.dialogTest.hostile)));
    assert.equal(await page.locator('.swal2-popup img[src=x], .swal2-popup svg[onload]').count(), 0);
    await page.locator('.swal2-cancel').click();
    await page.evaluate(() => window.deleteDialogResult);
    assert.equal(await page.evaluate(() => window.dialogAttack), 0);
    assert.deepEqual(errors, []);
  } finally {
    await context.close();
  }
}

async function testCookieAuthNavigation(browser) {
  for (const authenticated of [true, false]) {
    const context = await browser.newContext();
    try {
      const page = await context.newPage();
      const requests = [];
      await page.addInitScript(() => localStorage.setItem('authToken', 'retired-local-token'));
      await installMocks(page);
      await page.route('**/api/auth/me', route => {
        requests.push(route.request().headers());
        return route.fulfill({ status: authenticated ? 200 : 401,
          json: authenticated ? { success: true, data: { user_id: 'test', name: 'Test' } } : { message: 'Session invalid' } });
      });
      await page.goto(`${base.origin}/auth-callback?token=retired-url-token&redirect=%2Ftransactions`, { waitUntil: 'domcontentloaded' });
      try {
        await page.waitForURL(url => authenticated ? url.pathname === '/transactions' : url.pathname === '/login');
      } catch (error) {
        throw new Error(`Cookie navigation auth=${authenticated}, path=${new URL(page.url()).pathname}, body=${(await page.locator('body').innerText()).slice(0, 240)}`, { cause: error });
      }
      assert.equal(await page.evaluate(() => localStorage.getItem('authToken')), null);
      assert(requests.length > 0);
      assert(requests.every(headers => !headers.authorization), 'Web must not send a retired bearer token');
      assert(!page.url().includes('retired-url-token'));
      assert.equal(await page.evaluate(async () => {
        const { safeRedirectPath } = await import('/src/utils/authNavigation.js');
        return ['//evil.example', '/%5cevil.example', '/%2fevil.example', '/%0aevil.example']
          .every(path => safeRedirectPath(path) === '/');
      }), true);
    } finally { await context.close(); }
  }
}

async function testDisabledAiKeepsManualEntry(browser) {
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    const errors = await installMocks(page);
    await page.goto(`${base.origin}/add`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('status').filter({ hasText: '解析暫停開放' }).waitFor();
    await page.getByRole('button', { name: '手動新增支出', exact: true }).click();
    await page.locator('.manual-heading').waitFor();
    assert((await page.locator('.manual-heading').innerText()).includes('手動新增支出'));
    assert.deepEqual(errors, []);
  } finally { await context.close(); }
}

(async () => {
  let server, browser;
  try {
    fs.mkdirSync(output, { recursive: true });
    if (!process.env.UI_BASE_URL) {
      server = spawn(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', base.hostname, '--port', base.port, '--strictPort'], {
        cwd: frontend, stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env, VITE_APP_API_URL: '', VITE_DEV_AUTH_BYPASS: 'false' },
      });
      server.stdout.on('data', () => {});
      server.stderr.on('data', chunk => process.stderr.write(chunk));
    }
    await ready();
    browser = await chromium.launch({ headless: true, ...(process.env.UI_BROWSER_CHANNEL ? { channel: process.env.UI_BROWSER_CHANNEL } : {}) });
    await require('./test-account-recovery.cjs')(browser, base, installMocks);
    if (process.env.ASSET_RECOVERY_ONLY === 'true') return;
    await require('./test-transaction-recovery.cjs')(browser, base, installMocks);
    await testCurrencyDecimalInputs(browser);
    await testReportCurrencyRefusal(browser);
    await testUntrustedDialogs(browser);
    await testCookieAuthNavigation(browser);
    await testDisabledAiKeepsManualEntry(browser);
    for (const width of [320, 390, 430, 768, 1280]) for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
      await context.addInitScript(value => {
        if (!localStorage.getItem('nomica-theme')) localStorage.setItem('nomica-theme', value);
      }, theme);
      const page = await context.newPage();
      const errors = await installMocks(page);
      for (const [route, selector] of routes) {
        await page.goto(new URL(route, base).href);
        await page.locator(selector).first().waitFor();
        for (const surface of await page.locator('.app-surface').all()) {
          assert.equal(await surface.evaluate(el => getComputedStyle(el).borderRadius), '16px');
        }
        if (await page.locator('.app-surface').count()) await themeColor(page, '.app-surface', '--card-bg', 'backgroundColor');
        if (route === '/transactions') {
          await page.locator('.app-pagination').waitFor();
          assert(await page.getByRole('button', { name: '前往上一頁' }).isDisabled());
          assert(await page.getByRole('button', { name: '前往下一頁' }).isDisabled());
        }
        if (route === '/trips') await page.locator('.trip-card').waitFor();
        if (route === '/account') await themeColor(page, '.account-page', '--text-color');
        if (route === '/assets') {
          await page.locator('.group-header').filter({ hasText: '信用卡' }).click();
          await page.locator('.billing-summary').waitFor();
          await themeColor(page, '.billing-summary', '--warning-text');
          await themeColor(page, '.transfer-history .section-heading', '--text-color');
          await page.getByRole('button', { name: '新增帳戶', exact: true }).click();
          await themeColor(page, '.action-tab.active', '--primary-color');
          await page.locator('#bankName').focus();
          assert.equal(await page.locator('#bankName').evaluate(el => getComputedStyle(el).outlineStyle), 'solid');
        }
        if (route === '/allocation') {
          await page.getByRole('button', { name: '新增組合', exact: true }).click();
          await page.locator('.app-form-fields').waitFor();
          const field = await page.locator('.app-form-fields input').evaluate(el => ({ height: el.getBoundingClientRect().height, radius: getComputedStyle(el).borderRadius }));
          assert(field.height >= 44); assert.equal(field.radius, '12px');
        }
        await noOverflow(page);
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: path.join(output, `${width}-${theme}-${route.split('?')[0].replaceAll('/', '-') || 'home'}.png`), fullPage: true });
      }
      // All four allocation tabs exercise the extracted form styles with populated mock data.
      await page.goto(new URL('/allocation/sample', base).href);
      await page.locator('.detail-tabs').waitFor();
      await page.locator('.panel-toggle').click();
      await page.locator('.app-form-fields').waitFor(); await noOverflow(page);
      for (const [tab, form] of [['投入成本', '.app-form-fields'], ['資產快照', '.app-form-fields'], ['投入試算', '.app-field-labels']]) {
        await page.locator('.detail-tabs').getByRole('button', { name: tab }).click();
        if (tab !== '投入試算') await page.locator('.panel-toggle').click();
        await page.locator(form).waitFor(); await noOverflow(page);
      }
      // Theme persistence, keyboard focus, and menu dismissal.
      await page.goto(new URL('/add?mode=receipt', base).href);
      await page.locator('.receipt-flow').waitFor();
      await page.locator('.account-button').focus(); await page.keyboard.press('Enter');
      await page.locator('.account-menu').waitFor();
      await page.locator('.theme-toggle').click();
      assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), theme === 'light' ? 'dark' : 'light');
      await page.keyboard.press('Escape'); assert.equal(await page.locator('.account-menu').count(), 0);
      await page.reload(); await page.locator('.receipt-flow').waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), theme === 'light' ? 'dark' : 'light');
      await page.locator('.account-button').click(); await page.locator('.scanner-placeholder').click();
      assert.equal(await page.locator('.account-menu').count(), 0);
      // Camera denial must retain the image and manual-entry fallback.
      await page.evaluate(() => { navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Denied', 'NotAllowedError'); }; });
      await page.getByRole('button', { name: '開啟相機' }).click();
      await page.getByRole('alert').waitFor();
      assert(await page.getByRole('button', { name: '選擇圖片' }).isEnabled());
      assert(await page.getByRole('button', { name: '改用手動記帳' }).isEnabled());
      await noOverflow(page);
      assert.deepEqual(errors, [], 'No uncaught browser exceptions');
      console.log(`${width}px ${theme}: page shells, allocation forms, theme/menu/focus, camera fallback passed`);
      await context.close();
    }
    // Explicit loading/error/retry state, without contacting real services.
    const page = await browser.newPage(); await installMocks(page);
    let release; const gate = new Promise(resolve => { release = resolve; }); let calls = 0;
    await page.route('**/api/assets', async route => {
      calls++;
      if (calls === 1) { await gate; return route.fulfill({ status: 503, json: { success: false, message: 'Test failure' } }); }
      return route.fulfill({ json: { success: true, data: assets } });
    });
    await page.goto(new URL('/assets', base).href);
    await page.locator('.state-spinner').waitFor(); release();
    await page.locator('.app-state-panel.error').waitFor();
    await page.getByRole('button', { name: '重新整理', exact: true }).click();
    await page.locator('.accounts-list').waitFor(); assert.equal(calls, 2);
    console.log('Loading/error/retry passed. Screenshots: frontend/test-results/ui');
  } finally {
    if (browser) await browser.close();
    if (server) server.kill('SIGTERM');
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
