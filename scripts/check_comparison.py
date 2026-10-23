"""Opt-in local comparison AI check. Sends public product labels only; consumes AI quota."""
import argparse,json,time
from datetime import datetime,timezone
from pathlib import Path
import httpx


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live',action='store_true')
    parser.add_argument('--port',type=int,default=8001)
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'docs/comparison-live-check.json')
    args=parser.parse_args()
    if not args.run_live:print('No requests sent. Use --run-live to check the local AI connection.');return 0
    if not 1<=args.port<=65535:parser.error('Invalid local port')
    report={'checkedAt':datetime.now(timezone.utc).isoformat(),'passed':False,'data':'public product pairs only; no survey or chat','checks':[]}
    headers=None;stage='health'
    with httpx.Client(base_url=f'http://127.0.0.1:{args.port}',timeout=65) as api:
        try:
            health=api.get('/api/health');health.raise_for_status()
            pair=['600000129','600000128']
            assert api.post('/api/compare/explanation',json={'productIds':pair}).status_code==401
            assert api.post('/api/compare',json={'productIds':pair}).status_code==200
            report['checks'].append({'case':'table_public_ai_requires_consent','passed':True})
            r=api.post('/api/sessions',json={'provider':'codyssey','adultConfirmed':True,'privacyAccepted':True,'aiAccepted':True,'version':health.json()['consentVersion']});r.raise_for_status()
            headers={'X-Session-Token':r.json()['token']}
            for stage,pair in [('different_purposes',['600000129','600000128']),('same_formula_different_pack',['600000128','600000270']),('general_food_vs_functional',['610911097','600000313'])]:
                started=time.monotonic()
                response=api.post('/api/compare/explanation',json={'productIds':pair},headers=headers);response.raise_for_status();result=response.json()
                assert result['mode']=='ai' and result['productIds']==pair and 1<=len(result['highlights'])<=3
                assert {e['productId'] for e in result['citations']}==set(pair)
                report['checks'].append({'case':stage,'elapsedSeconds':round(time.monotonic()-started,2),'result':result})
            stage='cache';started=time.monotonic()
            r=api.post('/api/compare/explanation',json={'productIds':pair},headers=headers);r.raise_for_status()
            assert r.json()['cached']
            report['checks'].append({'case':stage,'cached':True,'elapsedSeconds':round(time.monotonic()-started,2)})
            stage='withdrawal';api.delete('/api/sessions/current',headers=headers).raise_for_status()
            assert api.post('/api/compare/explanation',json={'productIds':pair},headers=headers).status_code==401
            assert api.post('/api/compare',json={'productIds':pair}).status_code==200
            report['checks'].append({'case':stage,'passed':True});report['passed']=True
        except (AssertionError,KeyError,ValueError,httpx.HTTPError) as error:
            report['error']={'stage':stage,'code':type(error).__name__}
            if isinstance(error,httpx.HTTPStatusError):
                report['error']['status']=error.response.status_code
                try:report['error']['apiCode']=error.response.json()['error']['code']
                except (KeyError,ValueError):pass
        finally:
            if headers:api.delete('/api/sessions/current',headers=headers)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'checks':[{k:v for k,v in c.items() if k!='result'} for c in report['checks']],'error':report.get('error')},ensure_ascii=False,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
