// Exercise the standalone report through Chrome's DevTools pipe.
import {spawn} from 'node:child_process';
import {writeFileSync} from 'node:fs';
const browser=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
 '--headless','--disable-gpu','--no-first-run','--user-data-dir=/private/tmp/acts-score-html-check','--remote-debugging-pipe'],{stdio:['ignore','ignore','ignore','pipe','pipe']});
let id=0,buffer='',pending=new Map();
browser.stdio[4].on('data',chunk=>{buffer+=chunk;let n;while((n=buffer.indexOf('\0'))>=0){const message=JSON.parse(buffer.slice(0,n));buffer=buffer.slice(n+1);if(message.id){const p=pending.get(message.id);pending.delete(message.id);message.error?p.reject(message.error):p.resolve(message.result);}}});
function call(method,params={},sessionId){return new Promise((resolve,reject)=>{const request={id:++id,method,params,sessionId};pending.set(id,{resolve,reject});browser.stdio[3].write(JSON.stringify(request)+'\0');});}
const timeout=setTimeout(()=>{browser.kill();process.exit(2);},20000);
try {
 const {targetId}=await call('Target.createTarget',{url:'about:blank'});
 const {sessionId}=await call('Target.attachToTarget',{targetId,flatten:true});
 await call('Page.enable',{},sessionId);
 await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1400,deviceScaleFactor:1,mobile:false},sessionId);
 await call('Page.navigate',{url:'file://'+process.argv[2]},sessionId);
 const result=await call('Runtime.evaluate',{expression:`new Promise(resolve=>{function check(){if(!document.querySelector('svg circle'))return setTimeout(check,20);const plots=[...document.querySelectorAll('.figure')];const first=plots[0], before=first.querySelectorAll('circle').length;const input=first.querySelector('input');input.checked=false;input.dispatchEvent(new Event('change'));const after=first.querySelectorAll('circle').length;input.checked=true;input.dispatchEvent(new Event('change'));resolve({figures:plots.length,svg:document.querySelectorAll('svg').length,bitmap:document.querySelectorAll('img').length,legendWorks:after<before&&first.querySelectorAll('circle').length===before,accessiblePoints:[...document.querySelectorAll('circle')].every(c=>c.hasAttribute('aria-label')&&c.hasAttribute('tabindex')),embeddedData:JSON.parse(document.getElementById('plot-data').textContent).length});}check();})`,awaitPromise:true,returnByValue:true},sessionId);
 const out=result.result.value;console.log(JSON.stringify(out,null,2));
 if(process.argv[3]){const shot=await call('Page.captureScreenshot',{format:'png'},sessionId);writeFileSync(process.argv[3],Buffer.from(shot.data,'base64'));}
 if(result.exceptionDetails||!out.legendWorks||!out.accessiblePoints||out.bitmap!==0||out.svg!==out.embeddedData)process.exitCode=1;
} finally {clearTimeout(timeout);await call('Browser.close').catch(()=>{});}
