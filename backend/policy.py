"""Conservative product-selection policy; never diagnoses a deficiency or prescribes a dose."""
import re
from decimal import Decimal, InvalidOperation
from .config import POLICY_VERSION
from . import repository as repo

GOALS={'일상의 활력':('에너지',),'뼈·근육 건강':('뼈','근육'),'장 건강':('배변','유익균','장 건강'),'눈 건강':('눈 건강','시각','황반')}
ALIASES={'셀레늄':'셀렌','프로바이오틱스수':'프로바이오틱스','EPA및DHA의합':'EPA와DHA의합','EPA및DHA합':'EPA와DHA의합'}

def canonical(name):
    name=re.sub(r'\s+','',name)
    return ALIASES.get(name,name)

def functional(p):
    return [n for n in p['nutrients'] if n['name'] not in repo.GENERAL]

def quantity(n):
    """Only exact, explicit daily label amounts. No IU/RAE/DFE/NE conversions."""
    if n['operator']!='=' or not re.search(r'1\s*일',n['basis'] or ''):
        return None
    unit=re.sub(r'\s+','',n['unit']).replace('µ','μ').replace('ug','μg')
    try:
        raw=n['amount'].replace(',','')
        amount=Decimal(raw[:-1])*Decimal(100000000) if raw.endswith('억') else Decimal(raw)
    except (InvalidOperation,AttributeError):
        return None
    if unit in ('g','mg','μg'):
        return amount*{'g':Decimal(1000),'mg':Decimal(1),'μg':Decimal('.001')}[unit],'mg'
    return amount,unit

def overlap(ids):
    ps=repo.get_many(ids)
    groups={}
    missing=[]
    for p in ps:
        if not functional(p):missing.append(p['id'])
        per_product={}
        for n in functional(p):
            per_product.setdefault(canonical(n['name']),[]).append(n)
        for name,ns in per_product.items():
            n=ns[0]
            groups.setdefault(name,[]).append({'productId':p['id'],'productName':p['name'],**n,'_quantity':quantity(n) if len(ns)==1 else None})
    duplicates=[]
    for name,items in groups.items():
        if len(items)<2:continue
        amounts=[i['_quantity'] for i in items]
        calculable=all(q is not None for q in amounts) and len({q[1] for q in amounts if q})==1
        total={'amount':format(sum(q[0] for q in amounts),'f'),'unit':amounts[0][1]} if calculable else None
        duplicates.append({'name':name,'items':[{k:v for k,v in i.items() if k!='_quantity'} for i in items],'dailyTotal':total,'totalStatus':'explicit_daily_labels' if calculable else 'different_or_unknown_basis_unit_operator'})
    return {'status':'incomplete' if missing else 'checked_registered_products','duplicates':duplicates,'missingProductIds':missing,'notice':'등록한 제품의 표시 성분 중복만 확인합니다. 식사·의약품·미등록 제품은 포함하지 않으며, 중복이 없다는 결과가 병용 안전성을 뜻하지 않습니다.'}

def exclusion(p):
    if '건강기능식품' not in (p['type'] or ''):return '일반식품은 정보 탐색만 제공'
    if re.search(r'키즈|어린이|뽀로로|Kids|철분|임산|여성|남성|월경|전립선|다이어트|혈당|혈압|수면|슬립|갱년기',p['displayName'],re.I):return '초기 성인 일반 선택 정책의 지원 범위 밖'
    if re.search(r'혈당|혈압|질\s*건강|전립선|체지방|간\s*건강|수면|월경|여성',p['functionText'] or ''):return '추가 개인 조건이 필요한 특화 기능정보'
    ns=functional(p)
    if not p['functionText'] or not p['intake'] or not p['cautions'] or not ns:return '추천 필수 표시 근거 부족'
    if any(not re.search(r'1\s*일',n['basis'] or '') for n in ns):return '하루 기준 정량을 확정하지 못함'
    for n in ns:
        percent=n.get('percent')
        if percent:
            try:
                if Decimal(str(percent).replace(',','').replace('%',''))>200:return '초기 정책은 표시 기준치 200% 초과 제품을 자동 추천에서 제외'
            except InvalidOperation:return '표시 기준치 비율 확인 필요'
    return None

