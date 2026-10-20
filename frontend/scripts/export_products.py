"""Export only reviewed public product facts. No OCR, candidates or audit ledger."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
data=json.loads((root/'data/products/products-normalized.json').read_text())
products=[]
for p in data['products']:
 if p.get('data_review_status')!='verified':continue
 def value(k):
  f=p['fields'].get(k,{})
  return f.get('value') if f.get('status')=='direct_visual' else None
 products.append({'id':p['product_number'],'name':value('product_name') or p['name'],'displayName':p['name'],'brand':p['brand_display'],'type':value('food_type'),'package':('600 mg × 12정' if p['product_number']=='032306200' else value('package')),'form':value('dosage_form'),'price':p['price']['amount'],'priceDate':p['price']['observed_on'],'sourceUrl':p['detail_url'],'checkedAt':p['label_review']['reviewed_at'][:10],'observedAt':p['observed_on'],'intake':value('intake'),'cautions':value('cautions'),'allergen':value('allergen_or_cross_contact'),'storage':value('storage'),'ingredients':value('raw_materials'),'functionText':value('function'),'nutrients':[{'name':n['name_raw'],'amount':n['amount_raw'],'operator':n['operator'],'unit':n['unit_raw'],'basis':n['basis_raw'],'percent':n['nrv_percent_raw']} for n in p['reviewed_nutrients']]})
assert len(products)==87 and all(p['id']!='600651654' for p in products)
(root/'frontend/src/data/products.json').write_text(json.dumps(products,ensure_ascii=False,separators=(',',':'))+'\n')
print(f'Exported {len(products)} verified products; no OCR/candidates/held products')
