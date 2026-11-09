/* eslint-env browser */
// Real end-to-end smoke: Chromium -> Vite -> Flask -> PostgreSQL, with no API mocks.
// Runs only against loopback servers it starts itself, with loopback-only dev auth
// bypass and synthetic data. Names carry a run stamp so reruns on a kept DB stay valid.
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');

const frontend = path.resolve(__dirname, '..');
const root = path.resolve(frontend, '..');
const apiPort = process.env.E2E_API_PORT || '5055';
const webPort = process.env.E2E_WEB_PORT || '5199';
const web = `http://localhost:${webPort}`;
const api = `http://127.0.0.1:${apiPort}`;
const stamp = Date.now().toString(36);
const children = [];

assert(process.env.DATABASE_URL, 'DATABASE_URL must point to a disposable local database');
assert(/@(127\.0\.0\.1|localhost)[:/]/.test(process.env.DATABASE_URL), 'E2E DATABASE_URL must be loopback');

function start(command, args, options) {
  const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'], ...options });
  child.stdout.on('data', () => {});
  child.stderr.on('data', chunk => { if (process.env.E2E_VERBOSE) process.stderr.write(chunk); });
  children.push(child);
  return child;
}

async function waitFor(url) {
  for (let attempt = 0; attempt < 120; attempt++) {
    try { if ((await fetch(url)).ok) return; } catch { /* starting */ }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`Server did not start: ${url}`);
}

async function accountByName(page, name) {
  const response = await page.request.get(`${web}/api/assets`);
  const accounts = Object.values((await response.json()).data || {});
  return accounts.find(account => account.bank_name === name);
}

async function addExpense(page, { item, amount, pickAccount }) {
  await page.goto(`${web}/add`);
  await page.getByRole('button', { name: '手動新增支出', exact: true }).click();
  await page.locator('#transactionCategory').fill(item);
  await page.locator('#transactionAmount').fill(String(amount));
  if (pickAccount) {
    await page.locator('.picker-trigger').click();
    await page.getByRole('option', { name: new RegExp(pickAccount) }).click();
  }
  const created = page.waitForResponse(response =>
    response.url().endsWith('/api/transactions') && response.request().method() === 'POST');
  await page.getByRole('button', { name: '新增支出', exact: true }).click();
  const response = await created;
  assert.equal(response.status(), 201, `create failed: ${await response.text()}`);
}

async function run() {
  const python = process.env.E2E_PYTHON || 'python3';
  const env = {
    ...process.env,
    NOMICA_ENV: 'development', FLASK_ENV: 'development', DEV_AUTH_BYPASS: 'true',
    FRONTEND_BASE_URL: web, VITE_BACKEND_BASE_URL: `http://localhost:${apiPort}`, PORT: apiPort,
    NOMICA_AI_MODE: 'disabled', NOMICA_LINE_MODE: 'disabled',
  };
  start(python, ['web_app.py'], { cwd: root, env });
  start(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', 'localhost', '--port', webPort, '--strictPort'], {
    cwd: frontend,
    env: { ...process.env, VITE_DEV_AUTH_BYPASS: 'true', VITE_APP_API_URL: '', NOMICA_DEV_API_TARGET: api },
  });
  await waitFor(`${api}/healthcheck`);
  await waitFor(web);

  const browser = await chromium.launch({ headless: true, ...(process.env.UI_BROWSER_CHANNEL ? { channel: process.env.UI_BROWSER_CHANNEL } : {}) });
  try {
    const page = await (await browser.newContext({ viewport: { width: 390, height: 900 } })).newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));

    // 1. Identity: /api/auth/me must name the id that write routes receive.
    const me = await (await page.request.get(`${web}/api/auth/me`)).json();
    assert.match(me.data.user_id, /^[0-9a-f-]{36}$/, 'dev bypass exposes the internal user id');

    // 2. Create an account through the UI.
    const accountName = `E2E 錢包 ${stamp}`;
    await page.goto(`${web}/assets`);
    await page.getByRole('button', { name: '新增帳戶', exact: true }).click();
    await page.locator('#bankName').fill(accountName);
    await page.locator('#accountType').selectOption('cash');
    await page.locator('#balance').fill('1000');
    await page.locator('#currency').selectOption('TWD');
    await page.getByRole('button', { name: '新增', exact: true }).click();
    await expectEventually(async () => (await accountByName(page, accountName))?.balance === 1000, 'account created with balance 1000');

    // 3. Expense with an explicitly chosen account moves the balance.
    await addExpense(page, { item: `E2E 午餐 ${stamp}`, amount: 120, pickAccount: accountName });
    assert.equal((await accountByName(page, accountName)).balance, 880);

    // 4. The next expense defaults to the last-used account (no silent 不連動).
    await page.goto(`${web}/add`);
    await page.getByRole('button', { name: '手動新增支出', exact: true }).click();
    await expectEventually(async () =>
      (await page.locator('.picker-trigger').getAttribute('aria-label') || '').includes(accountName),
    'last-used account is preselected');
    await addExpense(page, { item: `E2E 咖啡 ${stamp}`, amount: 30 });
    assert.equal((await accountByName(page, accountName)).balance, 850);

    // 5. The ledger lists both entries.
    await page.goto(`${web}/transactions`);
    await page.getByText(`E2E 咖啡 ${stamp}`).waitFor();
    await page.getByText(`E2E 午餐 ${stamp}`).waitFor();

    // 6. Privacy: export, then delete the account (runs last: it removes the user).
    await require('./test-e2e-privacy.cjs')({ page, web, stamp, accountName, expectEventually });

    assert.deepEqual(errors, [], 'no uncaught browser exceptions');
    console.log('E2E smoke passed');
  } finally {
    await browser.close();
  }
}

async function expectEventually(check, message) {
  for (let attempt = 0; attempt < 40; attempt++) {
    if (await check()) return;
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out: ${message}`);
}

run()
  .catch(error => { console.error(error); process.exitCode = 1; })
  .finally(() => { for (const child of children) child.kill(); });
