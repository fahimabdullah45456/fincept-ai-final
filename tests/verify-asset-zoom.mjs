/** Local verification: genuine Chromium tab zoom via the test-only extension, not CSS zoom/DPR emulation.
 * Start frontend/backend first. Run: PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=$(which chromium) node tests/verify-asset-zoom.mjs
 */
import {chromium} from 'playwright';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const base=process.env.AUTH_PREVIEW_URL||'http://127.0.0.1:5173';
const extension=path.resolve('tests/support/browser-zoom');
const out=path.resolve('docs/asset-correction-zooms');await mkdir(out,{recursive:true});
const context=await chromium.launchPersistentContext('',{
  ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{}),
  headless:true,viewport:{width:1440,height:980},deviceScaleFactor:1,
  args:['--no-sandbox',`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]
});
const results=[];
try{
  const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker');
  const page=context.pages()[0]||await context.newPage();
  const pngRequests=[];page.on('request',r=>{if(/\.png(?:\?|$)/i.test(r.url()))pngRequests.push(r.url());});
  await page.goto(base+'/sign-in');
  for(const zoom of [1,1.25,1.5]){
    for(const route of ['sign-in','sign-up']){
      await page.goto(base+'/'+route);
    const actual=await worker.evaluate(async({base,zoom})=>{
      const tab=(await chrome.tabs.query({})).find(t=>t.url?.startsWith(base));
      await chrome.tabs.setZoomSettings(tab.id,{mode:'automatic',scope:'per-tab'});
      await chrome.tabs.setZoom(tab.id,zoom);
      return chrome.tabs.getZoom(tab.id);
    },{base,zoom});assert.equal(actual,zoom);
      await page.waitForTimeout(150);await page.evaluate(()=>document.fonts.ready);
      await page.locator('.financial-illustration').waitFor();
      await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0));
      const state=await page.evaluate(()=>({
        innerWidth:innerWidth,innerHeight:innerHeight,dpr:devicePixelRatio,
        documentWidth:document.documentElement.scrollWidth,documentHeight:document.documentElement.scrollHeight,
        cssZoom:getComputedStyle(document.documentElement).zoom,
        wordmark:document.querySelector('.brand-wordmark')?.textContent,
        images:Array.from(document.images).map(i=>({src:new URL(i.src).pathname,loaded:i.naturalWidth>0})),
        liveText:document.querySelector('.illustration-savings-value')?.textContent,
        ringCircles:document.querySelectorAll('.illustration-progress-ring circle').length,
        categoryCards:document.querySelectorAll('.illustration-category').length,
        fontLoaded:Array.from(document.fonts).some(face=>face.family==='FINCEPT Taka'&&face.status==='loaded')
      }));
      assert.equal(state.wordmark,'FINCEPT');assert.equal(state.liveText,'৳8,450');assert.equal(state.ringCircles,2);assert.equal(state.categoryCards,3);assert.equal(state.fontLoaded,true);
      assert.equal(state.cssZoom,'1');assert.ok(state.images.every(i=>i.src.endsWith('.svg')&&i.loaded));
      assert.ok(Math.abs(state.dpr-zoom)<.001,JSON.stringify({zoom,...state}));
      const filename=`${route}-${Math.round(zoom*100)}.png`;
      // CDP clip uses physical device-independent page coordinates at native zoom.
      // Playwright fullPage alone clips zoomed content; include the zoom factor explicitly.
      const cdp=await context.newCDPSession(page);
      const capture=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,fromSurface:true,clip:{x:0,y:0,width:Math.ceil(state.documentWidth*zoom),height:Math.ceil(state.documentHeight*zoom),scale:1}});
      await writeFile(path.join(out,filename),Buffer.from(capture.data,'base64'));await cdp.detach();
      // Scroll to actual form and use its original SVG visibility control at each real zoom.
      const password=page.getByLabel('Password',{exact:true});await password.fill('Fincept!2026');
      await page.getByRole('button',{name:'Show password',exact:true}).click();assert.equal(await password.getAttribute('type'),'text');
      await page.getByRole('button',{name:'Hide password',exact:true}).click();assert.equal(await password.getAttribute('type'),'password');
      results.push({route,browserZoom:actual,...state,screenshot:filename,passwordTogglePassed:true});
      console.log(`${route}: native browser zoom ${actual*100}%, CSS viewport ${state.innerWidth}x${state.innerHeight}, all vectors/live text verified`);
    }
  }
  assert.deepEqual(pngRequests,[]);
  await writeFile(path.join(out,'verification.json'),JSON.stringify({method:'chrome.tabs.setZoom + chrome.tabs.getZoom; CSS zoom unchanged; deviceScaleFactor 1; 1440x980 physical viewport',pngRequests,results},null,2));
}finally{await context.close();}
