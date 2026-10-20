import {test, expect, type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
const emptyOverview=JSON.parse(readFileSync(new URL('./fixtures/overview-empty.json',import.meta.url),'utf8'));
import {navigationItems, SIDEBAR_PREFERENCE_KEY} from '../src/components/layout/navigation';
async function session(page: Page) {
  await page.route('**/api/overview/summary?*', route=>route.fulfill({json:emptyOverview}));
  await page.route('**/api/overview/insights?*', route=>route.fulfill({json:{insight:null,method:'deterministic_rules',dataset:'live'}}));
  await page.route('**/api/overview/recent-transactions?*', route=>route.fulfill({json:{items:[],total:0,page:1,limit:6}}));
  await page.route('**/api/transactions?*',route=>route.fulfill({json:{items:[],total:0,page:1,pages:1,limit:10,counts:{},summary:{income_minor:0,expenses_minor:0,net_minor:0,count:0,previous_income_minor:0,previous_expenses_minor:0,income_change:null,expense_change:null,net_change_minor:0},period:{start:'2026-01-01',end:'2026-01-31'}}}));
  await page.route('**/api/transactions/options?*',route=>route.fulfill({json:{wallets:[],categories:[]}}));
  await page.route('**/api/wallets?*',route=>route.fulfill({json:{items:[],summary:Object.fromEntries(['total','bank','mobile','cash','savings'].map(k=>[k,{balance_minor:0,count:0}]))}}));
  await page.route('**/api/budgets?*',route=>route.fulfill({json:{items:[],total:0,filtered_count:0,summary:{limit_minor:0,spent_minor:0,remaining_minor:0,percentage:null,risk_count:0},alerts:[],categories:[],ambiguous_count:0,period:{start:'2026-01-01',end:'2026-01-31'}}}));
  await page.route('**/api/goals?*',route=>route.fulfill({json:{items:[],total:0,filtered_count:0,summary:{target_minor:0,saved_minor:0,remaining_minor:0,percentage:null,active_count:0},categories:[],today:'2026-10-19',scope:'all'}}));
  // This fixture has no real cookie: avoid an unrelated live 401 refreshing/unmounting its shell.
  await page.route('**/api/insights?*', route=>route.fulfill({status:503,json:{detail:'Analytics is outside this UI-only sidebar fixture.'}}));
  await page.route('**/api/assistant/**', route=>route.fulfill({status:503,json:{message:'Assistant is outside this UI-only shell fixture.'}}));
  // UI-only tests use an explicit session fixture; real authentication is covered in auth.spec.ts.
  await page.route('**/api/auth/me', route => route.fulfill({json: {user: {id: 'sidebar-test', full_name: 'Sidebar Test', email: 'sidebar@example.com'}}}));
}
async function assertGeometry(page: Page, width: number) {
  await expect.poll(async () => Math.round((await page.locator('.app-sidebar').boundingBox())!.width)).toBe(width);
  const aside = (await page.locator('.app-sidebar').boundingBox())!;
  const main = (await page.locator('.application-workspace').boundingBox())!;
  expect(main.x).toBeCloseTo(aside.x + aside.width, 0);
  expect(main.x + main.width).toBeLessThanOrEqual(page.viewportSize()!.width + 1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(page.viewportSize()!.width);
  for (const item of navigationItems) {
    const link = page.getByRole('link', {name: item.label, exact: true});
    await expect(link).toBeVisible();
    const box = (await link.boundingBox())!;
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.y + box.height).toBeLessThanOrEqual(page.viewportSize()!.height);
  }
  const settings = (await page.getByRole('link', {name: 'Settings', exact: true}).boundingBox())!;
  expect(page.viewportSize()!.height - settings.y - settings.height).toBeCloseTo(20, 0);
}
for (const viewport of [{width:1440,height:900},{width:1366,height:768},{width:1280,height:800},{width:1024,height:768}]) {
  test(`both sidebar states at ${viewport.width}x${viewport.height}`, async ({page}) => {
    await page.setViewportSize(viewport); await session(page); await page.goto('/overview');
    await expect(page.locator('.application-page-title')).toBeVisible();
    await assertGeometry(page,76);
    await expect(page.getByRole('link', {name:'Overview', exact:true})).toHaveAttribute('aria-current','page');
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({path:`docs/sidebar-qa/${viewport.width}-minimized.png`,fullPage:true});
    await page.getByRole('button',{name:'Expand sidebar'}).click();
    await assertGeometry(page,252);
    await expect(page.locator('.sidebar-wordmark')).toBeVisible();
    await page.screenshot({path:`docs/sidebar-qa/${viewport.width}-expanded.png`,fullPage:true});
    await page.reload(); await assertGeometry(page,252);
    await page.getByRole('button',{name:'Minimize sidebar'}).click(); await assertGeometry(page,76);
    await page.reload(); await assertGeometry(page,76);
  });
}
test('every route navigates without remounting sidebar in either state',async({page})=>{
  await session(page); await page.goto('/overview');
  await page.locator('.app-sidebar').evaluate(el=>el.setAttribute('data-instance-test','same'));
  for (const expanded of [false,true]) {
    if(expanded) await page.getByRole('button',{name:'Expand sidebar'}).click();
    for(const item of navigationItems) {
      await page.getByRole('link',{name:item.label,exact:true}).click();
      await expect(page).toHaveURL(new RegExp(item.path+'$'));
      await expect(page.getByRole('link',{name:item.label,exact:true})).toHaveAttribute('aria-current','page');
      await expect(page.locator('.sidebar-link[aria-current=page]')).toHaveCount(1);
      await expect(page.locator('.app-sidebar')).toHaveAttribute('data-instance-test','same');
      await expect(page.getByRole('button',{name:expanded?'Minimize sidebar':'Expand sidebar'})).toBeVisible();
    }
  }
  await page.goto('/transactions/example');
  await expect(page.getByRole('link',{name:'Transactions',exact:true})).toHaveAttribute('aria-current','page');
});
test('keyboard, tooltips, reduced motion and original assets',async({page})=>{
  await session(page);await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/overview');
  const toggle=page.getByRole('button',{name:'Expand sidebar'});
  await toggle.focus();await expect(page.getByRole('tooltip')).toHaveText('Expand sidebar');
  await page.keyboard.press('Escape');await expect(page.getByRole('tooltip')).toHaveCount(0);
  await page.keyboard.press('Enter');await assertGeometry(page,252);
  await expect(page.getByRole('button',{name:'Minimize sidebar'})).toBeFocused();
  expect(await page.locator('.application-shell').evaluate(el=>getComputedStyle(el).transitionDuration)).toBe('0s');
  await page.keyboard.press('Space');await assertGeometry(page,76);
  const wallets=page.getByRole('link',{name:'Wallets',exact:true});await wallets.focus();
  await expect(page.getByRole('tooltip')).toHaveText('Wallets');await page.keyboard.press('Enter');await expect(page).toHaveURL(/wallets$/);
  await expect(page.locator('.sidebar-brand img')).toHaveAttribute('src','/assets/sidebar/logo-mark.svg');
  expect(await page.locator('.sidebar-brand img').evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBe(38);
  for(const item of navigationItems) {
    const icon=page.getByRole('link',{name:item.label,exact:true}).locator('.sidebar-icon');
    expect(await icon.evaluate(el=>getComputedStyle(el).maskImage)).toContain(`/assets/sidebar/${item.icon}.svg`);
    const res=await page.request.get(`/assets/sidebar/${item.icon}.svg`);expect(res.ok()).toBe(true);expect(await res.text()).toContain('<svg');
  }
});
test('invalid and inaccessible storage fall back safely',async({page})=>{
  await session(page);await page.addInitScript(key=>localStorage.setItem(key,'invalid'),SIDEBAR_PREFERENCE_KEY);
  await page.goto('/overview');await assertGeometry(page,76);
  await page.evaluate(()=>{Object.defineProperty(Storage.prototype,'setItem',{value:()=>{throw new Error('Blocked');}});});
  await page.getByRole('button',{name:'Expand sidebar'}).click();await assertGeometry(page,252);
});
test('all application routes remain protected without a session',async({page})=>{
  for(const item of navigationItems){await page.goto(item.path);await expect(page).toHaveURL(/sign-in$/);await expect(page.locator('.app-sidebar')).toHaveCount(0);}
});
