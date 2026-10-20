import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const headers={'X-Fincept-Request':'1',Origin:'http://127.0.0.1:5180'};
const pageErrors=new WeakMap<Page,string[]>();
test.beforeEach(({page})=>{const errors:string[]=[];pageErrors.set(page,errors);page.on('pageerror',error=>errors.push(error.message));});
test.afterEach(({page})=>{expect(pageErrors.get(page)||[], 'No unhandled browser errors').toEqual([]);});
test.beforeAll(()=>{const db=path.resolve('test-results/auth-e2e.sqlite3');if(fs.existsSync(db))execFileSync(process.env.PYTHON_BIN||'python',['-c',"import sqlite3,sys;p=sys.argv[1];assert p.endswith('/test-results/auth-e2e.sqlite3');c=sqlite3.connect(p);c.execute('DELETE FROM rate_limits');c.commit();c.close()",db]);});
async function account(page:Page){const r=await page.request.post('/api/auth/register',{headers,data:{full_name:'Assistant User',email:`assistant-${Date.now()}-${Math.random()}@example.com`,password:'Fincept!2026',confirm_password:'Fincept!2026',accepted_terms:true}});expect(r.status()).toBe(201);}
async function open(page:Page){await account(page);await page.goto('/ai-assistant');await expect(page.getByRole('heading',{name:'How can I help with your finances?'})).toBeVisible();}
const composer=(page:Page)=>page.getByRole('textbox',{name:'Ask anything about your finances',exact:true});
async function capture(page:Page,name:string){await page.screenshot({path:`docs/assistant-qa/implemented-${name}.png`,fullPage:true,animations:'disabled'});}

