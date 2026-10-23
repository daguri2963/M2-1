"""Versioned product-purpose annotations, grounded in existing reviewed label sections."""
import json
import re
from .config import ROOT

CATALOG=json.loads((ROOT/'data/recommendation/classification-v2.json').read_text())
VERSION=CATALOG['version']
GOAL_DESCRIPTIONS={
    '일상의 활력':'에너지 대사에 관련된 성분과 제품 표시를 알아봐요.',
    '뼈·근육 건강':'뼈 중심과 정상적인 근육 기능 중심 제품을 구분해요.',
    '장 건강':'유산균과 프리바이오틱스 등의 장 기능 표시를 비교해요.',
    '눈 건강':'눈 관련 기능이 표시된 목적 중심 제품을 살펴봐요.',
    '혈당 관리':'식후 혈당 관련 기능 표시를 살펴봐요. 질환 치료 안내는 아니에요.',
    '다이어트':'체지방 감소 기능 표시를 살펴봐요. 감량을 보장하지 않아요.',
}
SPECIALTIES={'혈당 관리','다이어트'}

def normalized(text):return re.sub(r'\s+','',text or '')

def entry_for(product):
    entry=CATALOG['entries'].get(product['id'])
    if not entry:return None
    sections={normalized(ingredient):normalized(claim) for ingredient,claim in re.findall(r'\[([^\]]+)\]\s*([^\[]*)',product['functionText'] or '')}
    # Stale or misattributed annotations cannot silently classify a changed label.
    for match in entry['matches']:
        if (match['goal'] not in GOAL_DESCRIPTIONS or match['tier'] not in ('direct','related')
                or match['evidenceId']!=product['id']+':function'
                or not normalized(match['claim'])
                or sections.get(normalized(match['ingredient']))!=normalized(match['claim'])):
            return None
    return entry

def matches_for(product,interests,tier='direct'):
    entry=entry_for(product)
    return [dict(m) for m in entry['matches'] if m['goal'] in interests and m['tier']==tier] if entry else []

def family_key(product):
    entry=entry_for(product)
    # A manually reviewed family still needs matching daily labels/form/intake.
    nutrients=tuple(sorted((normalized(n['name']),str(n['amount']),n['operator'],normalized(n['unit']),normalized(n['basis'])) for n in product['nutrients']))
    return (entry['family'] if entry else product['id'],product['brand'],product['form'],normalized(product['intake']),nutrients)
