import { chromium } from 'playwright';
import fs from 'node:fs';

fs.mkdirSync('qa-output', { recursive: true });
const browser = await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-webgl','--ignore-gpu-blocklist']});
const context = await browser.newContext({
  viewport:{width:430,height:932},
  deviceScaleFactor:1,
  recordVideo:{dir:'qa-output',size:{width:430,height:932}}
});
const page = await context.newPage();
const errors=[];
page.on('console',m=>{ if(m.type()==='error') errors.push('console: '+m.text()); });
page.on('pageerror',e=>errors.push('pageerror: '+e.message));
await page.goto('http://127.0.0.1:8000/qa/build06.html',{waitUntil:'domcontentloaded',timeout:120000});
await page.waitForFunction(()=>window.__TM_READY__===true,null,{timeout:150000});
await page.waitForTimeout(3500);
await page.screenshot({path:'qa-output/build06-ingame-01.png',fullPage:false});

await page.keyboard.down('w');
await page.waitForTimeout(1800);
await page.keyboard.up('w');
await page.waitForTimeout(350);
await page.keyboard.down('Shift');
await page.keyboard.down('w');
await page.waitForTimeout(1400);
await page.keyboard.up('w');
await page.keyboard.up('Shift');
await page.keyboard.down('d');
await page.waitForTimeout(700);
await page.keyboard.up('d');
await page.waitForTimeout(700);
await page.screenshot({path:'qa-output/build06-ingame-02-after-movement.png',fullPage:false});

fs.writeFileSync('qa-output/runtime-errors.txt', errors.length?errors.join('\n'):'NO_RUNTIME_ERRORS');
await context.close();
await browser.close();
