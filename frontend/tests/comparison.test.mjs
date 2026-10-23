import test from 'node:test';
import assert from 'node:assert/strict';
import {scheduleComparison} from '../src/comparison-request.ts';
const tick=()=>new Promise(resolve=>setTimeout(resolve,5));

test('intermediate selections are cancelled before an AI request is sent',async()=>{
 let calls=0;
 const cancel=scheduleComparison(['a','b'],async()=>{calls++;return {productIds:['a','b']};},()=>assert.fail('cancelled'),()=>assert.fail('cancelled'),0);
 cancel();await tick();assert.equal(calls,0);
});

test('late response and error from replaced products never overwrite the new pair',async()=>{
 let resolveOld;const output=[];
 const cancel=scheduleComparison(['a','b'],()=>new Promise(resolve=>{resolveOld=resolve;}),data=>output.push(data.productIds),()=>output.push('error'),0);
 await tick();cancel();
 const cancelNew=scheduleComparison(['a','c'],async()=>({productIds:['a','c']}),data=>output.push(data.productIds),()=>output.push('error'),0);
 await tick();resolveOld({productIds:['a','b']});await tick();assert.deepEqual(output,[['a','c']]);
 cancelNew();
 let reject;
 const cancelError=scheduleComparison(['d','e'],()=>new Promise((_,r)=>{reject=r;}),()=>output.push('old'),()=>output.push('error'),0);
 await tick();cancelError();reject(new Error('late'));await tick();assert.deepEqual(output,[['a','c']]);
});

test('mismatched product order is an explicit failure and failure can be retried',async()=>{
 const errors=[],output=[];
 const cancel=scheduleComparison(['a','b'],async()=>({productIds:['b','a']}),data=>output.push(data),error=>errors.push(error.message),0);
 await tick();assert.equal(errors.length,1);assert.equal(output.length,0);cancel();
 const retry=scheduleComparison(['a','b'],async()=>({productIds:['a','b']}),data=>output.push(data),error=>errors.push(error.message),0);
 await tick();assert.equal(output.length,1);assert.equal(errors.length,1);retry();
});
