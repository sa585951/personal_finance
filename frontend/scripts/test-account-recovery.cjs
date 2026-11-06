/* global sessionStorage, Storage */
const assert = require('node:assert/strict');
module.exports = async function testAccountRecovery(browser, base, installMocks) {
  const failures = [];
  async function check(name, test) {
    if (process.env.ASSET_RECOVERY_CASE && !name.includes(process.env.ASSET_RECOVERY_CASE)) return;
    try { await test(); console.log(`account recovery: ${name} passed`); }
    catch (error) { failures.push(name+': '+error.message); }
  }
  const stored = page => page.evaluate(() => {
    const raw=sessionStorage.getItem('nomica-pending:test:account:create'); return raw?JSON.parse(raw):null;
  });
  async function fill(page) {
    await page.locator('.account-form #bankName').fill('Frozen account');
    await page.locator('.account-form #balance').fill('100');
  }
  for (const status of ['lost', 400, 401, 409, 500, 'success']) await check(String(status), async () => {
    const context=await browser.newContext();
    try {
      const page=await context.newPage();const errors=await installMocks(page);const sends=[];
      await page.route('**/api/assets', route => {
        if (route.request().method()!=='POST') return route.fallback();
        sends.push(route.request().postDataJSON());
        if (sends.length>1||status==='success') return route.fulfill({status:sends.length>1?200:201,json:{success:true,message:'Saved',data:{account_id:'new-account',transaction_id:null},replayed:sends.length>1}});
        if (status==='lost') return route.abort('failed');
        return route.fulfill({status,json:{success:false,message:'Controlled account failure'}});
      });
      await page.goto(new URL('/assets?action=account',base).href,{waitUntil:'networkidle'});await fill(page);
      await page.locator('.account-form button[type=submit]').click();
      if (status===400||status==='success') {
        if (status === 400) {
          await page.getByText('Controlled account failure', {exact: true}).waitFor();
        } else {
          await page.locator('.account-form').waitFor({state: 'detached'});
        }
        assert.equal(sends.length,1);assert.match(sends[0].client_request_id||'',/^[a-f0-9-]{36}$/);
        assert.equal(await stored(page),null);
      } else {
        await page.getByRole('status',{name:'待確認帳戶'}).waitFor({timeout:3000});
        assert.equal((await stored(page)).requestId,sends[0].client_request_id);
        await page.goto(new URL('/assets',base).href,{waitUntil:'networkidle'});
        const panel=page.getByRole('status',{name:'待確認帳戶'});await panel.waitFor({timeout:3000});
        assert.equal(sends.length,1,'reload never posts');
        assert((await panel.innerText()).includes('Frozen account'));
        assert.equal(await panel.getByRole('button',{name:'結束這次待確認請求'}).count(),0);
        await panel.getByRole('button',{name:'以原資料重試'}).click();await panel.waitFor({state:'detached'});
        assert.deepEqual(sends[1],sends[0]);assert.equal(await stored(page),null);
      }
      assert.deepEqual(errors,[]);
    } finally { await context.close(); }
  });
  await check('double-click submits once with frozen intent before auth await',async()=>{
    const context=await browser.newContext();let release;
    try {
      const page=await context.newPage();await installMocks(page);const sends=[];
      await page.route('**/api/assets',route=>{
        if(route.request().method()!=='POST')return route.fallback();sends.push(route.request().postDataJSON());return route.abort('failed');
      });
      await page.goto(new URL('/assets?action=account',base).href,{waitUntil:'networkidle'});await fill(page);
      let enter;const entered=new Promise(r=>enter=r);const gate=new Promise(r=>release=r);
      await page.route('**/api/auth/me',async route=>{enter();await gate;return route.fulfill({json:{success:true,data:{user_id:'test'}}});});
      await page.locator('.account-form button[type=submit]').dblclick();
      await Promise.race([entered,new Promise((_,reject)=>setTimeout(()=>reject(new Error('Missing auth preflight')),3000))]);
      await page.locator('.account-form #balance').fill('999');
      release();await page.getByRole('status',{name:'待確認帳戶'}).waitFor({timeout:3000});
      assert.equal(sends.length,1);assert.equal(sends[0].balance,100);assert.equal((await stored(page)).payload.balance,100);
    } finally {release?.();await context.close();}
  });
  await check('changed owner blocks without POST',async()=>{
    const context=await browser.newContext();
    try{
      const page=await context.newPage();await installMocks(page);let sends=0;
      await page.route('**/api/assets',route=>{if(route.request().method()==='POST')sends++;return route.fallback();});
      await page.goto(new URL('/assets?action=account',base).href,{waitUntil:'networkidle'});await fill(page);
      await page.route('**/api/auth/me',route=>route.fulfill({json:{success:true,data:{user_id:'other'}}}));
      await page.locator('.account-form button[type=submit]').click();await page.getByRole('alert').first().waitFor({timeout:3000});
      assert.equal(sends,0);assert.equal(await stored(page),null);
    }finally{await context.close();}
  });
  await check('reload ignores another owner and another command scope', async () => {
    const context = await browser.newContext();
    try {
      const page = await context.newPage();
      await installMocks(page);
      const old = {requestId: '5ba8d56b-f3b8-4ea3-946d-603624db4cfa', payload: {bank_name: 'Other owner'}};
      const transfer = {requestId: 'aecc5f40-d809-43e2-8cd9-09a35c8f0613', payload: {amount: 30}};
      await page.goto(new URL('/assets', base).href, {waitUntil: 'networkidle'});
      await page.evaluate(({old, transfer}) => {
        sessionStorage.setItem('nomica-pending:other:account:create', JSON.stringify(old));
        sessionStorage.setItem('nomica-pending:test:transfer', JSON.stringify(transfer));
      }, {old, transfer});
      await page.goto(new URL('/assets?action=account', base).href, {waitUntil: 'networkidle'});
      await page.locator('.account-form #bankName').waitFor();
      assert.equal(await page.getByRole('status', {name: '待確認帳戶'}).count(), 0);
      assert.equal(await stored(page), null);
      assert.deepEqual(await page.evaluate(() => [
        JSON.parse(sessionStorage.getItem('nomica-pending:other:account:create')),
        JSON.parse(sessionStorage.getItem('nomica-pending:test:transfer')),
      ]), [old, transfer]);
    } finally {
      await context.close();
    }
  });
  for(const mode of ['read','write'])await check('storage '+mode+' fails closed',async()=>{
    const context=await browser.newContext();
    try{
      const page=await context.newPage();await installMocks(page);let sends=0;
      await page.route('**/api/assets',route=>{if(route.request().method()==='POST')sends++;return route.fallback();});
      await page.addInitScript(mode=>{const method=mode==='read'?'getItem':'setItem';const old=Storage.prototype[method];Storage.prototype[method]=function(key,...args){if(key.startsWith('nomica-pending:'))throw new DOMException('Controlled storage failure','SecurityError');return old.call(this,key,...args);};},mode);
      await page.goto(new URL('/assets?action=account',base).href,{waitUntil:'networkidle'});
      if(mode==='write'){await fill(page);await page.locator('.account-form button[type=submit]').click();}
      await page.getByRole('alert').first().waitFor({timeout:3000});assert.equal(sends,0);
    }finally{await context.close();}
  });
  assert.deepEqual(failures,[],failures.join('\n'));
};
