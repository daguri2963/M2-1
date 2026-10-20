"""Apply explicit visual decisions; never infer review completion from OCR confidence."""
import copy, json, re
REQUIRED_FIELDS=('product_name','food_type','manufacturer','distributor','package','dosage_form','raw_materials','nutrition','function','intake','cautions','storage','allergen_or_cross_contact')
ACCEPTED={'direct_visual','not_displayed_in_observed_label','not_applicable'}
def review_status(p):
 r=p.get('label_review')
 if not r or not r.get('visual_inspection'):return 'pending'
 if r.get('blocking_issues'):return 'on_hold'
 return 'verified' if r.get('source_match')=='name_variant_package_matched' and all(p['fields'].get(k,{}).get('status') in ACCEPTED for k in REQUIRED_FIELDS) and r.get('completeness_confirmed',False) else 'partial'
def apply_reviews(products,ledger,split_ingredients):
 entries={x['product_number']:x for x in ledger.get('products',[])};changes=[]
 for p in products:
  r=entries.get(p['product_number'])
  if not r or not r.get('visual_inspection'):continue
  p['sources'].extend(copy.deepcopy(r.get('supplemental_sources',[])))
  p['label_review']=copy.deepcopy(r)
  source=next((s for s in p['sources'] if s['sha256'].startswith(r.get('evidence_source_sha_prefix','!'))),None)
  if not source:
   evidence_hashes={x['source_sha256'] for x in r['evidence']}
   source=max((s for s in p['sources'] if s['sha256'] in evidence_hashes),key=lambda s:len(s.get('raw_ocr_text') or ''),default=None)
  if not source:raise ValueError('Missing visual review source '+p['product_number'])
  sid=source['id'];p['label_review']['primary_source_id']=sid
  for field,value in r.get('field_values',{}).items():
   field_sid=r.get('field_source_ids',{}).get(field,sid)
   if field_sid not in {s['id'] for s in p['sources']}:raise ValueError('Unknown field source '+field_sid)
   old=copy.deepcopy(p['fields'].get(field))
   p['fields'][field]={'value':value,'raw_text':value,'source_id':field_sid,'status':'direct_visual','missing_reason':None,'reviewed_at':r['reviewed_at'],'candidate_blocks':old.get('candidate_blocks',[]) if old else []}
   if old!=p['fields'][field]:changes.append({'product_id':p['product_number'],'field':field,'old':old,'new':copy.deepcopy(p['fields'][field]),'reason':'공식 표시 근거 시각 대조 후 정규화/정정','source_id':field_sid,'reviewed_at':r['reviewed_at']})
  for field,f in r.get('field_dispositions',{}).items():
   old=copy.deepcopy(p['fields'].get(field));p['fields'][field]={'value':None,'raw_text':f.get('raw_text'),'source_id':sid,'status':f['status'],'missing_reason':f['reason'],'reviewed_at':r['reviewed_at'],'candidate_blocks':old.get('candidate_blocks',[]) if old else []}
   changes.append({'product_id':p['product_number'],'field':field,'old':old,'new':copy.deepcopy(p['fields'][field]),'reason':f['reason'],'source_id':sid,'reviewed_at':r['reviewed_at']})
  if r.get('reviewed_nutrients'):
   old=copy.deepcopy(p['reviewed_nutrients']);p['reviewed_nutrients']=[dict(n,source_id=sid,reviewed_at=r['reviewed_at']) for n in r['reviewed_nutrients']]
   changes.append({'product_id':p['product_number'],'field':'reviewed_nutrients','old':old,'new':copy.deepcopy(p['reviewed_nutrients']),'reason':'표시 영양표의 전체 정량 행을 직접 대조하여 보완; 단위 환산 없음','source_id':sid,'reviewed_at':r['reviewed_at']})
  if r.get('nutrition_panel_complete'):
   p['fields']['nutrition']={'value':{'basis_raw':r.get('nutrient_basis') or next((n['basis_raw'] for n in p['reviewed_nutrients'] if n.get('basis_raw')),None),'rows':len(p['reviewed_nutrients']),'unquantified':r.get('unquantified_nutrients',[])},'raw_text':r.get('nutrition_raw_text') or '\n'.join(n['raw_text'] for n in p['reviewed_nutrients']),'source_id':sid,'status':'direct_visual','missing_reason':None,'reviewed_at':r['reviewed_at'],'candidate_blocks':p['fields']['nutrition'].get('candidate_blocks',[])}
   # All original candidates remain available as history, excluded from reviewed views.
   for n in p['nutrient_candidates']:
    n['status']='ocr_candidate_reviewed_excluded'
    n['reason']='해당 영양 패널 전수 시각대조 행으로 대체; 광고·중복·오독 후보는 확정조회에서 제외'
  if 'raw_materials' in r.get('field_values',{}):
   raw=r['field_values']['raw_materials'];p['reviewed_ingredients']=[]
   for order,name in enumerate(split_ingredients(raw)):
    p['reviewed_ingredients'].append({'name_raw':name,'amount':None,'unit':None,'amount_missing_reason':'원문 원료명 묶음 보존; 배합량 자동 추정하지 않음(표시 비율은 raw_text 참조)','parent_id':None,'source_id':sid,'block_raw':raw,'ordinal':order,'status':'direct_visual','reason':'원료 구간 시각대조 전사; 복합원료 괄호 묶음 보존','reviewed_at':r['reviewed_at']})
   for i in p['ingredient_candidates']:
    i['status']='ocr_ingredient_reviewed_excluded';i['reason']='원료 구간 직접대조 전사로 대체; 자동 분리 후보는 이력 보존'
  p['data_review_status']=review_status(p);p['structure_status']='visual_'+p['data_review_status'];p['collection_status']='label_review_'+p['data_review_status']
  p['recommendation_eligible']=False
  p['eligibility_reasons']=['추천 정책·사용자 조건 로직은 이번 작업 범위 밖이며 평가하지 않음']
  if p['data_review_status']!='verified':p['eligibility_reasons'].append('표시정보 검수 상태 '+p['data_review_status'])
 return changes
