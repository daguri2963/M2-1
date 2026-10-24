import {useState,type ReactNode} from 'react';
import {ChevronDown} from 'lucide-react';
import type {ChatNutritionSummary} from './services';
import references from './data/adult-intake-references.json';
import {compareAdultIntake} from './adult-intake';

function NutrientRows({items,groupId}:{items:ChatNutritionSummary['nutrients'];groupId:string}){
 return <table className="chat-nutrition-table"><thead><tr><th scope="col">성분</th><th scope="col">함량</th><th scope="col">성인 1일 기준 대비</th></tr></thead><tbody>{items.map((n,i)=>{const comparison=compareAdultIntake(n,groupId,references);return <tr key={`${n.name}-${i}`}><th scope="row">{n.name}<small>{n.basis||'분량 기준 미확인'}</small></th><td>{n.operator==='='?'':n.operator}{n.amount} {n.unit||'단위 미확인'}</td><td>{comparison.status==='ok'?<><strong>{comparison.percentText}</strong><small>{comparison.kind==='RNI'?'권장':'충분'} {comparison.referenceAmount} {comparison.referenceUnit}/일</small></>:<span className="muted">{comparison.reason}</span>}</td></tr>;})}</tbody></table>;
}

export function ChatNutritionFacts({summary}:{summary:ChatNutritionSummary}){
 const [groupId,setGroupId]=useState('');
 const visible=summary.nutrients.slice(0,4);const more=summary.nutrients.slice(4);
 return <section className="chat-nutrition-facts" aria-label={`${summary.productName} 주요 영양정보`}><h3>먼저, 얼마나 들어 있나요?</h3>{visible.length?<><label className="adult-reference-picker">비교할 성인 기준<select aria-label="비교할 성인 섭취기준" value={groupId} onChange={event=>setGroupId(event.target.value)}><option value="">성별·연령 기준을 선택해 주세요</option>{references.groups.map(group=><option key={group.id} value={group.id}>{group.label}</option>)}</select></label><NutrientRows items={visible} groupId={groupId}/></>:<p>확인된 주요 성분의 정량 정보가 없어요. 함유량이 0이라는 뜻은 아니에요.</p>}{more.length>0&&<details className="disclosure"><summary>나머지 성분 {more.length}개 보기 <ChevronDown size={15}/></summary><NutrientRows items={more} groupId={groupId}/></details>}<p className="chat-reference-note">식사와 영양제 등을 합한 하루 권장·충분섭취량과 비교해요. 개인의 필요량·부족분·흡수율이나 안전성을 뜻하지 않아요. 일반 성인 기준이며 임신·수유는 포함하지 않아요.</p><a className="chat-reference-source" href={references.source.url} target="_blank" rel="noreferrer">출처: 2025 한국인 영양소 섭취기준</a></section>;
}

export function ChatProductLabelDetails({summary,children}:{summary:ChatNutritionSummary;children:ReactNode}){
 return <details className="disclosure chat-label-details"><summary>제품 표시와 자세한 근거 보기 <ChevronDown size={15}/></summary><div className="chat-label-sections">{([['표시된 기능정보','functionText'],['표시 섭취방법','intake'],['표시 주의사항','cautions'],['알레르기·같은 제조시설','allergen']] as const).map(([title,key])=><section key={key}><h4>{title}</h4><p>{summary.label[key]||'관찰한 표시에서 확인하지 못했어요.'}</p></section>)}{children}<a className="text-link" href={summary.sourceUrl} target="_blank" rel="noreferrer">공식 제품 페이지</a><span className="small muted"> · 표시 검수 {summary.checkedAt}</span></div></details>;
}
