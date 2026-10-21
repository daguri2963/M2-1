"""End-to-end HTTP smoke test. Uses synthetic choices and never prints session/API keys."""
import json
import argparse
import time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
import httpx

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8000',help='Backend origin; remote checks require HTTPS.')
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'docs/backend-live-check.json')
    args=parser.parse_args()
    origin=urlsplit(args.base_url)
    if origin.username or origin.password or origin.query or origin.fragment or origin.path not in ('','/') or not origin.hostname or (origin.scheme!='https' and not (origin.scheme=='http' and origin.hostname in ('127.0.0.1','localhost'))):
        parser.error('Use an HTTPS backend origin or local HTTP origin without credentials, paths or query parameters.')
    base_url=args.base_url.rstrip('/')
    results={}
    with httpx.Client(base_url=base_url,timeout=65) as client:
        health=client.get('/api/health');health.raise_for_status();health=health.json()
        assert health['ready'] and health['aiConfigured']
        catalog=client.get('/api/products');catalog.raise_for_status()
        assert len(catalog.json()['products'])==87
        assert client.get('/api/products/600651654').status_code==404
        consent=client.post('/api/sessions',json={'adultConfirmed':True,'privacyAccepted':True,'aiAccepted':True,'version':health['consentVersion']})
        consent.raise_for_status();headers={'X-Session-Token':consent.json()['token']}
        try:
            profile={'interests':['장 건강'],'habits':['다양하게 먹는 편이에요'],'existing':'없어요','productIds':[],'cautions':['해당 없어요'],'budget':'5,000원 이하','form':''}
            started=time.monotonic();response=client.post('/api/recommendations',json=profile,headers=headers);response.raise_for_status();recommendation=response.json()
            assert recommendation['status']=='ok' and recommendation['ai']['mode']=='gemini'
            results['recommendation']={'elapsedSeconds':round(time.monotonic()-started,2),'productIds':[p['id'] for p in recommendation['products']],'mode':recommendation['ai']['mode'],'model':recommendation['ai']['model'],'toolTrace':recommendation['ai']['toolTrace'],'citationIds':[e['id'] for e in recommendation['ai']['citations']]}
            response=client.post('/api/compare',json={'productIds':['600000128','600000147']});response.raise_for_status();assert response.json()['rows']
            response=client.post('/api/overlap',json={'productIds':['600000128','600000270']},headers=headers);response.raise_for_status();assert response.json()['duplicates']
            restricted=client.post('/api/recommendations',json={**profile,'cautions':['임신·수유 중이에요']},headers=headers)
            assert restricted.json()['status']=='restricted' and not restricted.json()['products']
            unknown=client.post('/api/recommendations',json={**profile,'existing':'목록에 없어요'},headers=headers)
            assert unknown.json()['status']=='insufficient'
            started=time.monotonic();response=client.post('/api/chat',json={'question':'함량과 기준량의 차이가 궁금해요.'},headers=headers);response.raise_for_status();guide=response.json()
            assert guide['mode']=='gemini' and guide['citations'] and guide['productIds']==[]
            assert all(e.get('kind')=='label_guide' and e['productId'] is None for e in guide['citations'])
            results['labelReading']={'elapsedSeconds':round(time.monotonic()-started,2),'mode':guide['mode'],'text':guide['text'],'citationIds':[e['id'] for e in guide['citations']],'productIds':guide['productIds']}
            started=time.monotonic();response=client.post('/api/chat',json={'question':'표시 기능과 주의사항을 확인할 곳을 설명해 주세요.','productId':'600000128'},headers=headers);response.raise_for_status();answer=response.json()
            assert answer['mode']=='gemini' and answer['citations']
            results['chat']={'elapsedSeconds':round(time.monotonic()-started,2),'mode':answer['mode'],'model':answer['model'],'toolTrace':answer['toolTrace'],'citationIds':[e['id'] for e in answer['citations']]}
        finally:
            client.delete('/api/sessions/current',headers=headers).raise_for_status()
        assert client.post('/api/chat',json={'question':'표시 설명'},headers=headers).status_code==401
    report={'passed':True,'checkedAt':datetime.now(timezone.utc).isoformat(),'baseUrl':base_url,'data':'synthetic general-adult choices and public product labels only','publicProducts':87,'checks':['health','consent','review_gate','recommendation_with_live_gemini','comparison','overlap','restricted','insufficient','label_reading_without_product','chat_with_live_gemini','withdrawal'],**results}
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
