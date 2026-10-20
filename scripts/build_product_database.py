"""Build reviewable label data and SQLite from local official browser evidence.
No network. OCR candidates are never promoted to reviewed facts automatically.
"""
import csv,hashlib,json,re,sqlite3
from apply_label_reviews import apply_reviews
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/products'
DATE='2026-10-19'
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def compact(s):return re.sub(r'\s+','',s)
HEADINGS={
 'raw_materials':r'원[재]?료명(?:및함량)?|원재료및함량|원재료명및함량',
 'nutrition':r'영양[·•ㆍ・]?기능정보|영양정보|영양성분|1일섭취량당함량',
 'intake':r'섭취방법|섭취량및섭취방법|섭취량,?섭취방법',
 'cautions':r'섭취시주의사항|섭취시의주의사항|주의사항',
 'storage':r'보관방법|보관시주의사항|보관및취급시주의사항',
 'manufacturer':r'제조원|전문제조원|건강기능식품전문제조원|제조업소',
 'distributor':r'유통전문판매원|판매원',
 'food_type':r'식품의유형|식품유형|식품유형및유형|제품유형',
 'package':r'내용량|포장단위별용량\(중량\)|포장단위별내용물의용량\(중량\),?수량|용량및수량',
 'function':r'기능정보|기능성정보',
 'product_name':r'제품명|상품명',
 'expiry':r'소비기한|소비기한또는품질유지기한',
 'other':r'내포장재질|반품및교환처|반품및교환장소|소비자상담번호|소비자상담실|제조국|품목보고번호|건강기능식품이력추적관리번호'}
def heading(text):
 s=compact(text).lstrip('•·※*|').rstrip(':：|')
 for k,pat in HEADINGS.items():
  if re.match(r'^(?:'+pat+r')(?:[:：]|$)',s):return k
  m=re.match(r'^(?:'+pat+r')',s)
  if m and len(s)>len(m.group(0)) and (k in {'raw_materials','intake','nutrition'}):return k
 return None

def clean_lines(d):
 out=[]
 for row in d['lines']:
  # Overlapping OCR tiles may read the same physical line twice.
  if any(compact(row['text'])==compact(x['text']) and abs(row['y']-x['y'])<55 for x in out[-20:]):continue
  out.append(row)
 return sorted(out,key=lambda r:(round(r['y']/9),r['x']))

def sections(lines):
 # Preserve column/reading-order uncertainty: each result stays an OCR candidate.
 marks=[(i,heading(r['text'])) for i,r in enumerate(lines) if heading(r['text'])]
 found=[]
 for n,(i,key) in enumerate(marks):
  if key=='other':continue
  prev=marks[n-1][0] if n else max(0,i-3)
  nxt=marks[n+1][0] if n+1<len(marks) else min(len(lines),i+15)
  # Include nearby preceding value lines because table labels are often vertically centered.
  start=max(prev+1,i-6)
  if key in {'nutrition','function'}:start=max(prev+1,i-3)
  selected=lines[start:nxt]
  txt='\n'.join(r['text'] for r in selected)
  if len(txt)>5:found.append({'field':key,'raw_text':txt,'line_start':start,'line_end':nxt,'status':'ocr_section_candidate','reason':'표의 좌우 열·구간 경계 미검증; 원문 이미지 대조 필요'})
 # Explicit allergy statements may live outside a table.
 for i,row in enumerate(lines):
  if any(w in row['text'] for w in ['함유','같은 제조','같은제조','동일한 제조','알레르기']):
   txt='\n'.join(r['text'] for r in lines[max(0,i-1):min(len(lines),i+4)])
   found.append({'field':'allergen_or_cross_contact','raw_text':txt,'line_start':max(0,i-1),'line_end':min(len(lines),i+4),'status':'ocr_section_candidate','reason':'알레르기·교차오염 문구 후보; 직접 함유와 같은 시설 문구를 자동 병합하지 않음'})
 return found

