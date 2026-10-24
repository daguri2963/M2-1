import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {compareAdultIntake} from '../src/adult-intake.ts';

const data=JSON.parse(fs.readFileSync(new URL('../src/data/adult-intake-references.json',import.meta.url),'utf8'));
const magnesium={name:'마그네슘',amount:'315',unit:'mg',operator:'=',basis:'1일 섭취량: 1정(1,000 mg)',percent:'100'};
const compare=(n=magnesium,group='male-19-29',references=data)=>compareAdultIntake(n,group,references);

test('adult percentages use the selected RNI, independent of the package reference %',()=>{
 assert.equal(compare().percent,87.5);
 assert.equal(compare({...magnesium,percent:'99999'}).percent,87.5);
 assert.equal(compare(magnesium,'female-19-29').percent,112.5);
 assert.equal(compare(magnesium,'male-30-49').percent,82.9);
 assert.equal(compare().referenceAmount,'360');
 assert.equal(compare().kind,'RNI');
});

test('vitamin D retains its AI classification and may correctly remain 100%',()=>{
 const d={...magnesium,name:'비타민D',amount:'10',unit:'ug'};
 assert.equal(compare(d).percent,100);
 assert.equal(compare(d).kind,'AI');
 assert.equal(compare(d,'female-65-74').percent,66.7);
 assert.equal(compare(d,'female-65-74').referenceAmount,'15');
});

test('four-tablet calcium is compared as the complete daily label serving',()=>{
 const ca={...magnesium,name:'칼슘',amount:'700',basis:'1일 섭취량: 4정(3.6 g)'};
 assert.equal(compare(ca).percent,87.5);
 assert.equal(compare(ca,'female-19-29').percent,107.7);
 assert.equal(ca.basis,'1일 섭취량: 4정(3.6 g)');
});

test('no demographic group is guessed and package totals are not treated as daily amounts',()=>{
 assert.deepEqual(compare(magnesium,''),{status:'unavailable',reason:'비교 기준 선택'});
 assert.equal(compare(magnesium,'unknown-group').status,'unavailable');
 assert.equal(compare({...magnesium,basis:'총 내용량 30정(30일분)'}).reason,'하루 분량 미확인');
 assert.equal(compare({...magnesium,basis:null}).status,'unavailable');
});

test('only physical mass units are converted; nutrient activity units must match',()=>{
 assert.equal(compare({...magnesium,amount:'0.315',unit:'g'}).percent,87.5);
 assert.equal(compare({...magnesium,amount:'315000',unit:'µg'}).percent,87.5);
 assert.equal(compare({...magnesium,name:'엽산',amount:'400',unit:'ug DFE'}).percent,100);
 assert.equal(compare({...magnesium,name:'엽산',amount:'400',unit:'μg'}).reason,'단위 기준이 달라요');
 assert.equal(compare({...magnesium,name:'비타민A',amount:'800',unit:'μg RAE'}).percent,100);
 assert.equal(compare({...magnesium,name:'비타민A',amount:'800',unit:'IU'}).status,'unavailable');
 assert.equal(compare({...magnesium,name:'나이아신',amount:'14',unit:'mgNE'}).percent,100);
 assert.equal(compare({...magnesium,name:'나이아신',amount:'14',unit:'mg'}).status,'unavailable');
});

test('unsupported functional ingredients get no invented adult daily requirement',()=>{
 for(const name of ['프로바이오틱스 수','코로솔산','루테올린','베타카로틴']){
  assert.deepEqual(compare({...magnesium,name}),{status:'unavailable',reason:'성인 기준 없음'});
 }
 assert.equal(compare({...magnesium,name:'셀렌',amount:'60',unit:'μg'}).percent,100);
});

test('unknown or inexact quantities never become exact percentage claims',()=>{
 assert.equal(compare({...magnesium,operator:'<'}).reason,'정확한 함량 미확인');
 for(const amount of ['미확인','1,2,3','-3','Infinity','1e3',''])assert.equal(compare({...magnesium,amount}).status,'unavailable');
 assert.equal(compare({...magnesium,amount:'0'}).percent,0);
 assert.equal(compare({...magnesium,amount:'0'}).percentText,'0%');
 assert.equal(compare({...magnesium,amount:'0.01'}).percentText,'0.1% 미만');
 assert.equal(compare({...magnesium,amount:'3,600'}).percent,1000);
 const bad=structuredClone(data);bad.nutrients['마그네슘'].values['male-19-29']='0';
 assert.equal(compare(magnesium,'male-19-29',bad).status,'unavailable');
});

test('official table extraction retains adult group, RNI/AI and source provenance',()=>{
 assert.equal(data.groups.length,10);assert.equal(Object.keys(data.nutrients).length,25);
 const expected={'비타민A':['800','650','RNI'],'비타민D':['10','10','AI'],'비타민E':['12','12','AI'],'비타민K':['75','65','AI'],'비타민C':['100','100','RNI'],'비타민B1':['1.2','1.1','RNI'],'비타민B2':['1.5','1.2','RNI'],'나이아신':['14','13','RNI'],'비타민B6':['1.5','1.4','RNI'],'엽산':['400','400','RNI'],'비타민B12':['2.4','2.4','RNI'],'판토텐산':['5.0','5.0','AI'],'비오틴':['30','30','AI'],'칼슘':['800','650','RNI'],'마그네슘':['360','280','RNI'],'칼륨':['3500','3500','AI'],'철':['8','12','RNI'],'아연':['10','8','RNI'],'구리':['850','650','RNI'],'망간':['4.0','3.5','AI'],'요오드':['150','150','RNI'],'셀레늄':['60','60','RNI'],'몰리브덴':['30','25','RNI'],'크롬':['30','20','AI'],'식이섬유':['30','20','AI']};
 for(const [name,[male,female,kind]] of Object.entries(expected)){
  const n=data.nutrients[name];assert.deepEqual([n.values['male-19-29'],n.values['female-19-29'],n.kind],[male,female,kind],name);
  assert.equal(Object.keys(n.values).length,10);assert(n.sourcePdfPage>0);assert(n.reviewStatus==='source_table_and_render_checked');
 }
 const pdf=fs.readFileSync(new URL('../../data/references/kdri-2025-summary-ko.pdf',import.meta.url));
 assert.equal(createHash('sha256').update(pdf).digest('hex'),data.source.sha256);
 assert.equal(data.source.publisher,'보건복지부·한국영양학회');
});
