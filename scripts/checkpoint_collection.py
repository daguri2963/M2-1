"""Record a completed browser batch and preserve existing successful evidence.
usage: checkpoint_collection.py START END [failed_id:reason ...]
Indices are zero-based, END exclusive in catalog order.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'data/products/collection-ledger.json';d=json.loads(p.read_text());start,end=map(int,sys.argv[1:3]);fail=dict(s.split(':',1) for s in sys.argv[3:])
for r in d['products'][start:end]:
 reason=fail.get(r['product_number'])
 event={'date':'2026-10-19','method':'browser_detail_attempt','source_url':r['detail_url'],'result':'label_assets_saved' if r.get('label_assets') else 'retry_needed','reason':reason}
 if event not in r['attempts']:r['attempts'].append(event)
 if not r.get('label_assets'):r['status']='retry_needed';r['failure_reason']=reason or '브라우저 상세 로딩 또는 이미지 자산 지연; 저장 증거 미확보'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
cp=ROOT/'data/products/checkpoints'/f'batch-{start+1:02d}-{end:02d}.json';cp.write_text(json.dumps(d['products'][start:end],ensure_ascii=False,indent=2)+'\n')
print('Attempted:',sum(bool(r['attempts']) for r in d['products']),'Saved:',sum(bool(r.get('label_assets')) for r in d['products']))
