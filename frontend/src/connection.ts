export type Connection='checking'|'warming'|'ready'|'offline';
export async function waitUntilReady<T extends {ready:boolean}>(options:{probe:()=>Promise<T>;onState:(state:Connection)=>void;now?:()=>number;sleep?:(ms:number)=>Promise<void>;timeoutMs?:number;retryMs?:number}):Promise<T>{
 const now=options.now||Date.now;const sleep=options.sleep||((ms:number)=>new Promise(resolve=>setTimeout(resolve,ms)));const started=now();
 options.onState('checking');
 while(now()-started<(options.timeoutMs??75000)){
  try{const result=await options.probe();if(result.ready){options.onState('ready');return result;}}catch{/* Network timeout or a waking server; retry within the deadline. */}
  options.onState('warming');await sleep(options.retryMs??2000);
 }
 options.onState('offline');throw new Error('Backend readiness deadline exceeded');
}