NAMES=['프로바이오틱스 수','프로바이오틱스수','프로바이오틱스','비타민B12','비타민B6','비타민B2','비타민B1','비타민D3','비타민A','비타민C','비타민D','비타민E','비타민K','판토텐산','나이아신','비오틴','엽산','마그네슘','칼슘','아연','셀레늄','셀렌','철분','철','망간','구리','크롬','몰리브덴','요오드','단백질','탄수화물','포화지방','트랜스지방','지방','나트륨','당류','콜레스테롤','열량','식이섬유','칼륨','루테인','지아잔틴','실리마린','감마리놀렌산','테아닌','코엔자임Q10','총 HCA','HCA','EPA와DHA의합','EPA 및 DHA의 합','홍삼성분','진세노사이드','바나바잎추출물','코로솔산','MSM']
# No unit conversion. Original unit strings remain alongside normalized symbols.
amount_re=r'([\d][\d,]*(?:\.\d+)?)\s*(mg\s*NE|[μµu]g\s*DFE|[μµu]g\s*RE|mg|[μµu]g|㎍|㎎|g|kcal|IU|CFU)(?![A-Za-z])'
name_re='|'.join(re.escape(x) for x in sorted(NAMES,key=len,reverse=True))
nutrient_pattern=re.compile(r'(?P<name>'+name_re+r')\s*[:：]?\s*'+amount_re+r'(?P<qualifier>\s*미만|\s*이하|\s*이상)?(?:\s*\(\s*(?P<pct>[\d,.]+)\s*%\s*\))?',re.I)

def nutrients(lines,blocks):
 # Restrict to candidate nutrition blocks; never mine marketing copy globally.
 nutrition=[b for b in blocks if b['field']=='nutrition']
 out=[];seen=set()
 for block in nutrition:
  txt=block['raw_text'];flat=re.sub(r'\s+',' ',txt)
  nearby='\n'.join(x['text'] for x in lines[max(0,block['line_start']-6):min(len(lines),block['line_end']+4)])
  bases=re.findall(r'(?:1일\s*섭취량\s*[:：]?\s*[^\n]{1,75}|총\s*내용량\s*[^\n]{1,75}|100\s*g\s*당[^\n]{0,30}|1회\s*제공량[^\n]{1,50})',nearby)
  basis=bases[-1] if bases else None
  for m in nutrient_pattern.finditer(flat):
   name=m.group('name');amount=m.group(2);unit=m.group(3);pct=m.group('pct');qual=m.group('qualifier')
   try:num=float(amount.replace(',',''))
   except ValueError:continue
   key=(compact(name).lower(),amount,unit,basis)
   if key in seen:continue
   seen.add(key)
   out.append({'name_raw':name,'amount':num,'amount_raw':amount,'operator':'<' if qual and '미만' in qual else ('<=' if qual and '이하' in qual else ('>=' if qual and '이상' in qual else '=')),'unit_raw':unit,'basis_raw':basis,'basis_status':'ocr_candidate_linkage_pending' if basis else 'unverified','basis_missing_reason':None if basis else '명시된 기준 구간을 자동 연결하지 못함','nrv_percent_raw':pct,'raw_text':m.group(0),'status':'ocr_candidate','classification':'nutrition_or_functional_label_candidate','reason':'OCR 글자·소수점·단위·기준 연결 및 패널 범위 시각 대조 미완료'})
 return out

def split_ingredients(txt):
 # Keep compound parentheses intact, and never invent sub-ingredient amounts.
 txt=re.sub(r'원[재]?료명\s*(?:및\s*함량)?','',txt).strip()
 result=[];start=0;depth=0
 for i,c in enumerate(txt):
  if c in '([{（':depth+=1
  elif c in ')]}）':depth=max(0,depth-1)
  elif c in ',，' and depth==0:
   result.append(txt[start:i].strip());start=i+1
 result.append(txt[start:].strip())
 return [x for x in result if len(x)>1]