test('real unavailable provider: suggestions, persistence, retry, history search and refresh',async({page})=>{
 await open(page);
 await expect(page.getByRole('link',{name:'AI Assistant',exact:true})).toHaveAttribute('aria-current','page');
 await expect(page.locator('.application-header')).toContainText('Your personal financial companion');
 const status=await (await page.request.get('/api/assistant/status')).json();expect(status.configured).toBe(false);
 await expect(page.locator('.ai-disclosure')).toContainText('server-side AI provider');
 await expect(page.getByRole('button',{name:'Send ↑',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:/Understand my spending/}).click();
 await expect(composer(page)).toHaveValue('Where did most of my money go this month?');
 await composer(page).press('Enter');
 await expect(page.locator('.ai-error')).toContainText('configuration is required');
 await expect(page.locator('.ai-message-user')).toHaveCount(1);await expect(page.locator('.ai-message-assistant')).toHaveCount(0);
 await expect(composer(page)).toHaveValue('Where did most of my money go this month?');
 const cid=new URL(page.url()).searchParams.get('conversation');expect(cid).toBeTruthy();
 let detail=await (await page.request.get('/api/assistant/conversations/'+cid)).json();const key=detail.request.id;expect(detail.messages).toHaveLength(1);
 await page.locator('.ai-error').getByRole('button',{name:'Try again'}).click();await expect(page.locator('.ai-error')).toBeVisible();
 await expect(page.locator('.ai-typing')).toHaveCount(0);
 detail=await (await page.request.get('/api/assistant/conversations/'+cid)).json();expect(detail.request.id).toBe(key);expect(detail.messages).toHaveLength(1);
 await page.reload();await expect(page.locator('.ai-error')).toContainText('configuration is required');await expect(page.locator('.ai-message-user')).toHaveCount(1);
 await page.getByRole('button',{name:'History',exact:true}).click();const history=page.getByRole('complementary',{name:'Conversation history'});
 await expect(history.locator('nav button')).toHaveCount(1);await expect(history.locator('nav button')).toHaveAttribute('aria-current','page');
 await history.getByRole('textbox',{name:'Search conversations'}).fill('not-present');await expect(history).toContainText('No conversations match');
 await history.getByRole('textbox',{name:'Search conversations'}).fill('money');await expect(history.locator('nav button')).toHaveCount(1);
 await capture(page,'real-unavailable-history');
 await page.locator('.ai-header-actions').getByRole('button',{name:'+ New Chat',exact:true}).click();await expect(composer(page)).toHaveValue('');await expect(page.locator('.ai-message-user')).toHaveCount(0);
 await history.locator('nav button').click();await expect(page.locator('.ai-message-user')).toHaveCount(1);await expect(composer(page)).toHaveValue('Where did most of my money go this month?');
});

test('real saved user text and conversation previews respect shared privacy',async({page})=>{
 await open(page);await composer(page).fill('Can I plan around ৳52,000 income or fifty thousand taka?');await composer(page).press('Enter');await expect(page.locator('.ai-error')).toBeVisible();
 await page.getByRole('button',{name:'History',exact:true}).click();await expect(page.locator('.ai-history nav button')).toHaveCount(1);
 await page.getByRole('button',{name:'Hide balances',exact:true}).click();
 expect(await page.locator('.assistant-page').innerText()).not.toMatch(/52,000|fifty thousand/);
 await expect(page.locator('.ai-message-user')).toContainText('Message text hidden');await expect(page.locator('.ai-history nav button')).toContainText('Preview hidden');
 await capture(page,'privacy');await page.reload();await expect(page.getByRole('button',{name:'Show balances',exact:true})).toBeVisible();await expect(page.locator('.ai-message-user')).toContainText('Message text hidden');
 await page.getByRole('button',{name:'Show balances',exact:true}).click();await expect(page.locator('.ai-message-user')).toContainText('৳52,000');
});

test('composer whitespace, Shift+Enter, long input, network errors and retry IDs',async({page})=>{
 await open(page);await composer(page).fill('   ');await expect(page.getByRole('button',{name:'Send ↑',exact:true})).toBeDisabled();
 await composer(page).fill('My question');await composer(page).press('Shift+Enter');await composer(page).press('x');await expect(composer(page)).toHaveValue('My question\nx');
 await page.route('**/api/assistant/conversations/*/messages?*',route=>route.abort());
 await composer(page).press('Enter');await expect(page.locator('.ai-error')).toContainText('Connection interrupted');await expect(composer(page)).toHaveValue('My question\nx');
 await expect(page.locator('.ai-typing')).toHaveCount(0);await expect(page.locator('.ai-message-user')).toHaveCount(0); // rejected network operation is not a sent receipt
 await page.unroute('**/api/assistant/conversations/*/messages?*');await page.locator('.ai-error').getByRole('button',{name:'Try again'}).click();
 await expect(page.locator('.ai-error')).toContainText('configuration is required');await expect(page.locator('.ai-message-user')).toHaveCount(1);
});

test('explicit UI-only provider fixture: pending, successful rendering, summary privacy and safe HTML',async({page})=>{
 await account(page);expect((await page.request.post('/api/overview/demo',{headers})).status()).toBe(201);
 const analytics=await (await page.request.get('/api/insights?dataset=demo')).json();
 await page.route('**/api/assistant/status?*',route=>route.fulfill({json:{configured:true,connection_verified:false,message:'Explicit UI-only provider test fixture'}}));
 let calls=0;let release:()=>void=()=>{};const wait=new Promise<void>(resolve=>{release=resolve;});
 await page.route('**/api/assistant/conversations/*/messages?*',async route=>{
  calls++;const body=route.request().postDataJSON();await wait;
  // Deliberate fixture, NOT a live model call or persistence test. Summary uses actual isolated-demo backend calculations.
  await route.fulfill({json:{request:{id:body.request_key,status:'completed'},messages:[{id:'ui-user',role:'user',request_id:body.request_key,content:body.content,created_at:'2026-10-20T10:00:00Z',summary:null},{id:'ui-assistant',role:'assistant',request_id:body.request_key,content:'UI TEST FIXTURE ONLY: recorded expenses ৳38,200. <img src=x onerror=alert(1)>',created_at:'2026-10-20T10:00:01Z',summary:{title:'Financial Summary',period:analytics.range,...analytics.summary}}]}});
 });
 await page.goto('/ai-assistant?dataset=demo');await composer(page).fill('Summarize cash flow');await composer(page).press('Enter');
 await expect(page.locator('.ai-typing')).toBeVisible();await expect(page.getByRole('button',{name:'Sending…',exact:true})).toBeDisabled();await composer(page).press('Enter');await expect.poll(()=>calls).toBe(1);
 await capture(page,'pending-test-fixture');release();await expect(page.locator('.ai-message-assistant')).toBeVisible();await expect(page.locator('.ai-typing')).toHaveCount(0);
 await expect(page.locator('.ai-message-assistant img')).toHaveCount(0);await expect(page.locator('.ai-message-assistant')).toContainText('<img src=x');
 await expect(page.locator('.ai-financial-summary')).toContainText('৳52,000');await expect(page.locator('.ai-financial-summary')).toContainText('+৳13,800');
 await capture(page,'success-test-fixture');await page.getByRole('button',{name:'Hide balances',exact:true}).click();expect(await page.locator('.assistant-page').innerText()).not.toMatch(/38,200|52,000|13,800/);
 await page.locator('.ai-financial-summary').getByRole('link',{name:'View Details →'}).click();await expect(page).toHaveURL(/\/insights\?.*dataset=demo.*period=custom/);
});

test('history/network load failure offers a working reload without breaking navigation',async({page})=>{
 await account(page);await page.route('**/api/assistant/conversations?*',r=>r.abort());await page.goto('/ai-assistant');await page.getByRole('button',{name:'History',exact:true}).click();
 await expect(page.locator('.ai-history [role=alert]')).toBeVisible();await page.unroute('**/api/assistant/conversations?*');await page.getByRole('button',{name:'Reload history'}).click();await expect(page.locator('.ai-history')).toContainText('Your conversations will appear');
 await page.getByRole('link',{name:'Transactions',exact:true}).click();await expect(page.locator('.transactions-page')).toBeVisible();
});

for(const size of [{width:1440,height:900},{width:1366,height:768},{width:1280,height:800},{width:1024,height:768}])test(`desktop layout and both sidebar states ${size.width}x${size.height}`,async({page})=>{
 await page.setViewportSize(size);await open(page);
 for(const expanded of [false,true]){
  if(expanded)await page.getByRole('button',{name:'Expand sidebar'}).click();
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth)).toBe(size.width);
  const suggestions=page.locator('.ai-suggestion');await expect(suggestions).toHaveCount(4);
  await composer(page).scrollIntoViewIfNeeded();const box=(await composer(page).boundingBox())!;expect(box.x+box.width).toBeLessThanOrEqual(size.width);
  await expect(page.getByRole('button',{name:'Send ↑',exact:true})).toBeVisible();
  await capture(page,`${size.width}-${expanded?'expanded':'minimized'}`);
  await page.getByRole('button',{name:'History',exact:true}).click();await expect(page.locator('.ai-history')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(size.width);
  await capture(page,`${size.width}-${expanded?'expanded':'minimized'}-history`);await page.getByRole('button',{name:'Collapse history'}).click();
 }
});

test('reduced motion, keyboard focus and original vector assets',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});await open(page);const suggestion=page.locator('.ai-suggestion').first();await suggestion.focus();await expect(suggestion).toBeFocused();await page.keyboard.press('Enter');await expect(composer(page)).toBeFocused();
 expect(await suggestion.evaluate(el=>getComputedStyle(el).transitionDuration)).toBe('0s');
 for(const icon of ['sparkle','suggestion']){const r=await page.request.get(`/assets/assistant/${icon}.svg`);expect(r.ok()).toBe(true);expect(await r.text()).toContain('<svg');}
});

test('reference-sized Figma comparison and usable long text',async({page})=>{
 await page.setViewportSize({width:1440,height:1080});await open(page);await capture(page,'reference-1440x1080');
 await composer(page).fill('A long question '.repeat(240));await expect(composer(page)).toHaveValue('A long question '.repeat(240));
 await composer(page).press('Enter');await expect(page.locator('.ai-error')).toBeVisible();await expect(page.locator('.ai-message-user')).toContainText('A long question');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(1440);
 const message=page.locator('.ai-message-user');expect(await message.evaluate(el=>el.scrollWidth<=el.clientWidth+1)).toBe(true);await capture(page,'long-user-question');
});
