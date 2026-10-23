import {useEffect,useState,type ReactNode} from 'react';
import {ArrowRight,ChevronDown,LoaderCircle,RotateCcw,Sparkles} from 'lucide-react';
import {api,type ComparisonExplanation} from './services';
import {scheduleComparison} from './comparison-request';

type State={key:string;data?:ComparisonExplanation;error?:string;loading?:boolean};
export function CompareExplanation({ids,consented,consentForm}:{ids:string[];consented:boolean;consentForm:ReactNode}){
 const key=ids.join(',');
 const [state,setState]=useState<State>({key:''});
 const [retry,setRetry]=useState(0);
 const [showConsent,setShowConsent]=useState(false);
 useEffect(()=>{
  setState({key,loading:consented&&ids.length===2});
  if(!consented||ids.length!==2)return;
  return scheduleComparison(ids,api.compareExplanation,
   data=>setState({key,data}),
   error=>setState({key,error:error instanceof Error?error.message:'AI 해설을 불러오지 못했어요.'}));
 },[key,consented,retry]);
 const current=state.key===key?state:undefined;
 const data=current?.data;
 return <section className="surface compare-explanation" aria-labelledby="compare-ai-title" aria-busy={Boolean(current?.loading)}>
  <header className="compare-ai-heading"><div className="compare-ai-icon"><Sparkles size={21}/></div><div><span className="eyebrow">먼저, 차이부터 가볍게</span><h2 id="compare-ai-title">AI가 짚어주는 차이점</h2></div><span className="tag pink">AI 생성 해설</span></header>
  {!consented?<div className="compare-ai-intro"><p>두 제품의 주요 성분·제형·표시 섭취방법에서 차이를 골라 쉽게 설명해요.</p><p className="small muted">선택한 두 제품의 공개 표시정보를 코디세이 API로 전송해요. 설문 답변과 대화는 사용하지 않아요. 아래 비교표는 동의 없이도 볼 수 있어요.</p><button className="button secondary" onClick={()=>setShowConsent(v=>!v)} aria-expanded={showConsent}>{showConsent?'이용 안내 접기':'안내 확인하고 AI 해설 보기'} <ArrowRight size={16}/></button>{showConsent&&<div className="compare-consent">{consentForm}</div>}</div>
  :current?.error?<div className="compare-ai-error" role="status"><p>{current.error}</p><p className="small muted">표시정보 비교표는 아래에서 계속 볼 수 있어요.</p><button className="text-link" onClick={()=>setRetry(v=>v+1)}><RotateCcw size={15}/> 해설 다시 시도</button></div>
  :!data?<div className="compare-ai-loading" role="status"><LoaderCircle className="spin" size={22}/><div><strong>두 제품의 차이를 정리하고 있어요.</strong><p className="small muted">시간이 조금 걸릴 수 있어요. 아래 비교표를 먼저 살펴봐도 좋아요.</p></div></div>
  :<>
   <p className="compare-ai-summary">{data.summary.text}</p>
   <div className="compare-ai-products">{data.products.map(p=><span key={p.id}><b>{p.label}</b>{p.name}</span>)}</div>
   <div className="compare-ai-highlights">{data.highlights.map(h=><article key={h.factId}><h3>{h.fact.title}</h3><p>{h.text}</p><details className="compare-fact"><summary>확인된 표시 보기 <ChevronDown size={14}/></summary><dl>{h.fact.values.map((value,i)=><div key={i}><dt>제품 {i===0?'A':'B'}</dt><dd>{value}</dd></div>)}</dl>{h.fact.notice&&<p className="small muted">{h.fact.notice}</p>}</details></article>)}</div>
   <div className="compare-ai-guide"><strong>고를 때는 이렇게 살펴보세요</strong><p>{data.selectionGuide.text}</p></div>
   <details className="compare-ai-sources"><summary>설명에 사용한 공식 출처 <ChevronDown size={15}/></summary><div>{data.citations.map(e=><a key={e.id} href={e.url} target="_blank" rel="noreferrer">{e.title}<small>확인 {e.observedAt}</small></a>)}</div></details>
   <p className="compare-ai-notice">{data.notice}</p>
  </>}
 </section>;
}