catalog=json.loads((DATA/'catalog-discovery.json').read_text())
ledger=json.loads((DATA/'collection-ledger.json').read_text());led={x['product_number']:x for x in ledger['products']}
pilot=json.loads((DATA/'pilot-products.json').read_text());pil={x['fields']['daiso_product_number']['value']:x for x in pilot['products']}
manual_path=DATA/'visual-reviews.json';manual=json.loads(manual_path.read_text()) if manual_path.exists() else {'reviews':[]}
reviews={r['product_number']:r for r in manual['reviews']}
products=[];source_seq=0
for item in catalog['products']:
 pid=item['product_number'];l=led[pid];sources=[];blocks=[];nut=[];ings=[]
 for asset in l.get('label_assets',[]):
  source_seq+=1;sid=f'label-{source_seq:04d}'
  ocrpath=ROOT/(asset['local_path']+'.ocr.json')
  src={**asset,'id':sid,'ocr_path':str(ocrpath.relative_to(ROOT)) if ocrpath.exists() else None,'raw_ocr_text':None,'ocr_status':'missing','missing_reason':None}
  if ocrpath.exists():
   od=json.loads(ocrpath.read_text());lines=clean_lines(od);src['raw_ocr_text']='\n'.join(x['text'] for x in lines);src['ocr_status']='ocr_pending_visual';bs=sections(lines)
   for b in bs:b['source_id']=sid
   blocks+=bs
   for n in nutrients(lines,bs):n['source_id']=sid;nut.append(n)
   # Do not force a full list if table boundaries are uncertain.
   for b in bs:
    if b['field']=='raw_materials':
     for order,x in enumerate(split_ingredients(b['raw_text'])):
      ings.append({'name_raw':x,'amount':None,'unit':None,'amount_missing_reason':'원재료 배합량 미정량/미검수; 원문 블록 참조','parent_id':None,'source_id':sid,'block_raw':b['raw_text'],'ordinal':order,'status':'ocr_ingredient_candidate','reason':'쉼표 기준 후보 분리; 표 경계·오독·복합원료 계층 검수 필요'})
  else:src['missing_reason']='라벨 파일은 확보했으나 OCR 미완료'
  sources.append(src)
 # Remove exact repeated candidates across duplicate panel images, retaining all sources.
 unique=[];seen={}
 for n in nut:
  key=(n['name_raw'],n['amount'],n['unit_raw'],n['basis_raw'])
  if key in seen:
   seen[key].setdefault('duplicate_source_ids',[]).append(n['source_id']);continue
  seen[key]=n;unique.append(n)
 nut=unique
 # Preserve pilot evidence separately; it was partial, not a new independent review.
 prior=[]
 if pid in pil:
  for n in pil[pid]['functional_components']:
   f=n['amount'];v=f['value'];prior.append({'name':n['name'],'amount':v['amount'],'unit':v['unit'],'basis':v['basis'],'basis_quantity':v['daily_tablets'],'raw_text':f['raw'],'source_url':f['source_url'],'method':f['method'],'status':'prior_partial_evidence'})
 def field(k):
  values=[b for b in blocks if b['field']==k]
  return {'value':None,'status':'unverified','missing_reason':'라벨 후보 블록은 있으나 정규화 확정 전' if values else '해당 표시 구간을 자동 식별하지 못함','candidate_blocks':values}
 product={'product_number':pid,'name':item['display_name'],'brand_display':item['displayed_brand_or_company'],'detail_url':item['detail_url'],'observed_on':DATE,'price':{'amount':item['price_krw'],'currency':'KRW','basis':item['price_basis'],'source_url':item['source_url'],'observed_on':item['observed_on'],'method':'official_list_card'},'package_display':item['package_text'],'sources':sources,'fields':{k:field(k) for k in ['product_name','manufacturer','distributor','food_type','package','raw_materials','nutrition','function','intake','cautions','storage','allergen_or_cross_contact']},'ingredient_candidates':ings,'nutrient_candidates':nut,'prior_nutrient_evidence':prior,'attempts':l['attempts'],'label_assets_saved':bool(sources),'collection_status':'partial_structured' if blocks else ('label_saved_pending_structure' if sources else 'access_failed'),'manufacturer_cross_check':'same_variant_manufacturer_site_not_confirmed','review':reviews.get(pid),'recommendation_eligible':False,'eligibility_reasons':['원재료·함량·전체 주의사항의 전수 시각 검수 미완료','독립 제2검수 없음','제조사 자체 동일 변형 교차확인 미완료']}
 product['reviewed_nutrients']=[]
 product['reviewed_ingredients']=[]
 if pid in reviews:
  rev=reviews[pid]
  source=next((x for x in sources if x['sha256']==rev['source_sha256']),None)
  if source:
   sid=source['id']
   for k,v in rev.get('field_values',{}).items():
    product['fields'][k]={'value':v,'raw_text':v,'source_id':sid,'status':'direct_visual','missing_reason':None,'candidate_blocks':product['fields'].get(k,{}).get('candidate_blocks',[])}
   for k,reason in rev.get('field_absences',{}).items():
    product['fields'][k]={'value':None,'status':'not_displayed_in_observed_label','missing_reason':reason,'source_id':sid,'candidate_blocks':[]}
   for n in rev['reviewed_nutrients']:
    product['reviewed_nutrients'].append({**n,'source_id':sid})
   for order,name in enumerate(rev.get('reviewed_ingredients',[])):
    product['reviewed_ingredients'].append({'name_raw':name,'amount':None,'unit':None,'amount_missing_reason':'라벨에 해당 원료의 배합량 미표시; 질량 추정하지 않음','parent_id':None,'source_id':sid,'block_raw':product['fields'].get('raw_materials',{}).get('raw_text',name),'ordinal':order,'status':'direct_visual','reason':'원료 구간 직접 대조; 복합원료·캡슐기제는 원문 묶음을 보존'})
   direct_names={compact(n['name_raw']).lower() for n in product['reviewed_nutrients']}
   for n in product['nutrient_candidates']:
    if compact(n['name_raw']).lower() in direct_names:
     n['status']='ocr_candidate_superseded'
     n['reason']='동일 성분의 직접 시각 대조 행을 우선 사용; OCR 후보는 이력으로 보존'
 product['structure_status']='partial_with_visual_sample' if pid in reviews else 'ocr_candidates_pending_visual'
 products.append(product)
