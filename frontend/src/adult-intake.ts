export type LabelNutrient={name:string;amount:string;unit:string;basis:string|null;operator:string};
export type AdultIntakeReference={unit:string;kind:string;values:Record<string,string>;sourcePdfPage:number};
export type AdultIntakeReferences={groups:{id:string;label:string}[];nutrients:Record<string,AdultIntakeReference>};
export type AdultIntakeComparison={status:'ok';percent:number;percentText:string;referenceAmount:string;referenceUnit:string;kind:'RNI'|'AI';sourcePdfPage:number}|{status:'unavailable';reason:string};

const normalizeUnit=(unit:string)=>unit.replace(/\s/g,'').replace(/µ/g,'μ').replace(/^(?:ug|mcg)/,'μg').toLowerCase();
const numeric=(value:string)=>/^(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$/.test(value.trim())?Number(value.replace(/,/g,'')):NaN;
const massUnits:Record<string,number>={'g':1_000_000,'mg':1_000,'μg':1};

export function compareAdultIntake(nutrient:LabelNutrient,groupId:string,data:AdultIntakeReferences):AdultIntakeComparison{
 const name=nutrient.name==='셀렌'?'셀레늄':nutrient.name;
 const reference=data.nutrients[name];
 if(!reference)return {status:'unavailable',reason:'성인 기준 없음'};
 if(!/^\s*1\s*일\s*(?:섭취량|섭취|분량|기준)/.test(nutrient.basis||''))return {status:'unavailable',reason:'하루 분량 미확인'};
 if(nutrient.operator!=='=')return {status:'unavailable',reason:'정확한 함량 미확인'};
 const sourceUnit=normalizeUnit(nutrient.unit),targetUnit=normalizeUnit(reference.unit);
 let factor=1;
 if(sourceUnit!==targetUnit){
  if(!massUnits[sourceUnit]||!massUnits[targetUnit])return {status:'unavailable',reason:'단위 기준이 달라요'};
  factor=massUnits[sourceUnit]/massUnits[targetUnit];
 }
 const amount=numeric(nutrient.amount);
 if(!Number.isFinite(amount)||amount<0)return {status:'unavailable',reason:'함량 확인 필요'};
 if(!data.groups.some(group=>group.id===groupId))return {status:'unavailable',reason:'비교 기준 선택'};
 const referenceAmount=reference.values[groupId];
 const daily=referenceAmount===undefined?NaN:numeric(referenceAmount);
 if(!Number.isFinite(daily)||daily<=0||!['RNI','AI'].includes(reference.kind))return {status:'unavailable',reason:'성인 기준 미확인'};
 const percent=amount*factor/daily*100;
 if(!Number.isFinite(percent))return {status:'unavailable',reason:'계산 확인 필요'};
 const rounded=Math.round((percent+Number.EPSILON)*10)/10;
 return {status:'ok',percent:rounded,percentText:percent>0&&percent<0.1?'0.1% 미만':`${rounded}%`,referenceAmount,referenceUnit:reference.unit,kind:reference.kind as 'RNI'|'AI',sourcePdfPage:reference.sourcePdfPage};
}
