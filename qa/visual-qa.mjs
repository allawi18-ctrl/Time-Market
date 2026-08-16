import { chromium } from 'playwright';
import fs from 'node:fs';
fs.mkdirSync('qa-output',{recursive:true});
const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-webgl','--ignore-gpu-blocklist']});
const context=await browser.newContext({viewport:{width:430,height:932},deviceScaleFactor:1,recordVideo:{dir:'qa-output',size:{width:430,height:932}}});
const page=await context.newPage();const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push('console: '+m.text())});page.on('pageerror',e=>errors.push('pageerror: '+e.message));
try{
 await page.goto('http://127.0.0.1:8000/qa/human08-test.html',{waitUntil:'domcontentloaded',timeout:240000});
 await page.waitForFunction(()=>window.__TM_READY__===true,null,{timeout:240000});
 await page.waitForTimeout(2500);
 await page.screenshot({path:'qa-output/human08-front.png',fullPage:false,timeout:30000});
 await page.waitForTimeout(3500);
 await page.screenshot({path:'qa-output/human08-orbit.png',fullPage:false,timeout:30000});
}catch(e){errors.push('qa: '+e.stack);throw e}finally{fs.writeFileSync('qa-output/runtime-errors.txt',errors.length?errors.join('\n'):'NO_RUNTIME_ERRORS');await context.close();await browser.close()}
