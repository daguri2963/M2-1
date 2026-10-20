"""Offline checks of provenance, review gates, serialization and numeric regressions.
These checks validate stored decisions; they are not an independent visual review.
"""
import csv, hashlib, json, re, sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from apply_label_reviews import REQUIRED_FIELDS, ACCEPTED, review_status
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/products'
d=json.loads((DATA/'products-normalized.json').read_text());ps=d['products']
catalog=json.loads((DATA/'catalog-discovery.json').read_text())['products']
ledger=json.loads((DATA/'label-review-ledger.json').read_text())['products']
c=sqlite3.connect(f'file:{DATA / "products.sqlite3"}?mode=ro',uri=True);c.row_factory=sqlite3.Row
checks=[]
def check(name,condition):
 checks.append({'check':name,'passed':bool(condition)})
 if not condition:raise AssertionError(name)
def count(t):return c.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
def qty(raw):
 raw=raw.replace(',','');return float(raw[:-1])*1e8 if raw.endswith('억') else float(raw)
def rows(sql,args=()):return [tuple(r) for r in c.execute(sql,args)]
ids={p['product_number'] for p in ps}
check('exact 88 catalog identifiers',len(ps)==len(ids)==88 and ids=={p['product_number'] for p in catalog}=={p['product_number'] for p in ledger})
check('SQLite identifiers retain text and leading zeros',ids=={r[0] for r in c.execute('SELECT product_number FROM products')} and all(r[0]=='text' for r in c.execute('SELECT typeof(product_number) FROM products')))
check('SQLite integrity',rows('PRAGMA integrity_check')==[('ok',)])
check('foreign keys',not rows('PRAGMA foreign_key_check'))
expected={'products':88,'sources':sum(len(p['sources']) for p in ps),'product_fields':sum(len(p['fields']) for p in ps),'label_blocks':sum(len(f['candidate_blocks']) for p in ps for f in p['fields'].values()),'product_ingredients':sum(len(p['ingredient_candidates'])+len(p['reviewed_ingredients']) for p in ps),'nutrient_amounts':sum(len(p['nutrient_candidates'])+len(p['reviewed_nutrients']) for p in ps),'prior_nutrient_evidence':sum(len(p['prior_nutrient_evidence']) for p in ps),'collection_attempts':sum(len(p['attempts']) for p in ps),'reviews':sum(bool(p['review']) for p in ps),'label_reviews':88,'prices':88}
for table,n in expected.items():check(table+' JSON/SQLite count',count(table)==n)
for p in ps:
 pid=p['product_number'];sources={s['id']:s for s in p['sources']};r=p['label_review']
 check(pid+' substantive original OCR',any(len((s.get('raw_ocr_text') or '').splitlines())>10 for s in sources.values()))
 check(pid+' explicit visual inspection and identity match',r['visual_inspection'] and r['source_match']=='name_variant_package_matched' and r['evidence'] and r.get('completeness_confirmed'))
 check(pid+' review gate',review_status(p)==p['data_review_status'])
 check(pid+' full review serialized',json.loads(c.execute('SELECT review_json FROM label_reviews WHERE product_id=?',(pid,)).fetchone()[0])==r)
 check(pid+' required fields resolved',all(p['fields'][k]['status'] in ACCEPTED for k in REQUIRED_FIELDS))
 check(pid+' review date is real completion date',bool(r['reviewed_at']) and r['reviewed_at'][:10] in ('2026-10-19','2026-10-20'))
 for s in sources.values():
  path=ROOT/s['local_path']
  check(s['id']+' official source/hash',urlparse(s['source_url']).hostname in ('cdn.daisomall.co.kr','www.daisomall.co.kr') and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256'])
  sr=c.execute('SELECT product_id,source_url,local_path,sha256,observed_on,published_on FROM sources WHERE id=?',(s['id'],)).fetchone()
  check(s['id']+' source provenance serialized',tuple(sr)==(pid,s['source_url'],s['local_path'],s['sha256'],s['observed_on'],s.get('published_on')))
 for key,f in p['fields'].items():
  check(pid+'/'+key+' missingness explained',f['value'] is not None or bool(f['missing_reason']))
  if f.get('source_id'):check(pid+'/'+key+' source ownership',f['source_id'] in sources)
  sf=c.execute('SELECT value_json,status,missing_reason,raw_text,source_id FROM product_fields WHERE product_id=? AND field_name=?',(pid,key)).fetchone()
  check(pid+'/'+key+' field serialization',(json.loads(sf[0]) if sf[0] is not None else None,sf[1],sf[2],sf[3],sf[4])==(f['value'],f['status'],f['missing_reason'],f.get('raw_text'),f.get('source_id')))
  if f.get('reviewed_at'):check(pid+'/'+key+' review timestamp serialized',c.execute('SELECT reviewed_at FROM field_review_dates WHERE product_id=? AND field_name=?',(pid,key)).fetchone()[0]==f['reviewed_at'])
 for n in p['nutrient_candidates']+p['reviewed_nutrients']:
  check('nutrient source ownership',n['source_id'] in sources and all(x in sources for x in n.get('duplicate_source_ids',[])))
  check('quantity unit operator preserved',bool(n['unit_raw']) and n['amount']==qty(n['amount_raw']) and n['operator'] in ('=','<','<=','>='))
  check('basis or explicit missing reason',bool(n['basis_raw'] or n['basis_missing_reason']))
  if n['status']=='direct_visual':check('direct nutrient has basis',bool(n['basis_raw']))
 cols=('source_id','name_raw','amount','amount_raw','unit_raw','basis_raw','basis_status','basis_missing_reason','nrv_percent_raw','raw_text','status','classification','reason','operator')
 actual=Counter(rows('SELECT '+','.join(cols)+' FROM nutrient_amounts WHERE product_id=?',(pid,)))
 check(pid+' every nutrient row serialized',actual==Counter(tuple(n.get(k) for k in cols) for n in p['nutrient_candidates']+p['reviewed_nutrients']))
 for i in p['ingredient_candidates']+p['reviewed_ingredients']:
  check('ingredient evidence/missing quantity',i['source_id'] in sources and (i['amount'] is not None or bool(i['amount_missing_reason'])))
 actual=Counter(rows('SELECT source_id,name_raw,ordinal,amount,unit,raw_text,status FROM product_ingredients pi JOIN ingredients i ON i.id=pi.ingredient_id WHERE product_id=?',(pid,)))
 check(pid+' every ingredient row serialized',actual==Counter((i['source_id'],i['name_raw'],i['ordinal'],i['amount'],i['unit'],i['block_raw'],i['status']) for i in p['ingredient_candidates']+p['reviewed_ingredients']))
check('recommendation remains deferred',not rows('SELECT 1 FROM products WHERE recommendation_eligible<>0') and all(not p['recommendation_eligible'] for p in ps))
check('all products inspected, 87 complete and one specific hold',Counter(p['data_review_status'] for p in ps)=={'verified':87,'on_hold':1} and next(p for p in ps if p['data_review_status']=='on_hold')['product_number']=='600651654')
check('direct nutrient view count',count('reviewed_nutrients')==sum(len(p['reviewed_nutrients']) for p in ps))
check('no duplicate direct nutrients',not rows('SELECT product_id,name_raw,unit_raw,basis_raw,count(*) FROM reviewed_nutrients GROUP BY 1,2,3,4 HAVING count(*)>1'))
check('complete-product view excludes held facts',not rows("SELECT * FROM verified_product_nutrients WHERE product_id='600651654'") and count('verified_product_nutrients')==908)
check('no unreviewed candidates leak into confirmed view',not rows("SELECT * FROM reviewed_nutrients WHERE status<>'direct_visual'"))
check('upper bounds retained',c.execute("SELECT count(*) FROM reviewed_nutrients WHERE product_id='994953534' AND operator='<'").fetchone()[0]==3)
def nutrient(pid,name):return c.execute('SELECT amount,unit_raw,basis_raw,amount_raw FROM reviewed_nutrients WHERE product_id=? AND name_raw=?',(pid,name)).fetchone()
check('calcium 700 mg daily four tablets',tuple(nutrient('600000147','칼슘')[:2])==(700.0,'mg') and '4정' in nutrient('600000147','칼슘')[2])
check('B12 decimal regression',nutrient('600000129','비타민B12')[0]==2.4)
check('total pack biotin not daily conversion',nutrient('610911100','비오틴')[0]==70000 and '총 내용량' in nutrient('610911100','비오틴')[2])
check('retinol total 12 pack basis',nutrient('994953530','비타민A')[0]==12000 and '12포' in nutrient('994953530','비타민A')[2])
check('Withanoside and mixed tablet basis',nutrient('032306284','Withanoside IV')[0]==5.664 and '650' in nutrient('032306284','Withanoside IV')[2])
check('myricetin/luteolin decimals',nutrient('976195543','미리세틴')[0]==6.64 and nutrient('976195543','루테올린')[0]==3.76)
check('Korean count preserved without unit conversion',nutrient('032306212','프로바이오틱스 수')[3]=='50억' and nutrient('032306212','프로바이오틱스 수')[0]==5e9)
check('FOS two pack daily basis',nutrient('600651647','프락토올리고당')[0]==3 and '2포' in nutrient('600651647','프락토올리고당')[2])
held=next(p for p in ps if p['product_number']=='600651654')
check('held CFU absent from quantitative facts',not rows("SELECT * FROM reviewed_nutrients WHERE product_id='600651654' AND unit_raw='CFU'") and bool(held['label_review']['unquantified_nutrients']) and bool(held['label_review']['blocking_issues']))
check('film absence distinguished from zero',next(p for p in ps if p['product_number']=='610911097')['fields']['nutrition']['status']=='not_displayed_in_observed_label')
for fn,key in [('nutrient-candidates.csv','nutrient_candidates'),('nutrients-reviewed.csv','reviewed_nutrients')]:
 with (DATA/fn).open(encoding='utf-8-sig',newline='') as f:check(fn+' row count',len(list(csv.DictReader(f)))==sum(len(p[key]) for p in ps))
check('correction log SQLite equality',count('correction_history')==len(json.loads((DATA/'label-review-corrections.json').read_text())['changes']))
# Audit artifacts must agree with the current dataset rather than stale collection states.
collection={p['product_number']:p for p in json.loads((DATA/'collection-ledger.json').read_text())['products']}
for p in ps:
 pid=p['product_number'];r=p['label_review']
 check(pid+' collection/review state synchronized',collection[pid]['data_review_status']==p['data_review_status']==r['review_status'])
 for ev in r['evidence']:
  check(pid+' visual evidence owns source',ev['source_sha256'] in {s['sha256'] for s in p['sources']})
  for crop in ev['crops']:
   check(pid+' evidence crop exists with bounded coordinates',(ROOT/crop['path']).is_file() and crop['x']>=0 and crop['y']>=0 and crop['width']>0 and crop['height']>0)
# Negative controls for the completion gate: an unresolved field or missing decision cannot pass.
import copy
fixture=copy.deepcopy(ps[0]);fixture['fields']['cautions']['status']='unverified'
check('unresolved required field cannot pass',review_status(fixture)=='partial')
fixture=copy.deepcopy(ps[0]);fixture['label_review']['completeness_confirmed']=False
check('no implicit completion from image/OCR availability',review_status(fixture)=='partial')
fixture=copy.deepcopy(ps[0]);fixture['label_review']['blocking_issues']=['unresolved quantity']
check('blocking issue overrides completed fields',review_status(fixture)=='on_hold')
report={'passed':True,'validation_scope':'offline integrity/provenance/serialization/regressions; same-agent visual decisions, no independent second reviewer','checks_passed':len(checks),'summary':d['summary'],'table_counts':expected,'nutrient_status_counts':dict(rows('SELECT status,count(*) FROM nutrient_amounts GROUP BY status')),'units_preserved':[r[0] for r in c.execute('SELECT DISTINCT unit_raw FROM nutrient_amounts ORDER BY unit_raw')],'held_product_numbers':['600651654']}
(DATA/'database-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
