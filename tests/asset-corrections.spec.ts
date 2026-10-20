import {test,expect} from '@playwright/test';
test('both actual auth pages use original SVGs, live wordmark/cards, and no PNGs',async({page})=>{
  for(const route of ['sign-in','sign-up']){
    const requested:string[]=[];
    const record=(request:{url:()=>string})=>requested.push(request.url());page.on('request',record);
    await page.goto('/'+route);await page.evaluate(()=>document.fonts.ready);
    await expect(page.locator('.brand-logo>img')).toHaveAttribute('src','/assets/auth/logo-mark.svg');
    await expect(page.locator('.brand-wordmark')).toHaveText('FINCEPT');
    await expect(page.locator('.illustration-savings-value')).toHaveText('৳8,450');
    await expect(page.locator('.illustration-category')).toHaveCount(3);
    await expect(page.locator('.illustration-progress-ring svg circle')).toHaveCount(2);
    for(const name of ['savings-chart','housing-icon','wallet-icon','groceries-icon'])await expect(page.locator(`.financial-illustration img[src="/assets/auth/${name}.svg"]`)).toBeVisible();
    await expect(page.locator('.password-toggle>img').first()).toHaveAttribute('src','/assets/auth/password-eye.svg');
    await expect(page.locator('.social-button>img')).toHaveAttribute('src','/assets/google.svg');
    await expect(page.locator('img[src$=".png"]')).toHaveCount(0);
    expect(requested.some(url=>/\.png(?:\?|$)/i.test(url))).toBe(false);
    expect(await page.locator('img').evaluateAll(images=>images.every(i=>(i as HTMLImageElement).complete&&(i as HTMLImageElement).naturalWidth>0))).toBe(true);
    await page.getByLabel('Password',{exact:true}).fill('Fincept!2026');
    await page.getByRole('button',{name:'Show password',exact:true}).click();
    await expect(page.getByLabel('Password',{exact:true})).toHaveAttribute('type','text');
    await expect(page.getByRole('button',{name:'Hide password',exact:true}).locator('img')).toHaveAttribute('src','/assets/auth/password-eye.svg');
    await page.getByRole('button',{name:'Hide password',exact:true}).click();
    await expect(page.getByLabel('Password',{exact:true})).toHaveAttribute('type','password');
    page.off('request',record);
  }
});
