"""Opt-in final API acceptance checks: three developer QA trials, not user feedback."""
import argparse,json,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
import httpx

BASE_PROFILE={'interests':['일상의 활력'],'habits':['다양하게 먹는 편이에요'],'existing':'없어요','productIds':[],'cautions':['해당 없어요'],'budget':'5,000원 이하','form':'','specialtyConfirmed':False}
EXPECTED={'600000129','601678603','613602132'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live',action='store_true')
    parser.add_argument('--base-url',default='http://127.0.0.1:8001')
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'docs/final/evidence/acceptance-api.json')
    args=parser.parse_args()
    if not args.run_live:print('No requests sent. --run-live runs three synthetic trials and consumes AI quota.');return 0
    origin=urlsplit(args.base_url)
    if origin.username or origin.password or origin.query or origin.fragment or origin.path not in ('','/') or not ((origin.scheme=='https' and origin.hostname=='m2-1-api.onrender.com') or (origin.scheme=='http' and origin.hostname in ('127.0.0.1','localhost'))):parser.error('Use the project production API or a local HTTP server.')
    report={'checkedAt':datetime.now(timezone.utc).isoformat(),'baseUrl':args.base_url,'layer':'HTTP API','operator':'developer QA with synthetic adult selections, not independent users','passed':False,'trials':[]}
    with httpx.Client(base_url=args.base_url,timeout=65) as api:
        health=api.get('/api/health');health.raise_for_status();h=health.json()
        assert h['ready'] and h['aiConfigured'] and h['aiProvider']=='codyssey'
        report['health']=h
        for attempt in range(1,4):
            trial={'attempt':attempt,'checks':[]};headers=None
            def record(name,call):
                started=time.monotonic()
                try:
                    evidence=call()
                    trial['checks'].append({'id':name,'passed':True,'seconds':round(time.monotonic()-started,2),'evidence':evidence})
                except (AssertionError,KeyError,ValueError,httpx.HTTPError) as error:
                    detail={'code':type(error).__name__}
                    if isinstance(error,httpx.HTTPStatusError):
                        detail['status']=error.response.status_code
                        try:detail['apiCode']=error.response.json()['error']['code']
                        except (KeyError,ValueError):pass
                    trial['checks'].append({'id':name,'passed':False,'seconds':round(time.monotonic()-started,2),'error':detail})
            def post(path,data):
                r=api.post(path,json=data,headers=headers);r.raise_for_status();return r.json()
            try:
                assert api.post('/api/recommendations',json=BASE_PROFILE).status_code==401
                bad={'provider':'codyssey','adultConfirmed':True,'privacyAccepted':True,'aiAccepted':False,'version':h['consentVersion']}
                assert api.post('/api/sessions',json=bad).status_code==400
                r=api.post('/api/sessions',json={**bad,'aiAccepted':True});r.raise_for_status();headers={'X-Session-Token':r.json()['token']}
                def validation():
                    for interests in [[],['눈 건강'],['잘 모르겠어요']]:
                        assert api.post('/api/recommendations',json={**BASE_PROFILE,'interests':interests},headers=headers).status_code==422
                    return {'rejected':'missing and removed interests','status':422}
                record('M02',validation)
                def chat():
                    d=post('/api/chat',{'question':'함량과 기준량의 차이가 궁금해요.'})
                    assert d['mode']=='ai' and d['citations'] and any(t['ok'] for t in d['toolTrace']) and not d['productIds']
                    return {'mode':d['mode'],'citationIds':[e['id'] for e in d['citations']],'toolTrace':d['toolTrace']}
                record('M03',chat)
                def recommendation():
                    d=post('/api/recommendations',BASE_PROFILE)
                    assert d['status']=='ok' and {p['id'] for p in d['products']}==EXPECTED
                    assert d['ai']['mode']=='ai' and d['ai']['citations'] and any(t['ok'] for t in d['ai']['toolTrace'])
                    assert all(e['productId'] in EXPECTED for e in d['ai']['citations'])
                    return {'mode':d['ai']['mode'],'classificationVersion':d['classificationVersion'],'productIds':[p['id'] for p in d['products']],'citationIds':[e['id'] for e in d['ai']['citations']],'toolTrace':d['ai']['toolTrace']}
                record('M04',recommendation)
                def detail():
                    r=api.get('/api/products/600000128');r.raise_for_status();p=r.json()
                    assert all(p[k] for k in ['intake','cautions','functionText','sourceUrl','checkedAt','nutrients'])
                    assert api.get('/api/products/600651654').status_code==404
                    return {'productId':p['id'],'checkedAt':p['checkedAt'],'heldStatus':404,'sourceUrl':p['sourceUrl']}
                record('M05',detail)
                def overlap():
                    d=post('/api/overlap',{'productIds':['600000128','600000270']})
                    mg=next(n for n in d['duplicates'] if n['name']=='마그네슘')
                    assert mg['dailyTotal']=={'amount':'630','unit':'mg'}
                    return {'status':d['status'],'magnesiumDailyLabelTotal':mg['dailyTotal'],'scope':'registered product labels only, not combined-use safety'}
                record('M06',overlap)
                def compare():
                    d=post('/api/compare',{'productIds':['600000128','600000147']})
                    assert [p['id'] for p in d['products']]==['600000128','600000147']
                    assert '4정' in next(r for r in d['rows'] if r['label']=='칼슘')['values'][1]
                    assert api.post('/api/compare',json={'productIds':['600000128']*2}).status_code==422
                    return {'productIds':[p['id'] for p in d['products']],'calciumLabel':next(r for r in d['rows'] if r['label']=='칼슘')['values'],'duplicateStatus':422}
                record('M07',compare)
                def limits():
                    restricted=post('/api/recommendations',{**BASE_PROFILE,'cautions':['임신·수유 중이에요']})
                    unknown=post('/api/recommendations',{**BASE_PROFILE,'existing':'목록에 없어요'})
                    specialty=post('/api/recommendations',{**BASE_PROFILE,'interests':['혈당 관리']})
                    assert restricted['status']=='restricted' and not restricted['products']
                    assert unknown['status']==specialty['status']=='insufficient'
                    assert all(d['ai']['mode']=='not_requested' for d in [restricted,unknown,specialty])
                    return {'restricted':restricted['status'],'unknown':unknown['status'],'scopeMissing':specialty['status'],'externalAI':'not_requested'}
                record('M09',limits)
                def explanation():
                    pair=['600000129','600000128'];d=post('/api/compare/explanation',{'productIds':pair})
                    assert d['mode']=='ai' and d['productIds']==pair and {e['productId'] for e in d['citations']}==set(pair)
                    return {'mode':d['mode'],'version':d['version'],'cached':d['cached'],'citationIds':[e['id'] for e in d['citations']]}
                record('S01',explanation)
                def withdrawal():
                    api.delete('/api/sessions/current',headers=headers).raise_for_status()
                    assert api.post('/api/compare/explanation',json={'productIds':['600000129','600000128']},headers=headers).status_code==401
                    assert api.post('/api/compare',json={'productIds':['600000129','600000128']}).status_code==200
                    return {'beforeConsent':401,'missingConsent':400,'afterWithdrawal':401,'publicCompare':200}
                record('M01',withdrawal)
            finally:
                if headers:api.delete('/api/sessions/current',headers=headers)
            report['trials'].append(trial)
            print(json.dumps({'attempt':attempt,'checks':[{k:c[k] for k in ('id','passed')} for c in trial['checks']]},ensure_ascii=False),flush=True)
    report['summary']={name:{'attempts':3,'successes':sum(c['passed'] for t in report['trials'] for c in t['checks'] if c['id']==name)} for name in ['M01','M02','M03','M04','M05','M06','M07','M09','S01']}
    report['passed']=all(r['successes']>=2 for r in report['summary'].values())
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'summary':report['summary']},ensure_ascii=False))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
