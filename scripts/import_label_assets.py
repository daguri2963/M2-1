"""Import only browser-exported official label assets; no network requests."""
import json,shutil,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ledger_path=ROOT/'data/products/collection-ledger.json'
ledger=json.loads(ledger_path.read_text())
lookup={p['product_number']:p for p in ledger['products']}
cache=Path('/var/folders/yz/kzzkpplj73qbzchy819k7v0m0000gn/T/browser-use/assets')
for manifest in cache.glob('*/manifest.json'):
 try:m=json.loads(manifest.read_text())
 except (OSError,ValueError):continue
 for a in m.get('assets',[]):
  url=a.get('url','')
  if 'cdn.daisomall.co.kr/' not in url or '/description/' not in url:continue
  matched=[pid for pid in lookup if pid in a.get('name','')]
  if len(matched)!=1:continue
  pid=matched[0];p=lookup[pid];src=Path(a['path'])
  if not src.exists():continue
  sha=hashlib.sha256(src.read_bytes()).hexdigest()
  dest=ROOT/'data/products/labels'/pid/(sha[:16]+src.suffix)
  dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():shutil.copy2(src,dest)
  evidence={'source_url':url,'local_path':str(dest.relative_to(ROOT)),'sha256':sha,'method':'official_label_image_saved_pending_visual','observed_on':'2026-10-19','published_on':None,'browser_manifest':str(manifest)}
  if not any(e['sha256']==sha for e in p.get('label_assets',[])):
   p.setdefault('label_assets',[]).append(evidence)
  if not any(x.get('source_url')==url for x in p['attempts']):
   p['attempts'].append({'date':'2026-10-19','method':'browser_detail_and_page_assets','source_url':url,'result':'label_asset_saved','detail_url':p['detail_url']})
  p['status']='label_assets_saved_pending_transcription'
ledger_path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
print('Persisted assets for',sum(bool(p.get('label_assets')) for p in lookup.values()),'of',len(lookup),'SKUs')
