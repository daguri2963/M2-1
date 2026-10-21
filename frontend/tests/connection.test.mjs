import test from 'node:test';
import assert from 'node:assert/strict';
import {waitUntilReady} from '../src/connection.ts';

test('sleeping backend shows warming and resumes automatically when health succeeds',async()=>{
 let clock=0,calls=0;const states=[];
 const result=await waitUntilReady({probe:async()=>{calls++;if(calls<3)throw new Error('sleeping');return {ready:true,version:'test'};},onState:s=>states.push(s),now:()=>clock,sleep:async ms=>{clock+=ms;}});
 assert.equal(result.version,'test');assert.equal(calls,3);assert.equal(clock,4000);assert.deepEqual(states,['checking','warming','warming','ready']);
});
test('readiness has a bounded deadline and ends in a retryable offline state',async()=>{
 let clock=0;const states=[];
 await assert.rejects(waitUntilReady({probe:async()=>({ready:false}),onState:s=>states.push(s),now:()=>clock,sleep:async ms=>{clock+=ms;},timeoutMs:6000}),/deadline/);
 assert.equal(clock,6000);assert.equal(states.at(-1),'offline');
});
