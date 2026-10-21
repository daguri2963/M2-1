"""Small reviewed knowledge corpus, searched by Korean aliases and topic before generation."""
import json,re
from functools import lru_cache
from pathlib import Path
from .privacy import safe_history

ALIASES={
 'c':('비타민c','비타민씨','아스코르빈산'),
 'd':('비타민d','비타민디'),
 'b12':('비타민b12','b12','비타민비12'),
 'e':('비타민e','비타민이'),
 'calcium':('칼슘','calcium'),
 'magnesium':('마그네슘','magnesium'),
 'zinc':('아연','zinc'),
 'iron':('철분','철영양제','헤모글로빈','iron','식품의철','헴철','비헴철','철은','철과'),
 'omega3':('오메가3','오메가-3','epa','dha','어유'),
 'probiotics':('유산균','프로바이오틱스','probiotic'),
}
TOPICS={
 'timing':('공복','식후','식전','시간','식사','언제','아침','저녁','밤','흡수','탄산','구연산'),
 'caution':('주의','부작용','과량','고함량','메가도스','설사','고용량','위험','장기','오래'),
 'interaction':('상호작용','의약품','와파린','항생제','약과','병용'),
 'storage':('보관','냉장','실온','소비기한','유통기한'),
 'evidence':('효과','근거','역할','뭐에','많을수록','균수','균주','cfu','피로','활력'),
 'overlap':('중복','여러','겹치','종합비타민','멀티비타민'),
}

def compact(text):return re.sub(r'\s+','',text).lower()

@lru_cache(maxsize=1)
def corpus():return json.loads(Path(__file__).with_name('nutrition-knowledge.json').read_text())

def context_query(question,history=()):
    q=compact(question)
    if re.match(r'^(그럼|그러면|그건|그것|이건|그성분|그영양제)',q) and not any(a in q for names in ALIASES.values() for a in names):
        for h in reversed(safe_history(history)):
            if h.role=='user':return h.text+' '+question
    return question

def search(query,limit=4):
    q=compact(query)
    entities={key for key,names in ALIASES.items() if any(a in q for a in names)}
    topics={key for key,names in TOPICS.items() if any(a in q for a in names)}
    ranked=[];data=corpus()
    for index,c in enumerate(data['cards']):
        if c['reviewStatus']!='source_checked':continue
        if c['ingredient'] and c['ingredient'] not in entities:continue
        hits=sum(compact(t) in q for t in c['tags'])
        if not hits and not (c['ingredient'] and c['ingredient'] in entities):continue
        score=hits*3+(12 if c['ingredient'] in entities else 0)+(10 if c['topic'] in topics else 0)
        if c['ingredient'] and not topics and c['topic']=='basics':score+=10
        # Public product label questions keep the product DB as their primary evidence.
        src=data['sources'][c['sourceId']]
        ranked.append((score,-index,{'id':c['id'],'kind':'knowledge','productId':None,'productUrl':None,'title':c['title']+' · '+src['publisher']+' (공식 안내 요약)','text':c['text'],'url':src['url'],'observedAt':src['checkedAt'],'scope':c['scope']}))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True)
    return [item[2] for item in ranked[:limit]]

def is_product_question(question,product_id=None):
    q=compact(question)
    labelled_ingredient='표시' in q and any(a in q for names in ALIASES.values() for a in names)
    return bool(product_id or labelled_ingredient or re.search(r'다이소|제품.*(?:표시|가격|성분|함량|섭취|보관)|이\s*(?:제품|상품)|품번|비교',question))
