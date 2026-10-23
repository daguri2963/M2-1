import type {ComparisonExplanation} from './services';

type FetchExplanation=(ids:string[],signal:AbortSignal)=>Promise<ComparisonExplanation>;
/** Cancel intermediate selections and ignore every response belonging to a replaced pair. */
export function scheduleComparison(ids:string[],request:FetchExplanation,onResult:(data:ComparisonExplanation)=>void,onError:(error:unknown)=>void,delay=350){
 const selected=[...ids];
 const key=selected.join(',');
 const controller=new AbortController();
 const timer=setTimeout(()=>{
  request(selected,controller.signal).then(data=>{
   if(controller.signal.aborted)return;
   if(data.productIds.join(',')!==key)throw new Error('선택한 제품과 해설이 일치하지 않아 표시하지 않았어요. 다시 시도해 주세요.');
   onResult(data);
  }).catch(error=>{if(!controller.signal.aborted)onError(error);});
 },delay);
 return()=>{clearTimeout(timer);controller.abort();};
}
