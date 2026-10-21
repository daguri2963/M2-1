"""Query-time retrieval of reviewed, public label-reading guidance, not product facts."""
import json
import re
from pathlib import Path


def evidence(query):
    compact=re.sub(r'\s+','',query)
    concept=('기준량' in compact or '기준치' in compact or
             ('함량' in compact and '기준' in compact) or
             (any(word in compact for word in ('영양정보','영양성분표','함량표','제품표시')) and
              any(word in compact for word in ('읽','뜻','의미'))))
    if not concept:return []
    return json.loads(Path(__file__).with_name('label-guides.json').read_text())
