export type Survey = {interests:string[]; habits:string[]; existing:string; productIds:string[]; cautions:string[]; budget:string; form:string;specialtyConfirmed:boolean};
export const emptySurvey:Survey={interests:[],habits:[],existing:'',productIds:[],cautions:[],budget:'',form:'',specialtyConfirmed:false};
export const interestDescriptions:Record<string,string>={
 '일상의 활력':'에너지 대사 관련 성분과 표시를 알아봐요.',
 '뼈·근육 건강':'뼈와 정상적인 근육 기능을 구분해 살펴봐요.',
 '장 건강':'유산균·프리바이오틱스의 기능을 비교해요.',
 '혈당 관리':'식후 혈당 관련 기능 표시를 살펴봐요.',
 '다이어트':'체지방 감소 기능 표시를 살펴봐요.',
};
export const interestOptions=Object.keys(interestDescriptions);
export const needsSpecialtyCheck=(s:Survey)=>s.interests.some(g=>g==='혈당 관리'||g==='다이어트');
export function toggleChoice(current:string[],value:string,exclusive:string[]=[]):string[]{
 if(current.includes(value))return current.filter(v=>v!==value);
 return exclusive.includes(value)?[value]:[...current.filter(v=>!exclusive.includes(v)),value];
}
export function validateStep(step:number,s:Survey):string|null{
 if(step===1&&(!s.interests.length||s.interests.some(g=>!interestOptions.includes(g))))return '다섯 관심 분야 중 하나 이상 선택해 주세요.';
 if(step===2&&!s.habits.length)return '식습관을 하나 이상 선택해 주세요. 잘 모르겠어요도 선택할 수 있어요.';
 if(step===3&&(!s.existing||(s.existing==='제품 선택'&&!s.productIds.length)))return '현재 제품 상태를 선택해 주세요. 제품 선택 시 목록에서 하나 이상 골라 주세요.';
 if(step===4&&!s.cautions.length)return '확인할 조건을 선택해 주세요. 잘 모르겠어요도 괜찮아요.';
 if(step===4&&needsSpecialtyCheck(s)&&s.cautions.length===1&&s.cautions[0]==='해당 없어요'&&!s.specialtyConfirmed)return '혈당 관리·다이어트 안내 범위와 주의조건을 확인해 주세요.';
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
