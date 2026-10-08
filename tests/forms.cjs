// Run with Playwright available in NODE_PATH; no actual form submission leaves this test.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
fs.mkdirSync('reports/forms', {recursive:true});
const base=process.env.VISPO_BASE||'http://localhost:8774/';
(async()=>{
 const browser=await chromium.launch();let checks=0;
 const configs=[{file:'web',key:'6bcc394e730170',name:'6314162',phone:'6314170',email:'6314169',date:'6314167',time:'6314168',consent:'6314171'}, {file:'trial',key:'3b0215b2730171',name:'6314172',phone:'6314173',email:'6314174',date:'6314175',time:'6314177'}, {file:'inquiry',key:'2a26fe3c730176',name:'6314199',phone:'6314200',email:'6314201',message:'6314204'}];
 for(const width of [1440,390,320])for(const c of configs){
  const context=await browser.newContext({viewport:{width,height:900}});const page=await context.newPage();let posts=[];let oldRequests=[];
  await context.route('**/*',async route=>{const req=route.request();if(req.method()!=='GET'&&req.method()!=='HEAD'){posts.push({url:req.url(),data:req.postData()});return route.fulfill({status:200,contentType:'text/html',body:'<title>Intercepted test submission</title>'})}if(new URL(req.url()).hostname==='vispo-fit.com'){oldRequests.push(req.url());return route.abort()}return route.continue()});
  await page.clock.install({time:new Date('2026-10-09T00:00:00Z')});
  await page.goto(base+c.file+'.html');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'overflow');
  await page.locator('[data-review]').click();assert.equal(await page.locator('[data-confirm-panel]').isVisible(),false);
  await page.locator(`[name="field_${c.name}"]`).fill('検証 <img src=x onerror=alert(1)>');
  await page.locator(`[name="field_${c.phone}"]`).fill('00000000000');
  await page.locator(`[name="field_${c.email}"]`).fill('not-an-email');
  if(c.file==='web')await page.locator('[name="field_6314164"]').selectOption('1');
  if(c.date){
   const d=page.locator(`[name="field_${c.date}"]`), t=page.locator(`[name="field_${c.time}"]`);
   await d.fill('2026-10-08');assert.equal(await d.evaluate(e=>e.checkValidity()),false,'past');
   await d.fill('2026-10-15');assert.equal(await d.evaluate(e=>e.checkValidity()),false,'Thursday');
   if(c.file==='trial'){await d.fill('2026-10-09');assert.equal(await d.evaluate(e=>e.checkValidity()),false,'same-day trial')}
   await d.fill('2026-10-12');assert.equal(await t.locator('option').last().textContent(),'16:00','holiday limit');
   await d.fill('2026-10-10');assert.equal(await t.locator('option').last().textContent(),'16:00','weekend limit');
   assert.equal(await t.locator('option[value="0"]').textContent(),c.file==='trial'?'10:15':'10:00','backend time mapping');
   await d.fill('2026-10-13');assert.equal(await t.locator('option').last().textContent(),'20:00','weekday limit');
   await t.selectOption('0');
  }
  if(c.message)await page.locator(`[name="field_${c.message}"]`).fill('送信しない検証用の内容です。');
  await page.locator('[data-review]').click();assert.equal(await page.locator('[data-confirm-panel]').isVisible(),false,'invalid email');
  await page.locator(`[name="field_${c.email}"]`).fill('test@example.invalid');
  await page.locator('[data-review]').click();assert.equal(await page.locator('[data-confirm-panel]').isVisible(),false,'consent required');
  await page.locator('.form-consent input').check();
  await page.locator('[data-review]').click();assert.equal(await page.locator('[data-confirm-panel]').isVisible(),true);
  assert.equal(await page.locator('.form-summary img').count(),0,'escaped summary');
  assert.match(await page.locator('.form-summary').textContent(),/<img src=x/);
  assert.equal(posts.length,0,'review did not send');
  await page.locator('[data-edit]').click();assert.equal(await page.locator(`[name="field_${c.email}"]`).inputValue(),'test@example.invalid');
  await page.locator('[data-review]').click();
  if(width===390)await page.screenshot({path:`reports/forms/${c.file}-confirm.png`,fullPage:true});
  await Promise.all([page.waitForURL('https://ssl.form-mailer.jp/fm/service/Forms/complete'),page.locator('[data-send]').click()]);
  assert.equal(posts.length,1);assert.equal(posts[0].url,'https://ssl.form-mailer.jp/fm/service/Forms/complete');
  assert.match(posts[0].data,new RegExp('name="key"\\r\\n\\r\\n'+c.key));
  assert.match(posts[0].data,new RegExp('name="field_'+c.email+'"\\r\\n\\r\\ntest@example.invalid'));
  if(c.time)assert.match(posts[0].data,new RegExp('name="field_'+c.time+'"\\r\\n\\r\\n0'));
  if(c.consent)assert.match(posts[0].data,/name="field_6314171"\r\n\r\n0/);
  assert.equal(oldRequests.length,0);checks++;await context.close();
 }
 await browser.close();console.log(JSON.stringify({formScenarios:checks,externalSubmissionsSent:0,result:'PASS'}));
})().catch(e=>{console.error(e);process.exit(1)});
