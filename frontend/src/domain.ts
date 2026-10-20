export type Survey = {interests:string[]; habits:string[]; existing:string; productIds:string[]; cautions:string[]; budget:string; form:string};
export const emptySurvey:Survey={interests:[],habits:[],existing:'',productIds:[],cautions:[],budget:'',form:''};
export function toggleChoice(current:string[],value:string,exclusive:string[]=[]):string[]{
 if(current.includes(value))return current.filter(v=>v!==value);
 return exclusive.includes(value)?[value]:[...current.filter(v=>!exclusive.includes(v)),value];
}
export function validateStep(step:number,s:Survey):string|null{
 if(step===1&&!s.interests.length)return '관심 분야를 하나 이상 선택해 주세요. 잘 모르겠어요도 괜찮아요.';
 if(step===2&&!s.habits.length)return '식습관을 하나 이상 선택해 주세요. 잘 모르겠어요도 선택할 수 있어요.';
 if(step===3&&(!s.existing||(s.existing==='제품 선택'&&!s.productIds.length)))return '현재 제품 상태를 선택해 주세요. 제품 선택 시 목록에서 하나 이상 골라 주세요.';
 if(step===4&&!s.cautions.length)return '확인할 조건을 선택해 주세요. 잘 모르겠어요도 괜찮아요.';
 return null;
}
export type CompareAction={ids:string[];notice?:string;replace?:string};
export function selectCompare(ids:string[],id:string):CompareAction{
 if(ids.includes(id))return {ids:ids.filter(v=>v!==id)};
 if(ids.length>=2)return {ids,notice:'한 번에 두 제품을 비교해요. 교체할 제품을 골라 주세요.',replace:id};
 return {ids:[...ids,id]};
}
export function replaceCompare(ids:string[],oldId:string,newId:string){return ids.map(id=>id===oldId?newId:id).filter((id,i,a)=>a.indexOf(id)===i).slice(0,2);}
export const resultStates=['example','loading','empty','insufficient','restricted','error'] as const;
export type ResultState=typeof resultStates[number];
export function parseRoute(hash:string){const [path,query='']=hash.replace(/^#/,'').split('?');return {path:path||'/',query:new URLSearchParams(query)};}
export function canCompareAmounts(a:{unit:string;basis:string},b:{unit:string;basis:string}){return a.unit===b.unit&&a.basis===b.basis;}

export function isHealthFood(foodType:string|null){return foodType?.startsWith('건강기능식품')===true;}
