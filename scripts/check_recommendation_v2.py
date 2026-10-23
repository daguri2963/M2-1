"""Local v2 integration check. Synthetic choices only; --run-live consumes AI quota."""
import argparse,json,time
from datetime import datetime,timezone
from pathlib import Path
import httpx

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live',action='store_true')
    parser.add_argument('--port',type=int,default=8001)
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'docs/recommendation-v2-live-check.json')
    args=parser.parse_args()
    if not args.run_live:
        print('No requests sent. Add --run-live for local HTTP checks with real AI.');return 0
    if not 1<=args.port<=65535:parser.error('Invalid local port')
    report={'checkedAt':datetime.now(timezone.utc).isoformat(),'passed':False,'policyVersion':'2026-10-23.2','data':'synthetic adult choices and public labels only','checks':[]}
    stage='health';headers=None
    with httpx.Client(base_url=f'http://127.0.0.1:{args.port}',timeout=65) as client:
        try:
            health=client.get('/api/health');health.raise_for_status()
            assert health.json()['policyVersion']==report['policyVersion'] and health.json()['aiProvider']=='codyssey'
            consent=client.post('/api/sessions',json={'provider':'codyssey','adultConfirmed':True,'privacyAccepted':True,'aiAccepted':True,'version':health.json()['consentVersion']});consent.raise_for_status()
            headers={'X-Session-Token':consent.json()['token']}
            base={'habits':['다양하게 먹는 편이에요'],'existing':'없어요','productIds':[],'cautions':['해당 없어요'],'budget':'5,000원 이하','form':'','specialtyConfirmed':True}
            for goal,expected in [('일상의 활력',{'600000129','601678603','613602132'}),('혈당 관리',{'601678608','591580761','610910678'}),('다이어트',{'976195543'})]:
                stage=goal;started=time.monotonic()
                response=client.post('/api/recommendations',json={**base,'interests':[goal]},headers=headers);response.raise_for_status();data=response.json()
                assert data['status']=='ok' and {p['id'] for p in data['products']}==expected
                assert data['ai']['mode']=='ai' and data['ai']['citations']
                assert all(e['productId'] in expected for e in data['ai']['citations'])
                assert any(t['ok'] for t in data['ai']['toolTrace'])
                report['checks'].append({'case':goal,'elapsedSeconds':round(time.monotonic()-started,2),'productIds':[p['id'] for p in data['products']],'mode':data['ai']['mode'],'toolTrace':data['ai']['toolTrace'],'citationIds':[e['id'] for e in data['ai']['citations']],'text':data['ai']['text']})
            cases=[('scope_missing',{'interests':['혈당 관리'],'specialtyConfirmed':False},'insufficient'),('diagnosis',{'interests':['혈당 관리'],'cautions':['질환 진단·치료·의약품 복용 중이에요']},'restricted'),('same_weight_function',{'interests':['다이어트'],'existing':'제품 선택','productIds':['968235549']},'restricted')]
            for stage,patch,expected in cases:
                response=client.post('/api/recommendations',json={**base,**patch},headers=headers);response.raise_for_status();data=response.json()
                assert data['status']==expected and not data['products'] and data['ai']['mode']=='not_requested'
                report['checks'].append({'case':stage,'status':data['status'],'mode':data['ai']['mode']})
            for removed in ['눈 건강','잘 모르겠어요']:
                stage='removed_interest'
                response=client.post('/api/recommendations',json={**base,'interests':[removed]},headers=headers)
                assert response.status_code==422 and response.json()['error']['code']=='INVALID_INPUT'
                report['checks'].append({'case':stage,'interest':removed,'status':422})
            stage='withdrawal';client.delete('/api/sessions/current',headers=headers).raise_for_status()
            assert client.post('/api/recommendations',json={**base,'interests':['일상의 활력']},headers=headers).status_code==401
            report['checks'].append({'case':stage,'status':401});report['passed']=True
        except (AssertionError,KeyError,ValueError,httpx.HTTPError) as error:
            report['error']={'stage':stage,'code':type(error).__name__}
        finally:
            if headers:client.delete('/api/sessions/current',headers=headers)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({**report,'checks':[{k:v for k,v in c.items() if k!='text'} for c in report['checks']]},ensure_ascii=False,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
