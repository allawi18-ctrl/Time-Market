import { chromium } from 'playwright';
import fs from 'node:fs';

fs.mkdirSync('qa-output',{recursive:true});
const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-webgl','--ignore-gpu-blocklist']});
const context=await browser.newContext({viewport:{width:430,height:932},deviceScaleFactor:1,recordVideo:{dir:'qa-output',size:{width:430,height:932}}});
const page=await context.newPage();
const errors=[];
page.on('console',m=>{if(m.type()==='error')errors.push('console: '+m.text())});
page.on('pageerror',e=>errors.push('pageerror: '+e.message));
try{
 await page.goto('http://127.0.0.1:8000/qa/build07.html',{waitUntil:'domcontentloaded',timeout:180000});
 await page.waitForFunction(()=>window.__TM_READY__===true,null,{timeout:180000});
 await page.waitForTimeout(5000);
 await page.screenshot({path:'qa-output/build07-ingame-01.png',fullPage:false});
 await page.keyboard.down('w');await page.waitForTimeout(1900);await page.keyboard.up('w');
 await page.waitForTimeout(300);
 await page.keyboard.down('Shift');await page.keyboard.down('w');await page.waitForTimeout(1300);await page.keyboard.up('w');await page.keyboard.up('Shift');
 await page.keyboard.down('a');await page.waitForTimeout(650);await page.keyboard.up('a');await page.waitForTimeout(850);
 await page.screenshot({path:'qa-output/build07-ingame-02-after-movement.png',fullPage:false});
}catch(e){errors.push('qa: '+e.stack);await page.screenshot({path:'qa-output/failure-state.png',fullPage:false}).catch(()=>{});throw e}finally{fs.writeFileSync('qa-output/runtime-errors.txt',errors.length?errors.join('\n'):'NO_RUNTIME_ERRORS');await context.close();await browser.close()}
