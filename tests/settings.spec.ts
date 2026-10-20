import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const headers={'X-Fincept-Request':'1',Origin:'http://127.0.0.1:5180'},password='Fincept!2026';
const categories=['Profile','Privacy & Security','Notifications','Financial Preferences','Connected Services','Data & Account','Help & About'];
test.beforeAll(()=>{const db=path.resolve('test-results/auth-e2e.sqlite3');if(fs.existsSync(db))execFileSync(process.env.PYTHON_BIN||'python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('DELETE FROM rate_limits');c.commit()",db]);});
test.beforeEach(({page})=>{page.on('pageerror',error=>{throw error;});});
async function account(page:Page){const email=`settings-${Date.now()}-${Math.random()}@example.com`;const r=await page.request.post('/api/auth/register',{headers,data:{full_name:'Settings Tester',email,password,confirm_password:password,accepted_terms:true}});expect(r.status()).toBe(201);return email;}
async function category(page:Page,label:string){
 await expect(page.locator('.settings-page')).toBeVisible();
 const dropdown=page.getByLabel('Settings category',{exact:true});
 if((page.viewportSize()?.width||1440)<=650)await dropdown.selectOption({label});
 else await page.getByRole('navigation',{name:'Settings categories'}).getByRole('link',{name:label,exact:true}).click();
 const slug:Record<string,string>={'Profile':'profile','Privacy & Security':'privacy-security','Notifications':'notifications','Financial Preferences':'financial-preferences','Connected Services':'connected-services','Data & Account':'data-account','Help & About':'help-about'};
 await expect(page).toHaveURL(new RegExp('/settings/'+slug[label]+'(?:[?#].*)?$'));
 await expect(page.locator('.st-content')).toHaveAttribute('aria-label',label);
 await expect(page.locator('.st-content').getByRole('heading',{name:label==='Notifications'?'Financial activity':label,exact:true})).toBeVisible();
}
async function seedWallet(page:Page){const r=await page.request.post('/api/transactions/wallets',{headers,data:{request_key:crypto.randomUUID(),name:'Settings live wallet',kind:'bank',opening_minor:123450,opening_date:'2026-01-01'}});expect(r.status()).toBe(201);return r.json();}

test('profile validates, cancels, saves real user data, and updates shared header without reload',async({page})=>{
 const email=await account(page);await page.goto('/settings');await expect(page).toHaveURL(/\/settings\/profile$/);await expect(page.getByLabel('Display name')).toHaveValue('Settings Tester');await expect(page.getByLabel('Email address')).toHaveValue(email);
 await page.getByRole('link',{name:'Edit Profile'}).click();await expect(page.getByLabel('Display name')).toBeFocused();
 await page.getByLabel('Display name').fill('x');await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByText('Enter a display name between 2 and 100 characters.')).toBeVisible();
 await page.getByRole('button',{name:'Cancel',exact:true}).click();await expect(page.getByLabel('Display name')).toHaveValue('Settings Tester');
 await page.getByLabel('Display name').fill('Updated Actual User');await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByText('Your profile has been updated.')).toBeVisible();await expect(page.locator('.st-summary h2')).toHaveText('Updated Actual User');await expect(page.locator('.profile-name')).toHaveText('Updated');
 await page.reload();await expect(page.getByLabel('Display name')).toHaveValue('Updated Actual User');
});
test('category routes support back/forward and saved notification preferences',async({page})=>{
 await account(page);await page.goto('/settings/profile');await category(page,'Notifications');
 await page.getByRole('switch',{name:'Budget alerts',exact:true}).click();await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByText('Notification preferences saved. Delivery is not configured.')).toBeVisible();
 await category(page,'Help & About');await page.goBack();await expect(page.getByRole('switch',{name:'Budget alerts',exact:true})).toHaveAttribute('aria-checked','true');await page.goForward();await expect(page.getByRole('heading',{name:'Help & About',exact:true})).toBeVisible();
 await page.goto('/settings/notifications');await page.getByRole('switch',{name:'Goal updates',exact:true}).click();await page.getByRole('button',{name:'Cancel',exact:true}).click();await expect(page.getByRole('switch',{name:'Goal updates',exact:true})).toHaveAttribute('aria-checked','false');await page.reload();await expect(page.getByRole('switch',{name:'Budget alerts',exact:true})).toHaveAttribute('aria-checked','true');
});
test('formatting propagates across shared amounts and preserves underlying records',async({page})=>{
 await account(page);const wallet=await seedWallet(page);await page.goto('/settings/financial-preferences');await page.getByLabel('Decimal display').selectOption('fixed');await page.getByRole('switch',{name:'Thousands separators'}).click();await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByText('Financial display preferences saved. Your recorded amounts have not changed.')).toBeVisible();
 await page.goto('/wallets');await expect(page.locator('.money').first()).toHaveText('৳1234.50');await page.reload();await expect(page.locator('.money').first()).toHaveText('৳1234.50');
 const data=await (await page.request.get('/api/settings/export?format=json&scope=wallets')).json();expect(data.data.wallets.find((w:{id:string})=>w.id===wallet.id).opening_minor).toBe(123450);
});
test('Settings and header privacy share one persisted state across all application routes',async({page})=>{
 await account(page);await seedWallet(page);await page.goto('/settings/privacy-security');await page.getByRole('switch',{name:'Hide monetary amounts'}).click();await expect(page.getByRole('button',{name:'Show balances',exact:true})).toHaveAttribute('aria-pressed','true');
 for(const route of ['/overview','/transactions','/wallets','/budgets','/financial-goals','/insights','/debt-loans','/financial-hub','/planner','/ai-assistant','/settings/financial-preferences']){
  await page.goto(route);await expect(page.getByRole('button',{name:'Show balances',exact:true})).toBeVisible();expect(await page.evaluate(()=>localStorage.getItem('fincept.money.hidden'))).toBe('true');
  for(const amount of await page.locator('.money').all())await expect(amount).toContainText('••••');
 }
 await page.getByRole('button',{name:'Show balances',exact:true}).click();await category(page,'Privacy & Security');await expect(page.getByRole('switch',{name:'Hide monetary amounts'})).toHaveAttribute('aria-checked','false');
});
test('password flow reauthenticates, blocks dismissal while pending, and genuinely revokes other sessions',async({page,browser})=>{
 const email=await account(page);const other=await browser.newContext();try{
  expect((await other.request.post('http://127.0.0.1:5180/api/auth/login',{headers,data:{email,password}})).status()).toBe(200);
  await page.goto('/settings/privacy-security');await page.getByRole('button',{name:'Change Password'}).click();const dialog=page.getByRole('dialog',{name:'Change Password'});
  await dialog.getByLabel('Current password',{exact:true}).fill('wrong');await dialog.getByLabel('New password',{exact:true}).fill('Updated!2026');await dialog.getByLabel('Confirm new password',{exact:true}).fill('Updated!2026');await dialog.getByRole('button',{name:'Update Password'}).click();await expect(dialog.getByRole('alert')).toContainText('current password is incorrect');
  await dialog.getByLabel('Current password',{exact:true}).fill(password);await page.route('**/api/settings/password',async route=>{await new Promise(resolve=>setTimeout(resolve,400));await route.continue();});
  await dialog.getByRole('button',{name:'Update Password'}).click();await page.keyboard.press('Escape');await expect(dialog).toBeVisible();await expect(dialog.getByRole('button',{name:'Cancel',exact:true})).toBeDisabled();await expect(dialog).not.toBeVisible();await expect(page.getByText('Password updated. Other sessions were signed out. This session was renewed.')).toBeVisible();expect((await other.request.get('http://127.0.0.1:5180/api/auth/me')).status()).toBe(401);
 }finally{await other.close();}
});
test('native dialog Escape, focus restoration, keyboard switches, and accessible FAQ',async({page})=>{
 await account(page);await page.goto('/settings/privacy-security');const trigger=page.getByRole('button',{name:'Change Password'});await trigger.click();await expect(page.getByLabel('Current password',{exact:true})).toBeFocused();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();await expect(trigger).toBeFocused();
 const toggle=page.getByRole('switch',{name:'Hide monetary amounts'});await toggle.focus();await page.keyboard.press('Space');await expect(toggle).toHaveAttribute('aria-checked','true');
 await category(page,'Help & About');const faq=page.getByText('Does changing display formatting change my money?',{exact:true});await faq.focus();await page.keyboard.press('Enter');await expect(page.getByText(/No\. Thousands separators and decimal display only change presentation/)).toBeVisible();await page.getByRole('button',{name:'About FINCEPT AI'}).click();await expect(page.getByRole('dialog')).toContainText('0.1.0');
});
test('real JSON/CSV downloads, empty scopes, and confirmed demo clearing preserve live data',async({page})=>{
 await account(page);const wallet=await seedWallet(page);expect((await page.request.post('/api/overview/demo',{headers})).status()).toBe(201);await page.goto('/settings/data-account');
 await page.getByLabel('File format').selectOption('json');await page.getByRole('button',{name:'Export Your Data',exact:true}).click();let dialog=page.getByRole('dialog');await expect(dialog).toContainText('unmasked monetary values');
 const downloadPromise=page.waitForEvent('download');await dialog.getByRole('button',{name:'Download Export'}).click();const download=await downloadPromise;const file=await download.path();expect(file).not.toBeNull();const snapshot=JSON.parse(fs.readFileSync(file!,'utf8'));expect(snapshot.data.wallets).toHaveLength(1);expect(snapshot.data.wallets[0].id).toBe(wallet.id);expect(snapshot.manifest.dataset).toBe('live');
 await page.getByLabel('File format').selectOption('csv');await page.getByLabel('Export scope').selectOption('transactions');await page.getByRole('button',{name:'Export Your Data',exact:true}).click();const csvPromise=page.waitForEvent('download');await page.getByRole('dialog').getByRole('button',{name:'Download Export'}).click();const csv=await csvPromise;expect(csv.suggestedFilename()).toMatch(/\.zip$/);expect(fs.readFileSync((await csv.path())!).subarray(0,2).toString()).toBe('PK');
 await page.getByRole('button',{name:'Clear Demo Data',exact:true}).click();dialog=page.getByRole('dialog');await expect(dialog.getByRole('button',{name:'Permanently Clear Demo Data'})).toBeDisabled();await dialog.getByLabel('Type CLEAR DEMO DATA to confirm').fill('CLEAR DEMO DATA');await dialog.getByRole('button',{name:'Permanently Clear Demo Data'}).click();await expect(page.getByText('Sample workspace cleared. Live records and other accounts were not changed.')).toBeVisible();
 const data=await(await page.request.get('/api/settings/export?format=json&dataset=demo')).json();expect(data.data.wallets).toHaveLength(0);const live=await(await page.request.get('/api/settings/export?format=json')).json();expect(live.data.wallets[0].id).toBe(wallet.id);
 await expect(page.getByRole('button',{name:'Restore unavailable'})).toBeDisabled();await expect(page.getByRole('button',{name:'Delete unavailable'})).toBeDisabled();
});
test('failed preferences retain draft and never display success, then retry correctly',async({page})=>{
 await account(page);await page.goto('/settings/notifications');await page.getByRole('switch',{name:'Budget alerts',exact:true}).click();let fail=true;await page.route('**/api/settings/preferences',async route=>{if(fail)await route.fulfill({status:503,json:{message:'Unable to save these preferences.'}});else await route.continue();});await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByRole('alert')).toContainText('Unable to save');expect((await(await page.request.get('/api/settings')).json()).preferences.notifications.budget_alerts).toBe(false);await expect(page.getByRole('switch',{name:'Budget alerts',exact:true})).toHaveAttribute('aria-checked','true');fail=false;await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByText('Notification preferences saved. Delivery is not configured.')).toBeVisible();
});
test('initial load errors retry and integrations never claim a connection',async({page})=>{
 await account(page);let fail=true;await page.route('**/api/settings',async route=>{if(fail)await route.fulfill({status:503,json:{message:'Settings temporarily unavailable.'}});else await route.continue();});await page.goto('/settings/connected-services');await expect(page.getByRole('alert')).toContainText('Settings temporarily unavailable.');fail=false;await page.getByRole('button',{name:'Try again'}).click();await expect(page.getByText('No third-party account connections are active. Your manually maintained wallets and records are unchanged.')).toBeVisible();for(const button of await page.getByRole('button',{name:'Connect unavailable'}).all())await expect(button).toBeDisabled();
});
for(const [width,height] of [[1440,900],[1366,768],[1280,800],[1024,768],[390,844]])test(`all categories and dialogs fit ${width}x${height}`,async({page})=>{
 await page.setViewportSize({width,height});await account(page);await page.goto('/settings/profile');
 for(const name of categories){await category(page,name);await expect(page.locator('.st-content')).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`docs/settings-qa/${width}x${height}-${name.replace(/[^a-z]/gi,'-').toLowerCase()}.png`,fullPage:true,animations:'disabled'});}
 await category(page,'Privacy & Security');await page.getByRole('button',{name:'Change Password'}).click();const bounds=await page.getByRole('dialog').boundingBox();expect(bounds!.x).toBeGreaterThanOrEqual(0);expect(bounds!.x+bounds!.width).toBeLessThanOrEqual(width);expect(bounds!.height).toBeLessThanOrEqual(height);await page.screenshot({path:`docs/settings-qa/${width}x${height}-security-dialog.png`,fullPage:true,animations:'disabled'});await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();
 await page.getByRole('button',{name:'Expand sidebar'}).click();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await expect(page.getByRole('button',{name:'Minimize sidebar'})).toHaveAttribute('aria-expanded','true');await expect.poll(async()=>Math.round((await page.getByRole('complementary',{name:'Application sidebar'}).boundingBox())!.width)).toBe(252);await page.getByRole('button',{name:'Minimize sidebar'}).click();
});
test('profile errors retain inputs and never claim a successful update',async({page})=>{
 await account(page);await page.goto('/settings/profile');await page.getByLabel('Display name').fill('Unsaved Actual Name');await page.route('**/api/settings/profile',route=>route.fulfill({status:503,json:{message:'Profile could not be saved.'}}));await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByRole('alert')).toContainText('Profile could not be saved.');await expect(page.getByLabel('Display name')).toHaveValue('Unsaved Actual Name');await expect(page.locator('.st-summary h2')).toHaveText('Settings Tester');expect((await(await page.request.get('/api/auth/me')).json()).user.full_name).toBe('Settings Tester');
});
test('version conflicts reload explicitly and pending saves cannot double-submit',async({page})=>{
 await account(page);await page.goto('/settings/notifications');await page.getByRole('switch',{name:'Budget alerts',exact:true}).click();const saved=await(await page.request.get('/api/settings')).json();expect((await page.request.patch('/api/settings/preferences',{headers,data:{...saved.preferences,version:saved.version,financial:{number_grouping:false,decimal_style:'fixed'}}})).status()).toBe(200);await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByRole('alert')).toContainText('another window');await page.getByRole('button',{name:'Reload saved settings (discard edits)'}).click();await expect(page.getByRole('switch',{name:'Budget alerts',exact:true})).toHaveAttribute('aria-checked','false');await page.getByRole('switch',{name:'Budget alerts',exact:true}).click();let requests=0;await page.route('**/api/settings/preferences',async route=>{requests++;await new Promise(resolve=>setTimeout(resolve,350));await route.continue();});await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByRole('button',{name:'Saving…',exact:true})).toBeDisabled();await expect(page.getByText('Notification preferences saved. Delivery is not configured.')).toBeVisible();expect(requests).toBe(1);
});
test('expired Settings authorization provides a sign-in action instead of saved controls',async({page})=>{
 await account(page);await page.route('**/api/settings',route=>route.fulfill({status:401,json:{message:'Session expired.'}}));await page.goto('/settings/notifications');await expect(page.getByRole('alert')).toContainText('session has expired');await expect(page.getByRole('link',{name:'Sign in again'})).toHaveAttribute('href','/sign-in');await expect(page.getByRole('button',{name:'Save Changes',exact:true})).toHaveCount(0);
});
