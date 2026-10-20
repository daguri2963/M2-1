"""Validate pilot integrity, evidence references, units, and fail-closed eligibility.
Run: python3 scripts/validate_pilot_products.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'data/products/pilot-products.json').read_text(encoding='utf-8'))
errors = []
ids = set()

def check(condition, message):
    if not condition:
        errors.append(message)

def walk(value, path):
    if isinstance(value, dict):
        if 'value' in value:
            check(set(('raw', 'source_url', 'accessed_on', 'status', 'reason', 'method')) <= value.keys(), f'{path}: evidence fields missing')
            check(value['value'] != '', f'{path}: empty value')
            if value['value'] is None:
                check(bool(value.get('reason')), f'{path}: null requires reason')
                check(value['status'] == 'unverified', f'{path}: null marked verified')
            else:
                check(str(value.get('source_url', '')).startswith('https://'), f'{path}: missing source URL')
                check(bool(value.get('raw')), f'{path}: missing raw evidence')
            check(value['accessed_on'] == data['accessed_on'], f'{path}: inconsistent observation date')
        for key, item in value.items():
            walk(item, f'{path}.{key}')
    elif isinstance(value, list):
        for i, item in enumerate(value):
            walk(item, f'{path}[{i}]')

for p in data['products']:
    pid = p['id']
    check(pid not in ids, f'{pid}: duplicate ID')
    ids.add(pid)
    f = p['fields']
    number = f['daiso_product_number']['value']
    check(f'pdNo={number}' in f['product_name']['source_url'], f'{pid}: product URL mismatch')
    check(f['price']['value']['amount'] > 0, f'{pid}: invalid price')
    check(f['price']['value']['current_price_observed_on'] == data['accessed_on'], f'{pid}: stale price date')
    intake = f['intake']['value']
    daily = intake['times_per_day'] * intake['tablets_per_time']
    check(daily == intake['tablets_per_day'], f'{pid}: inconsistent intake')
    for c in p['functional_components']:
        a = c['amount']['value']
        check(a['amount'] > 0 and a['unit'] in {'mg', 'μg', 'mg NE', 'μg DFE'}, f'{pid}: invalid component unit/amount')
        check(a['basis'] == '1일 섭취량' and a['daily_tablets'] == daily, f'{pid}: wrong amount basis')
    e = p['eligibility']
    gates = ('daiso_sale_confirmed', 'daiso_listing_identity_confirmed', 'manufacturer_cross_source_exact_match', 'required_fields_verified')
    if e['recommendation_eligible']:
        check(all(e[g] for g in gates), f'{pid}: eligible without all gates')
        check(p['collection_status'] == 'verified', f'{pid}: partial eligible')
    if p['collection_status'] == 'partial':
        check(not e['recommendation_eligible'] and bool(e['reasons']), f'{pid}: partial must be excluded with reasons')
    check(p['review']['kind'] == 'self_review' and not p['review']['independent_second_reviewer'], f'{pid}: inaccurate review claim')
    walk(p, pid)
if errors:
    raise SystemExit('\n'.join(errors))
print(f"PASS: {len(ids)} products; {sum(p['eligibility']['recommendation_eligible'] for p in data['products'])} recommendation eligible")
