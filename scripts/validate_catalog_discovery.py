"""Offline integrity checks; does not prove current labels or stock."""
import csv,json
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse,parse_qs
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data/products/catalog-discovery.json').read_text(encoding='utf-8'))
rows=d['products'];s=d['summary'];ids=[r['product_number'] for r in rows]
assert len(ids)==len(set(ids))==s['saved_single_package_skus']
assert len({r['family_key'] for r in rows})==s['inferred_families']
assert dict(Counter(r['displayed_brand_or_company'] for r in rows))==s['brand_company_groups']
assert s['category_priced_card_occurrences']-s['category_distinct_pdNo_observed']==s['category_repeated_card_occurrences']
assert s['category_distinct_pdNo_observed']-len(rows)==s['category_unique_not_selected_for_saved_sample']
for row in rows+d['excluded_bundle_examples']:
 u=urlparse(row['detail_url'])
 assert u.scheme=='https' and u.hostname=='www.daisomall.co.kr'
 assert parse_qs(u.query)['pdNo']==[row['product_number']]
 assert row['price_krw']>0 and row['observed_on']==d['observed_on']
for row in rows:
 assert row['recommendation_eligible'] is False and row['validation_status']=='discovery_only'
 assert row['is_bulk_bundle'] is False
 assert row['food_type'] is None or row['food_type_source_url']
 assert row['manufacturer'] is None or row.get('manufacturer_source_url')
 assert row['stock_status'] is None
for row in d['excluded_bundle_examples']:
 assert row['single_package_product_number'] in ids
 assert not row['counted_as_new_product_family']
with (root/'data/products/catalog-discovery.csv').open(encoding='utf-8-sig',newline='') as f:
 csvrows=list(csv.DictReader(f))
assert [r['product_number'] for r in csvrows]==ids
assert all(int(c['price_krw'])==j['price_krw'] and c['display_name']==j['display_name'] for c,j in zip(csvrows,rows))
print(f"PASS: {len(rows)} single SKUs, {s['inferred_families']} inferred families, {len(s['brand_company_groups'])} groups, {len(d['excluded_bundle_examples'])} excluded bundle examples")
