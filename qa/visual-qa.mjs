import { chromium } from 'playwright';
import fs from 'node:fs';
fs.mkdirSync('qa-output',{recursive:true});
const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-webgl','--ignore-gpu-blocklist']});
const context=await browser.newContext({viewport:{width:430,height:932},deviceScaleFactor:1,recordVideo:{dir:'qa-output',size:{width:430,height:932}}});
const page=await context.newPage();const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push('console: '+m.text())});page.on('pageerror',e=>errors.push('pageerror: '+e.message));
async function frame(name){const data=await page.evaluate(()=>document.querySelector('canvas')?.toDataURL('image/png'));if(!data)throw new Error('No canvas frame');fs.writeFileSync(`qa-output/${name}`,Buffer.from(data.split(',')[1],'base64'))}
try{
 await page.goto('http://127.0.0.1:8000/qa/build12.html',{waitUntil:'domcontentloaded',timeout:180000});
 await page.waitForFunction(()=>window.__TM_READY__===true,null,{timeout:180000});
 await page.waitForTimeout(3200);await frame('build12-start.png');
 await page.keyboard.down('w');await page.waitForTimeout(1900);await page.keyboard.up('w');await page.waitForTimeout(600);await frame('build12-walk.png');
 await page.keyboard.down('Shift');await page.keyboard.down('w');await page.waitForTimeout(1200);await page.keyboard.up('w');await page.keyboard.up('Shift');await page.keyboard.down('d');await page.waitForTimeout(500);await page.keyboard.up('d');await page.waitForTimeout(1000);await frame('build12-after-movement.png');
}catch(e){errors.push('qa: '+e.stack);throw e}finally{fs.writeFileSync('qa-output/runtime-errors.txt',errors.length?errors.join('\n'):'NO_RUNTIME_ERRORS');await context.close();await browser.close()}
