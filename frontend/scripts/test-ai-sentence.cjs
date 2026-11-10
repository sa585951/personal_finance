const assert = require('node:assert/strict');

const draft = (text, amount = '120') => ({
  intent: 'create_transaction', source: 'gemini', raw_text: text,
  transaction: { type: 'expense', title: '午餐', budget_category: '伙食', amount, description: '', currency: 'TWD' },
  missing_fields: [], errors: [],
});

module.exports = async function testAiSentence(browser, base, installMocks) {
  const failures = [];
  async function check(name, test) {
    try { await test(); console.log(`ai sentence: ${name} passed`); } catch (error) { failures.push(`${name}: ${error.message}`); }
  }
  async function open(status, handlers) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await installMocks(page);
    const calls = { ai: [], consent: [] };
    await page.route('**/api/ai/status', route => route.fulfill({ json: { success: true, data: status } }));
    await page.route('**/api/parse/local', route => route.fulfill({ json: { success: true, data: {
      parse_event_id: 'event', parse_result: { transaction: null, missing_fields: [], errors: [] } } } }));
    await page.route('**/api/ai/consent', route => { calls.consent.push(route.request().postDataJSON()); return route.fulfill({ json: { success: true, data: {} } }); });
    await page.route('**/api/parse/ai', route => { calls.ai.push(route.request().postDataJSON()); return handlers(route); });
    await page.goto(new URL('/add', base).href, { waitUntil: 'networkidle' });
    await page.locator('#sentenceInput').fill('跟朋友吃飯一百二');
    await page.locator('#sentenceInput').press('Enter');
    return { context, page, calls };
  }

  await check('no offer when AI is off', async () => {
    const { context, page } = await open({ available: false }, () => {});
    try {
      await page.getByText('沒有認出這句話').waitFor({ timeout: 4000 });
      assert.equal(await page.getByRole('button', { name: /用 AI 試試/ }).count(), 0);
    } finally { await context.close(); }
  });

  await check('first use asks for consent, then drafts with one request id', async () => {
    const { context, page, calls } = await open(
      { available: true, consented: false, remaining: 20, notice: 'Google Gemini 說明文字' },
      route => route.fulfill({ json: { success: true, data: { parse_event_id: 'e2', parse_result: draft('x') } } }),
    );
    try {
      await page.getByRole('button', { name: /用 AI 試試/ }).click();
      await page.locator('.swal2-popup').getByText('Google Gemini 說明文字').waitFor({ timeout: 4000 });
      assert.equal(calls.ai.length, 0, 'nothing is sent before consent');
      await page.locator('.swal2-confirm').click();
      await page.getByText('已填入下方欄位').waitFor({ timeout: 4000 });
      assert.deepEqual(calls.consent, [{ consented: true }]);
      assert.equal(calls.ai.length, 1);
      assert.match(calls.ai[0].client_request_id, /^[a-f0-9-]{36}$/);
    } finally { await context.close(); }
  });

  await check('declining consent sends nothing', async () => {
    const { context, page, calls } = await open(
      { available: true, consented: false, remaining: 20, notice: 'notice' }, route => route.abort());
    try {
      await page.getByRole('button', { name: /用 AI 試試/ }).click();
      await page.locator('.swal2-cancel').click();
      assert.equal(calls.consent.length + calls.ai.length, 0);
    } finally { await context.close(); }
  });

  await check('daily limit shows the server message and hides the offer', async () => {
    const { context, page } = await open(
      { available: true, consented: true, remaining: 1 },
      route => route.fulfill({ status: 429, json: { success: false, code: 'AI_DAILY_LIMIT', message: '今天的 AI 解析次數已用完' } }),
    );
    try {
      await page.getByRole('button', { name: /用 AI 試試/ }).click();
      await page.getByText('今天的 AI 解析次數已用完').waitFor({ timeout: 4000 });
      assert.equal(await page.getByRole('button', { name: /用 AI 試試/ }).count(), 0);
    } finally { await context.close(); }
  });

  if (failures.length) throw new Error(failures.join('\n'));
};
