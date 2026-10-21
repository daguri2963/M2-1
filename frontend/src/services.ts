import type productData from './data/products.json';
import type {Survey} from './domain';
import {waitUntilReady,type Connection} from './connection';
export type {Connection} from './connection';
export type Product=typeof productData[number];
export type Citation={id:string;productId:string|null;title:string;text:string;url:string;productUrl:string|null;observedAt:string;kind?:'label_guide'};
export type ChatReply={text:string;mode:string;citations:Citation[];productIds:string[]};
export type Overlap={status:string;duplicates:{name:string;items:{productId:string;productName:string;amount:string;operator:string;unit:string;basis:string|null}[];dailyTotal:{amount:string;unit:string}|null;totalStatus:string}[];notice?:string};
export type Recommendation={status:'ok'|'empty'|'insufficient'|'restricted';message:string;nextStep?:number;policyVersion:string;products:Product[];reasons:Record<string,string[]>;evidence:Citation[];notices:string[];overlap:Overlap;ai:Partial<ChatReply>&{message?:string;code?:string}};
const local=window.location.hostname==='127.0.0.1'||window.location.hostname==='localhost';
const base=(import.meta.env.VITE_API_BASE_URL||(local?`http://${window.location.hostname}:8000`:'')).replace(/\/$/,'');
let token:string|undefined;
let consentVersion='2026-10-21.1';
let healthPromise:Promise<void>|undefined;
let connection:Connection='checking';
let healthCheckedAt=0;
const listeners=new Set<(state:Connection)=>void>();
function setConnection(state:Connection){connection=state;listeners.forEach(f=>f(state));}
export function subscribeConnection(listener:(state:Connection)=>void){listeners.add(listener);listener(connection);return()=>{listeners.delete(listener);};}
export class APIError extends Error{constructor(public code:string,message:string,public status=0){super(message);}}
export async function waitForServer(){
 if(connection==='ready'&&Date.now()-healthCheckedAt<30000)return;
 if(healthPromise)return healthPromise;
 healthPromise=(async()=>{
  try{const health=await waitUntilReady({onState:setConnection,probe:async()=>{
   const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),5000);
   try{const r=await fetch(base+'/api/health',{signal:controller.signal,cache:'no-store'});if(!r.ok)throw new Error('not ready');return await r.json() as {ready:boolean;consentVersion:string};}finally{clearTimeout(timeout);}
  }});consentVersion=health.consentVersion;healthCheckedAt=Date.now();}catch{throw new APIError('SERVER_UNAVAILABLE','서버 연결이 지연되고 있어요. 잠시 후 다시 시도해 주세요.');}
 })().finally(()=>{healthPromise=undefined;});
 return healthPromise;
}
async function request<T>(path:string,body?:unknown,options:{signal?:AbortSignal;personal?:boolean;method?:string;timeout?:number}={}):Promise<T>{
 await waitForServer();
 if(options.personal&&!token)throw new APIError('CONSENT_REQUIRED','이용 안내에 먼저 동의해 주세요.',401);
 const controller=new AbortController();const onAbort=()=>controller.abort();options.signal?.addEventListener('abort',onAbort,{once:true});
 if(options.signal?.aborted)controller.abort();
 const timer=setTimeout(()=>controller.abort(),options.timeout??65000);
 try{
  const r=await fetch(base+path,{method:options.method||(body===undefined?'GET':'POST'),headers:{...(body===undefined?{}:{'Content-Type':'application/json'}),...(options.personal?{'X-Session-Token':token!}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal,cache:'no-store'});
  const data=await r.json();
  if(!r.ok){if(r.status===401){token=undefined;window.dispatchEvent(new Event('session-expired'));}throw new APIError(data.error?.code||'REQUEST_ERROR',data.error?.message||'요청을 처리하지 못했어요.',r.status);}
  return data;
 }catch(error){
  if(error instanceof APIError)throw error;
  if(options.signal?.aborted)throw error;
  setConnection('offline');healthCheckedAt=0;
  throw new APIError('NETWORK_ERROR','연결이 끊겼거나 응답이 지연되고 있어요. 다시 시도해 주세요.');
 }finally{clearTimeout(timer);options.signal?.removeEventListener('abort',onAbort);}
}
export let products:Product[]=[];
const featuredIds=['600000128','600000129','600000147','610911092','600000313','601678603','610911097','032306200'];
export let featured:Product[]=[];
export const getProduct=(id:string)=>products.find(p=>p.id===id);
export async function loadProducts(signal?:AbortSignal){const data=await request<{products:Product[]}>('/api/products',undefined,{signal});products=data.products;featured=featuredIds.map(id=>getProduct(id)!).filter(Boolean);return products;}
export const api={
 async consent(){const data=await request<{token:string}>('/api/sessions',{adultConfirmed:true,privacyAccepted:true,aiAccepted:true,version:consentVersion});token=data.token;},
 async clearSession(){try{if(token)await request('/api/sessions/current',undefined,{personal:true,method:'DELETE'});}finally{token=undefined;}},
 detail(id:string,signal?:AbortSignal){return request<Product>('/api/products/'+encodeURIComponent(id),undefined,{signal});},
 compare(productIds:string[],signal?:AbortSignal){return request<{rows:{label:string;values:string[]}[];notice:string}>('/api/compare',{productIds},{signal});},
 recommend(survey:Survey,signal?:AbortSignal){return request<Recommendation>('/api/recommendations',survey,{personal:true,signal});},
 reply(question:string,context:{productId?:string;survey?:Survey;history:{role:'user'|'assistant';text:string}[]},signal?:AbortSignal){return request<ChatReply>('/api/chat',{question,...context},{personal:true,signal});}
};