def recommend(survey):
    """Return reproducible reasons and gates, independent of model availability."""
    from collections import Counter
    ps=repo.list_products()
    repo.get_many(survey.productIds)
    base={'policyVersion':POLICY_VERSION,'products':[],'reasons':{},'evidence':[],
          'notices':['제품 선택 참고용이며 개인별 영양 부족이나 치료 효과를 판단하지 않습니다.','식습관 답변만으로 특정 영양소가 부족하다고 추정하지 않습니다.'],
          'overlap':overlap(survey.productIds) if survey.productIds else {'status':'not_needed' if survey.existing=='없어요' else 'incomplete','duplicates':[]},
          'excludedCounts':{}}
    if any(c not in ('해당 없어요','잘 모르겠어요') for c in survey.cautions):
        return {**base,'status':'restricted','message':'의약품 복용·치료, 임신·수유 또는 알레르기 확인이 필요한 경우 개인 추천을 제공하지 않습니다. 제품 표시와 전문가 확인을 먼저 진행해 주세요.'}
    if '잘 모르겠어요' in survey.cautions:
        return {**base,'status':'insufficient','message':'주의조건을 확인한 뒤 추천을 진행할 수 있어요. 모르는 상태를 해당 없음으로 처리하지 않습니다.','nextStep':4}
    if survey.existing in ('잘 모르겠어요','목록에 없어요'):
        return {**base,'status':'insufficient','message':'현재 먹는 제품을 확인할 수 없어 중복 검사를 완료하지 못했어요. 제품을 확인하거나 전체 상품 정보를 둘러보세요.','nextStep':3}
    if base['overlap']['status']=='incomplete':
        return {**base,'status':'insufficient','message':'기존 제품의 표시 정량이 부족해 중복 검사를 완료하지 못했어요.','nextStep':3}
    if survey.interests==['잘 모르겠어요']:
        return {**base,'status':'insufficient','message':'먼저 관심 분야를 정해 주세요. 다양한 제품을 보고 싶다면 ‘다양한 성분 보기’를 선택할 수 있어요.','nextStep':1}
    existing=[p for p in ps if p['id'] in survey.productIds]
    existing_names={canonical(n['name']) for p in existing for n in functional(p)}
    ranked=[];excluded=Counter()
    for p in ps:
        reason=exclusion(p)
        if reason:excluded[reason]+=1;continue
        if p['id'] in survey.productIds:excluded['이미 선택한 제품']+=1;continue
        if existing_names.intersection(canonical(n['name']) for n in functional(p)):
            excluded['기존 제품과 표시 성분 중복']+=1;continue
        budget={'3,000원 이하':3000,'5,000원 이하':5000}.get(survey.budget)
        if budget is not None and (p['price'] is None or p['price']>budget):excluded['예산 조건']+=1;continue
        form_patterns={'정제·캡슐':r'정제|캡슐','분말·포':r'분말|과립','필름·액상':r'필름|액상|액체'}
        if survey.form in form_patterns and not re.search(form_patterns[survey.form],p['form'] or ''):excluded['제형 조건']+=1;continue
        matched=[g for g in survey.interests if g in GOALS and any(t in p['functionText'] for t in GOALS[g])]
        if '다양한 성분 보기' in survey.interests and len(functional(p))>=3:matched.append('다양한 성분 보기')
        if not matched:excluded['관심 분야와 연결되는 표시 근거 없음']+=1;continue
        score=len(matched)
        reasons=[f"‘{g}’ 관심과 연결되는 기능정보가 제품 표시에 있습니다." for g in matched]
        if budget:reasons.append(f"관찰 가격이 선택한 예산({survey.budget})에 들어갑니다.")
        if survey.form in form_patterns:reasons.append('선호한 제형과 일치합니다.')
        ranked.append((score,p,reasons))
    ranked.sort(key=lambda x:(-x[0],x[1]['price'] if x[1]['price'] is not None else float('inf'),x[1]['id']))
    selected=ranked[:3]
    base.update(status='ok' if selected else 'empty',message='입력 조건과 표시 근거에 맞는 후보입니다.' if selected else '현재 정책과 입력 조건을 모두 충족하는 후보가 없어요. 예산·제형을 수정하거나 전체 제품을 살펴보세요.',products=[p for _,p,_ in selected],reasons={p['id']:reasons for _,p,reasons in selected},excludedCounts=dict(excluded))
    for _,p,_ in selected:
        base['evidence']+=repo.evidence('기능', [p['id']],limit=1)
    return base