review_ledger_path=DATA/'label-review-ledger.json'
review_ledger=json.loads(review_ledger_path.read_text()) if review_ledger_path.exists() else {}
corrections=apply_reviews(products,review_ledger,split_ingredients)
dump(DATA/'label-review-corrections.json',{'changes':corrections})
summary={'products':len(products),'attempted':sum(bool(p['attempts']) for p in products),'label_assets_saved':sum(p['label_assets_saved'] for p in products),'ocr_products':sum(any(s['raw_ocr_text'] for s in p['sources']) for p in products),'raw_material_blocks_products':sum(bool(p['fields']['raw_materials']['candidate_blocks']) for p in products),'nutrient_candidate_products':sum(bool(p['nutrient_candidates']) for p in products),'ingredient_candidate_rows':sum(len(p['ingredient_candidates']) for p in products),'nutrient_candidate_rows':sum(len(p['nutrient_candidates']) for p in products),'direct_visual_nutrient_rows':sum(len(p['reviewed_nutrients']) for p in products),'direct_visual_ingredient_rows':sum(len(p['reviewed_ingredients']) for p in products),'historical_visual_sample_products':sum(bool(p['review']) for p in products),'visual_inspected_products':sum(bool(p.get('label_review',{}).get('visual_inspection')) for p in products),'prior_nutrient_rows':sum(len(p['prior_nutrient_evidence']) for p in products),'full_label_verified':sum(p.get('data_review_status')=='verified' for p in products),'review_status_counts':dict(Counter(p.get('data_review_status','pending') for p in products)),'recommendation_eligible':0,'status_counts':dict(Counter(p['collection_status'] for p in products))}
normalized={'schema_version':'0.3','observed_on':DATE,'summary':summary,'products':products}
dump(DATA/'products-normalized.json',normalized)
# SQLite is an actual queryable database; all provisional information carries status.
schema=(ROOT/'scripts/product_schema.sql').read_text()
tmp=DATA/'products.building.sqlite3'
if tmp.exists():tmp.unlink()
con=sqlite3.connect(tmp);con.executescript(schema)
for p in products:
 pid=p['product_number'];con.execute('INSERT INTO products VALUES(?,?,?,?,?,?,?,?,?,?)',(pid,p['name'],p['brand_display'],p['detail_url'],DATE,p['collection_status'],int(p['label_assets_saved']),0,p['manufacturer_cross_check'],json.dumps(p['eligibility_reasons'],ensure_ascii=False)))
 con.execute('INSERT INTO prices(product_id,amount,currency,basis,source_url,observed_on,method) VALUES(?,?,?,?,?,?,?)',(pid,p['price']['amount'],'KRW',p['price']['basis'],p['price']['source_url'],DATE,'official_list_card'))
 for s in p['sources']:
  con.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?)',(s['id'],pid,s['source_url'],s['local_path'],s['sha256'],s.get('observed_on',DATE),s.get('published_on'),s.get('method',s['ocr_status']),s['raw_ocr_text'],s['missing_reason']))
 for field,f in p['fields'].items():
  con.execute('INSERT INTO product_fields VALUES(?,?,?,?,?,?,?)',(pid,field,json.dumps(f['value'],ensure_ascii=False) if f['value'] is not None else None,f['status'],f['missing_reason'],f.get('raw_text'),f.get('source_id')))
  for b in f['candidate_blocks']:
   con.execute('INSERT INTO label_blocks(product_id,source_id,field_name,raw_text,status,reason,line_start,line_end) VALUES(?,?,?,?,?,?,?,?)',(pid,b['source_id'],field,b['raw_text'],b['status'],b['reason'],b['line_start'],b['line_end']))
 for i in p['ingredient_candidates']+p['reviewed_ingredients']:
  cur=con.execute('INSERT OR IGNORE INTO ingredients(name_raw) VALUES(?)',(i['name_raw'],));iid=con.execute('SELECT id FROM ingredients WHERE name_raw=?',(i['name_raw'],)).fetchone()[0]
  con.execute('INSERT INTO product_ingredients(product_id,ingredient_id,source_id,ordinal,parent_id,amount,unit,amount_missing_reason,raw_text,status,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(pid,iid,i['source_id'],i['ordinal'],None,None,None,i['amount_missing_reason'],i['block_raw'],i['status'],i['reason']))
 for n in p['nutrient_candidates']+p['reviewed_nutrients']:
  con.execute('INSERT INTO nutrient_amounts(product_id,source_id,name_raw,amount,amount_raw,unit_raw,basis_raw,basis_status,basis_missing_reason,nrv_percent_raw,raw_text,status,classification,reason,duplicate_source_ids,operator) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,n['source_id'],n['name_raw'],n['amount'],n['amount_raw'],n['unit_raw'],n['basis_raw'],n['basis_status'],n['basis_missing_reason'],n['nrv_percent_raw'],n['raw_text'],n['status'],n['classification'],n['reason'],json.dumps(n.get('duplicate_source_ids',[])),n['operator']))
 for n in p['prior_nutrient_evidence']:
  con.execute('INSERT INTO prior_nutrient_evidence(product_id,name,amount,unit,basis,basis_quantity,raw_text,source_url,method,status) VALUES(?,?,?,?,?,?,?,?,?,?)',(pid,n['name'],n['amount'],n['unit'],n['basis'],n['basis_quantity'],n['raw_text'],n['source_url'],n['method'],n['status']))
 for a in p['attempts']:
  con.execute('INSERT INTO collection_attempts(product_id,attempt_date,method,result,source_url,reason) VALUES(?,?,?,?,?,?)',(pid,a['date'],a['method'],a['result'],a['source_url'],a.get('reason')))
 if p['review']:con.execute('INSERT INTO reviews(product_id,review_json) VALUES(?,?)',(pid,json.dumps(p['review'],ensure_ascii=False)))
for p in products:
 if p.get('label_review'):
  r=p['label_review'];con.execute('INSERT INTO label_reviews VALUES(?,?,?,?,?,?)',(p['product_number'],p['data_review_status'],r['reviewed_at'],r['source_match'],int(r.get('visual_inspection',False)),json.dumps(r,ensure_ascii=False)))
 for key,f in p['fields'].items():
  if f.get('reviewed_at'):con.execute('INSERT INTO field_review_dates VALUES(?,?,?)',(p['product_number'],key,f['reviewed_at']))
for v in corrections:
 con.execute('INSERT INTO correction_history(product_id,field_name,old_json,new_json,reason,source_id,reviewed_at) VALUES(?,?,?,?,?,?,?)',(v['product_id'],v['field'],json.dumps(v['old'],ensure_ascii=False),json.dumps(v['new'],ensure_ascii=False),v['reason'],v['source_id'],v['reviewed_at']))
con.commit();con.close();tmp.replace(DATA/'products.sqlite3')
with (DATA/'nutrient-candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
 cols=['product_number','name_raw','amount','amount_raw','operator','unit_raw','basis_raw','basis_status','nrv_percent_raw','raw_text','status','source_url'];w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader()
 for p in products:
  srcs={s['id']:s['source_url'] for s in p['sources']}
  for n in p['nutrient_candidates']:w.writerow({**n,'product_number':p['product_number'],'source_url':srcs[n['source_id']]})
print(json.dumps(summary,ensure_ascii=False,indent=2))

with (DATA/'nutrients-reviewed.csv').open('w',encoding='utf-8-sig',newline='') as f:
 cols=['product_number','name_raw','amount','amount_raw','operator','unit_raw','basis_raw','nrv_percent_raw','raw_text','status','source_url'];w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader()
 for p in products:
  srcs={s['id']:s['source_url'] for s in p['sources']}
  for n in p['reviewed_nutrients']:w.writerow({**n,'product_number':p['product_number'],'source_url':srcs[n['source_id']]})
