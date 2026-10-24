"""Verified label numbers for a product overview, separate from generated prose."""
import re
from . import repository as repo


def overview_requested(question):
    # Storage, timing and cautions keep their own focused answers.
    if re.search(r'보관|섭취\s*시간|식사|주의|알레르기|상호작용', question):
        return False
    return bool(re.search(r'주요\s*성분|주\s*성분|성분.{0,20}(?:역할|기능|함량|기준치)|영양\s*정보', question))


def nutrition_summary(product):
    nutrients = []
    for nutrient in product['nutrients']:
        if nutrient['name'] in repo.GENERAL:
            continue
        # Preserve the label's basis, operator and units; never derive a new %.
        percent = nutrient.get('percent')
        if percent is not None:
            percent = str(percent).strip().removesuffix('%').strip()
            if not re.fullmatch(r'\d[\d,]*(?:\.\d+)?', percent):
                percent = None
        nutrients.append({**nutrient, 'percent': percent})
    return {
        'productId': product['id'], 'productName': product['name'],
        'nutrients': nutrients,
        'notice': '비율은 제품에 표시된 영양성분 기준치 대비 값이에요. 개인의 하루 필요량이나 흡수율을 뜻하지 않아요.',
        'label': {key: product.get(key) for key in ('functionText', 'intake', 'cautions', 'allergen')},
        'sourceUrl': product['sourceUrl'], 'checkedAt': product['checkedAt'],
    }
