"""Conservative product-selection policy; never diagnoses a deficiency or prescribes a dose."""
import re
from decimal import Decimal, InvalidOperation
from .config import POLICY_VERSION
from . import repository as repo
from . import classification as catalog

GOALS=tuple(catalog.GOAL_DESCRIPTIONS)
ALIASES={'셀레늄':'셀렌','프로바이오틱스수':'프로바이오틱스','EPA및DHA의합':'EPA와DHA의합','EPA및DHA합':'EPA와DHA의합'}

def canonical(name):
    name=re.sub(r'\s+','',name)
    return ALIASES.get(name,name)

def functional(p):
    return [n for n in p['nutrients'] if n['name'] not in repo.GENERAL]

def quantity(n):
    """Only exact, explicit daily label amounts. No IU/RAE/DFE/NE conversions."""
    if n['operator']!='=' or not re.search(r'1\s*일',n['basis'] or '') or not isinstance(n['unit'],str) or not n['unit'].strip():
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

def exclusion(p,interests=()):
    if '건강기능식품' not in (p['type'] or ''):return '일반식품은 정보 탐색만 제공'
    if re.search(r'키즈|어린이|뽀로로|Kids|철분|임산|여성|남성|월경|전립선|혈압|수면|슬립|갱년기',p['displayName'],re.I):return '성인 제품 탐색 정책의 지원 범위 밖'
    if re.search(r'혈압|질\s*건강|전립선|간\s*건강|수면|월경|여성',p['functionText'] or ''):return '미지원 특화 기능정보'
    entry=catalog.entry_for(p)
    if not entry:return '목적별 분류 근거 미확인'
    if entry.get('holdReason'):return entry['holdReason']
    if not set(entry['specialties'])<=set(interests):return '선택하지 않은 특화 기능이 포함된 제품'
    if entry['specialties'] and entry.get('scopeReviewVersion')!=POLICY_VERSION:return '특화 범주 표시·주의조건 검토 미완료'
    ns=functional(p)
    if not p['functionText'] or not p['intake'] or not p['cautions'] or not ns:return '추천 필수 표시 근거 부족'
    if any(quantity(n) is None for n in ns):return '하루 기준 정량을 확정하지 못함'
    for n in ns:
        percent=n.get('percent')
        if percent:
            try:
                if Decimal(str(percent).replace(',','').replace('%',''))>200:return '초기 정책은 표시 기준치 200% 초과 제품을 자동 추천에서 제외'
            except InvalidOperation:return '표시 기준치 비율 확인 필요'
    return None

FORM_PATTERNS={'정제·캡슐':r'정제|캡슐','구미·츄어블':r'구미|츄어블','분말·포':r'분말|과립','필름·액상':r'필름|액상|액체'}

def preference_exclusion(p,survey):
    budget={'3,000원 이하':3000,'5,000원 이하':5000}.get(survey.budget)
    if budget is not None and (p['price'] is None or p['price']>budget):return '예산 조건'
    form=p['form'] or ''
    if survey.form=='정제·캡슐' and re.search(r'구미|츄어블',form):return '제형 조건'
    if survey.form in FORM_PATTERNS and not re.search(FORM_PATTERNS[survey.form],form):return '제형 조건'
    return None

def _price_key(candidate):
    p=candidate['product']
    return (p['price'] if p['price'] is not None else float('inf'),p['id'])

def _representatives(candidates):
    families={}
    for candidate in sorted(candidates,key=_price_key):
        families.setdefault(catalog.family_key(candidate['product']),candidate)
    return list(families.values())

def _choose(candidates):
    remaining=_representatives(candidates);chosen=[];covered=set();subgoals=set()
    while remaining and len(chosen)<3:
        def key(c):
            goals={m['goal'] for m in c['matches']}
            groups={(m['goal'],m['subgoal']) for m in c['matches']}
            return (-len(goals-covered),-len(groups-subgoals),-len(goals),*_price_key(c))
        winner=min(remaining,key=key);remaining.remove(winner);chosen.append(winner)
        covered.update(m['goal'] for m in winner['matches'])
        subgoals.update((m['goal'],m['subgoal']) for m in winner['matches'])
    return chosen

