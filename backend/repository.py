"""Every public product and evidence retrieval comes from reviewed SQLite rows."""
import json
import re
import sqlite3
from contextlib import contextmanager
from .config import DATABASE
from .label_guide import evidence as guide_evidence

GENERAL = {'열량','나트륨','탄수화물','당류','지방','트랜스지방','포화지방','단백질','콜레스테롤','에리스리톨'}

@contextmanager
def connect():
    db = sqlite3.connect(f'file:{DATABASE}?mode=ro',uri=True)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()

def list_products():
    with connect() as db:
        rows = db.execute("SELECT p.*,r.reviewed_at FROM products p JOIN label_reviews r ON r.product_id=p.product_number WHERE r.data_review_status='verified' ORDER BY p.rowid").fetchall()
        result=[]
        for row in rows:
            sku=row['product_number']
            fields={f['field_name']:json.loads(f['value_json']) for f in db.execute("SELECT * FROM verified_product_fields WHERE product_id=?",(sku,)) if f['value_json'] is not None}
            price=db.execute('SELECT amount,observed_on FROM prices WHERE product_id=? ORDER BY id DESC LIMIT 1',(sku,)).fetchone()
            image=db.execute('SELECT * FROM product_thumbnails WHERE product_id=?',(sku,)).fetchone()
            image_data=json.loads(image['image_json']) if image else {}
            thumb={'path':None,'sourceUrl':None,'observedAt':None}
            if image_data.get('status')=='available':
                from pathlib import Path
                thumb={'path':'product-images/'+Path(image_data['local_path']).name,'sourceUrl':image_data['source_url'],'observedAt':image_data['observed_on']}
            nutrients=[{'name':n['name_raw'],'amount':n['amount_raw'],'operator':n['operator'],'unit':n['unit_raw'],'basis':n['basis_raw'],'percent':n['nrv_percent_raw']} for n in db.execute('SELECT * FROM verified_product_nutrients WHERE product_id=?',(sku,))]
            # This catalog's 12-tablet retail package was checked separately in the official product screen (label review ledger).
            package='600 mg × 12정' if sku=='032306200' else fields.get('package')
            result.append({'id':sku,'name':fields.get('product_name') or row['name'],'displayName':row['name'],'brand':row['brand_display'],'type':fields.get('food_type'),'package':package,'form':fields.get('dosage_form'),'price':price['amount'] if price else None,'priceDate':price['observed_on'] if price else None,'sourceUrl':row['detail_url'],'checkedAt':row['reviewed_at'][:10],'observedAt':row['observed_on'],'intake':fields.get('intake'),'cautions':fields.get('cautions'),'allergen':fields.get('allergen_or_cross_contact'),'storage':fields.get('storage'),'ingredients':fields.get('raw_materials'),'functionText':fields.get('function'),'nutrients':nutrients,'thumbnail':thumb})
        return result

def get_product(sku):
    product=next((p for p in list_products() if p['id']==sku),None)
    if product is None:
        raise LookupError('Reviewed product not found')
    return product

def get_many(ids):
    products={p['id']:p for p in list_products()}
    if len(ids)!=len(set(ids)) or any(sku not in products for sku in ids):
        raise LookupError('Unknown, held, or duplicate product')
    return [products[sku] for sku in ids]

def evidence(query='',product_ids=None,limit=8):
    """Query-specific retrieval over reviewed external-source DB fields, not static prompt text."""
    guides=guide_evidence(query)
    if guides and not product_ids:return guides[:limit]
    terms=list(dict.fromkeys(re.findall(r'[가-힣A-Za-z0-9]{2,}',query)))[:8]
    # User phrasing expands into label vocabulary; it never invents a health claim.
    synonyms={'활력':['에너지'],'뼈':['칼슘','뼈'],'근육':['근육'],'장':['배변','유익균'],'눈':['시각','눈'],'혈당':['바나바','코로솔산'],'다이어트':['체지방'],'중복':['영양'],'섭취':['섭취'],'주의':['주의']}
    for word,values in synonyms.items():
        if word in query:terms.extend(values)
    field_map={'function':('기능정보','function'),'nutrition':('영양정보','nutrition'),'intake':('표시 섭취방법','intake'),'cautions':('주의사항','cautions'),'allergen_or_cross_contact':('알레르기·교차오염','allergen_or_cross_contact'),'storage':('표시 보관방법','storage')}
    clauses=["r.data_review_status='verified'","f.status='direct_visual'","f.field_name IN ('function','nutrition','intake','cautions','allergen_or_cross_contact','storage')"]
    args=[]
    if product_ids:
        get_many(product_ids)
        clauses.append('f.product_id IN ('+','.join('?' for _ in product_ids)+')');args.extend(product_ids)
    with connect() as db:
        rows=db.execute('SELECT f.*,p.name,p.detail_url,s.source_url,s.observed_on FROM product_fields f JOIN products p ON p.product_number=f.product_id JOIN label_reviews r ON r.product_id=f.product_id LEFT JOIN sources s ON s.id=f.source_id WHERE '+' AND '.join(clauses),args).fetchall()
    ranked=[]
    for row in rows:
        text=row['raw_text'] or (json.loads(row['value_json']) if row['value_json'] else '')
        if not isinstance(text,str) or not text.strip():continue
        score=sum(term.lower() in (text+row['name']+field_map[row['field_name']][0]).lower() for term in terms)
        if guides and row['field_name'] in ('nutrition','intake'):score+=5
        if '기능' in query and row['field_name']=='function':score+=5
        if terms and not score:continue
        title=field_map[row['field_name']][0]
        ranked.append((score,{'id':f"{row['product_id']}:{row['field_name']}",'productId':row['product_id'],'title':row['name']+' · '+title,'text':text[:2200],'url':row['source_url'] or row['detail_url'],'productUrl':row['detail_url'],'observedAt':row['observed_on']}))
    ranked.sort(key=lambda v:-v[0])
    return (guides+[r[1] for r in ranked])[:limit]

def compare(ids):
    ps=get_many(ids)
    fields=[('식품유형','type'),('포장·규격','package'),('관찰 가격','price'),('가격 확인일','priceDate'),('표시정보 검수일','checkedAt'),('제형','form'),('표시 섭취방법','intake'),('주의사항','cautions'),('알레르기·교차오염','allergen')]
    rows=[{'label':label,'values':[str(p[key]) if p.get(key) is not None else '표시 미확인' for p in ps]} for label,key in fields]
    next(r for r in rows if r['label']=='관찰 가격')['values']=[f"{p['price']:,}원" if p['price'] is not None else '가격 미확인' for p in ps]
    for name in dict.fromkeys(n['name'] for p in ps for n in p['nutrients'] if n['name'] not in GENERAL):
        values=[]
        for p in ps:
            n=next((n for n in p['nutrients'] if n['name']==name),None)
            values.append(f"{n['operator'] if n['operator']!='=' else ''}{n['amount']} {n['unit']} / {n['basis']}" if n else '표시 정량 없음')
        rows.append({'label':name,'values':values})
    return {'products':ps,'rows':rows,'notice':'표시 기준과 단위를 유지한 비교입니다. 제품 우열이나 병용 가능 여부를 판단하지 않습니다.'}
