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
