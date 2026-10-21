"""Download only official thumbnail URLs observed in the browser DOM.

Discovery is recorded separately; this script never guesses CDN URLs or uses
label/marketing images as a substitute. Existing successful downloads are reused.
"""
import concurrent.futures
import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/products'
MANIFEST = DATA / 'product-thumbnails.json'


def dimensions(path):
    # macOS ImageIO decodes the file; do not trust an extension or HTTP 200 alone.
    result = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(path)],
                            capture_output=True, text=True, check=True)
    values = dict(line.strip().split(': ', 1) for line in result.stdout.splitlines()
                  if line.strip().startswith(('pixelWidth:', 'pixelHeight:')))
    return int(values['pixelWidth']), int(values['pixelHeight'])


def main():
    discovery = json.loads((DATA / 'thumbnail-discovery.json').read_text())
    catalog = json.loads((DATA / 'catalog-discovery.json').read_text())['products']
    old = {p['product_number']: p for p in json.loads(MANIFEST.read_text())['products']} if MANIFEST.exists() else {}
    candidates = {}
    for row in discovery['candidates']:
        sku = parse_qs(urlparse(row['detail_url']).query).get('pdNo', [''])[0]
        url = row.get('lazy') or row.get('src') or ''
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'cdn.daisomall.co.kr' or '/thumb/' not in parsed.path:
            continue
        if sku not in Path(parsed.path).name:
            continue
        candidates.setdefault(sku, {**row, 'image_url': url})
    now = datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    output = DATA / 'thumbnails'
    output.mkdir(exist_ok=True)

    def collect(product):
        sku = product['product_number']
        row = candidates.get(sku)
        record = {'product_number': sku, 'catalog_name': product['display_name'],
                  'status': 'unavailable', 'missing_reason': None}
        if not row:
            record['missing_reason'] = 'No official thumbnail observed for this product number'
            return record
        url = row['image_url']
        suffix = Path(urlparse(url).path).suffix.lower()
        if suffix not in ('.png', '.jpg', '.jpeg', '.webp'):
            record['missing_reason'] = 'Unsupported image format'
            return record
        previous = old.get(sku, {})
        path = output / (sku + suffix)
        try:
            if (previous.get('status') == 'available' and previous.get('source_url') == url
                    and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == previous.get('sha256')):
                return previous
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': row['detail_url']})
            with urllib.request.urlopen(request, timeout=35) as response:
                content_type = response.headers.get_content_type()
                if not content_type.startswith('image/'):
                    raise ValueError('Response is not an image')
                body = response.read(5_000_001)
                if len(body) > 5_000_000:
                    raise ValueError('Thumbnail exceeds 5MB limit')
            path.write_bytes(body)
            width, height = dimensions(path)
            if min(width, height) < 100 or not 0.5 <= width / height <= 2:
                raise ValueError('Not a sufficiently sized product thumbnail')
            record.update(status='available', source_url=url,
                          page_url=row.get('page_url', discovery['page_url']),
                          detail_url=row['detail_url'], displayed_name=row['name'].strip(),
                          local_path=str(path.relative_to(ROOT)),
                          sha256=hashlib.sha256(body).hexdigest(), byte_size=len(body),
                          width=width, height=height, content_type=content_type,
                          observed_on=discovery['observed_on'], downloaded_at=now,
                          method=row.get('method', discovery['method']),
                          identity_match='official_product_link_and_image_filename_sku')
        except Exception as error:
            record.update(source_url=url, missing_reason=f'{type(error).__name__}: {error}')
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        products = list(pool.map(collect, catalog))
    report = {'schema_version': '1.0', 'observed_on': discovery['observed_on'],
              'summary': {'total': len(products), 'available': sum(p['status'] == 'available' for p in products)},
              'products': products}
    MANIFEST.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report['summary']))
    for p in products:
        if p['status'] != 'available':
            print(p['product_number'], p['missing_reason'])
    return 0 if report['summary']['available'] == len(products) else 1


if __name__ == '__main__':
    raise SystemExit(main())
