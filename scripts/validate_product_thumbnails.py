"""Check official image identity, bytes, DB serialization and the public export."""
import hashlib
import json
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/products'
manifest = json.loads((DATA / 'product-thumbnails.json').read_text())
normalized = json.loads((DATA / 'products-normalized.json').read_text())
public = json.loads((ROOT / 'frontend/src/data/products.json').read_text())
catalog = json.loads((DATA / 'catalog-discovery.json').read_text())['products']
images = {p['product_number']: p for p in manifest['products']}
facts = {p['product_number']: p for p in normalized['products']}
connection = sqlite3.connect(f'file:{DATA / "products.sqlite3"}?mode=ro', uri=True)
assert set(images) == {p['product_number'] for p in catalog}
assert len(images) == len(manifest['products']) == 88
assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert not connection.execute('PRAGMA foreign_key_check').fetchall()
assert connection.execute('SELECT count(*) FROM product_thumbnails').fetchone()[0] == 88
digests = set()
for sku, image in images.items():
    assert facts[sku]['thumbnail'] == image
    row = connection.execute('SELECT status,source_url,page_url,local_path,sha256,width,height,observed_on,missing_reason,image_json FROM product_thumbnails WHERE product_id=?', (sku,)).fetchone()
    assert json.loads(row[-1]) == image
    assert row[:-1] == tuple(image.get(k) for k in ('status','source_url','page_url','local_path','sha256','width','height','observed_on','missing_reason'))
    if image['status'] != 'available':
        assert image['missing_reason']
        continue
    url = urlparse(image['source_url'])
    assert url.scheme == 'https' and url.hostname == 'cdn.daisomall.co.kr'
    assert '/thumb/' in url.path and sku in Path(url.path).name
    detail = urlparse(image['detail_url'])
    assert detail.hostname == 'www.daisomall.co.kr' and parse_qs(detail.query)['pdNo'] == [sku]
    assert urlparse(image['page_url']).hostname == 'www.daisomall.co.kr'
    path = ROOT / image['local_path']
    assert path.is_relative_to(DATA / 'thumbnails') and path.stem == sku
    body = path.read_bytes()
    assert body.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'RIFF'))
    assert hashlib.sha256(body).hexdigest() == image['sha256']
    assert len(body) == image['byte_size'] and min(image['width'], image['height']) >= 100
    # Catch accidentally attaching one placeholder image to multiple products.
    assert image['sha256'] not in digests
    digests.add(image['sha256'])
for product in public:
    sku = product['id']
    assert facts[sku]['data_review_status'] == 'verified'
    image = images[sku]
    if image['status'] == 'available':
        exported = ROOT / 'frontend/public' / product['thumbnail']['path']
        assert exported.stem == sku and hashlib.sha256(exported.read_bytes()).hexdigest() == image['sha256']
        assert product['thumbnail']['sourceUrl'] == image['source_url']
        assert product['thumbnail']['observedAt'] == image['observed_on']
    else:
        assert product['thumbnail']['path'] is None
assert len(public) == 87 and '600651654' not in {p['id'] for p in public}
assert not any(p.stem == '600651654' for p in (ROOT / 'frontend/public/product-images').iterdir())
assert all(p['recommendation_eligible'] is False for p in normalized['products'])
report = {'passed': True, 'catalog_products': len(images),
          'available': sum(p['status'] == 'available' for p in images.values()),
          'public_products': len(public), 'unique_images': len(digests),
          'scope': 'official DOM SKU linkage, image bytes/hash, database and public export; no change to label or recommendation gates'}
(DATA / 'thumbnail-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