def recommend(survey):
    """Return reproducible reasons and gates, independent of model availability."""
    from collections import Counter
    ps=repo.list_products()
    repo.get_many(survey.productIds)
    base={'policyVersion':POLICY_VERSION,'products':[],'reasons':{},'evidence':[],
          'notices':['제품 선택 참고용이며 개인별 영양 부족이나 치료 효과를 판단하지 않습니다.','식습관 답변만으로 특정 영양소가 부족하다고 추정하지 않습니다.'],
          'overlap':overlap(survey.productIds) if survey.productIds else {'status':'not_needed' if survey.existing=='없어요' else 'incomplete','duplicates':[]},
          'excludedCounts':{},'purposeMatches':{},'missingInterests':[],
          'relatedProducts':[],'guidance':[],'classificationVersion':catalog.VERSION}
    if any(c not in ('해당 없어요','잘 모르겠어요') for c in survey.cautions):
        return {**base,'status':'restricted','message':'질환 진단·치료·의약품 복용, 임신·수유 또는 알레르기 확인이 필요한 경우 개인 추천을 제공하지 않습니다. 제품 표시와 전문가 확인을 먼저 진행해 주세요.'}
    if '잘 모르겠어요' in survey.cautions:
        return {**base,'status':'insufficient','message':'주의조건을 확인한 뒤 추천을 진행할 수 있어요. 모르는 상태를 해당 없음으로 처리하지 않습니다.','nextStep':4}
    if survey.existing in ('잘 모르겠어요','목록에 없어요'):
        return {**base,'status':'insufficient','message':'현재 먹는 제품을 확인할 수 없어 중복 검사를 완료하지 못했어요. 제품을 확인하거나 전체 상품 정보를 둘러보세요.','nextStep':3}
    if base['overlap']['status']=='incomplete':
        return {**base,'status':'insufficient','message':'기존 제품의 표시 정량이 부족해 중복 검사를 완료하지 못했어요.','nextStep':3}
    specialties=set(survey.interests)&catalog.SPECIALTIES
    if specialties and not survey.specialtyConfirmed:
        return {**base,'status':'insufficient','message':'혈당 관리·다이어트 제품의 안내 범위와 질환·의약품 관련 주의조건을 먼저 확인해 주세요.','nextStep':4}
    existing=[p for p in ps if p['id'] in survey.productIds]
    existing_specialties={goal for goal,pattern in [('혈당 관리',r'혈당'),('다이어트',r'체지방')] if any(re.search(pattern,p['functionText'] or '') for p in existing)}
    if specialties & existing_specialties:
        return {**base,'status':'restricted','message':'등록한 제품에 같은 혈당·체지방 관련 기능이 있어 새 제품의 추가 후보를 제공하지 않아요. 원료가 달라도 함께 섭취할 수 있다는 뜻은 아닙니다.'}
    existing_names={canonical(n['name']) for p in existing for n in functional(p)}
    ranked=[];related=[];excluded=Counter()
    for p in ps:
        reason=exclusion(p,survey.interests)
        if reason:excluded[reason]+=1;continue
        if p['id'] in survey.productIds:excluded['이미 선택한 제품']+=1;continue
        if existing_names.intersection(canonical(n['name']) for n in functional(p)):
            excluded['기존 제품과 표시 성분 중복']+=1;continue
        reason=preference_exclusion(p,survey)
        if reason:excluded[reason]+=1;continue
        matches=catalog.matches_for(p,survey.interests)
        if matches:ranked.append({'product':p,'matches':matches})
        else:
            matches=catalog.matches_for(p,survey.interests,'related')
            if matches:related.append({'product':p,'matches':matches})
            excluded['목적 중심 분류 근거 없음']+=1
    selected=_choose(ranked)
    covered={m['goal'] for c in selected for m in c['matches']}
    missing=[g for g in survey.interests if g not in covered]
    base.update(status='ok' if selected else 'empty',message='선택한 목적을 중심으로 표시 근거가 확인된 후보입니다.' if selected else '현재 자료와 조건에서 목적 중심 후보를 찾지 못했어요. 관련 성분 제품은 별도 정보로 살펴볼 수 있어요.',products=[c['product'] for c in selected],excludedCounts=dict(excluded),missingInterests=missing)
    if not selected:base['nextStep']=5
    if missing:base['notices'].append('목적 중심 후보를 확보하지 못한 분야: '+', '.join(missing)+'. 다른 분야의 후보가 이 목적까지 충족한다는 뜻은 아니에요.')
    base['relatedProducts']=[c['product'] for c in _representatives(related) if any(m['goal'] in missing for m in c['matches'])][:2]
    for c in selected:
        p=c['product'];matches=c['matches'];reasons=[]
        for goal in dict.fromkeys(m['goal'] for m in matches):
            ingredients=' · '.join(dict.fromkeys(m['ingredient'] for m in matches if m['goal']==goal))
            groups=' · '.join(dict.fromkeys(m['subgoal'] for m in matches if m['goal']==goal))
            reasons.append(f'‘{goal}’ 목적 중심 후보예요. {ingredients}의 검수 기능정보를 연결했어요. ({groups})')
        if survey.budget in ('3,000원 이하','5,000원 이하'):reasons.append(f'관찰 가격이 선택한 예산({survey.budget})에 들어갑니다.')
        if survey.form in FORM_PATTERNS:reasons.append('선호한 제형과 일치합니다.')
        base['reasons'][p['id']]=reasons;base['purposeMatches'][p['id']]=matches
        evidence=repo.evidence('기능',[p['id']],limit=1)
        for e in evidence:e['matchedClaims']=matches
        base['evidence']+=evidence
    return base
