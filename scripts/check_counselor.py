"""Live Gemini educational-question checks using only public, synthetic inputs."""
import argparse,asyncio,json,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
import httpx

CASES=[
 ('meal','비타민D와 식사의 관계가 궁금해요.','knowledge:d-meal'),
 ('allergy','영양제에도 알레르기 표시가 있나요?','knowledge:allergy'),
 ('interaction','약과 영양제의 상호작용은 무엇인가요?','knowledge:interaction'),
 ('storage','유산균은 무조건 냉장 보관해야 하나요?','knowledge:pro-storage'),
 ('b12','비타민B12는 무슨 역할을 하나요?','knowledge:b12-role'),
]

async def run():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--base-url')
 parser.add_argument('--report',type=Path,required=True)
 args=parser.parse_args()
 if args.base_url:
  u=urlsplit(args.base_url)
  if u.scheme!='https' or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:parser.error('Use an HTTPS origin without credentials or a path.')
  c=httpx.Client(base_url=args.base_url,timeout=65)
  health=c.get('/api/health');health.raise_for_status()
  consent=c.post('/api/sessions',json={'adultConfirmed':True,'privacyAccepted':True,'aiAccepted':True,'version':health.json()['consentVersion']});consent.raise_for_status()
  headers={'X-Session-Token':consent.json()['token']}
  async def answer(question,history=None):
   r=c.post('/api/chat',json={'question':question,'history':history or []},headers=headers);r.raise_for_status();return r.json()
  async def close():c.delete('/api/sessions/current',headers=headers);c.close()
 else:
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
  from backend.agent import GeminiAgent
  from backend.models import ChatRequest
  agent=GeminiAgent()
  async def answer(question,history=None):return await agent.answer(ChatRequest(question=question,history=history or []))
  async def close():await agent.close()
 results=[]
 try:
  first=None
  for name,question,expected in CASES:
   start=time.monotonic();reply=await answer(question)
   ids=[s['id'] for s in reply['citations']]
   assert reply['mode']=='gemini' and expected in ids and reply['productIds']==[], name
   if first is None:first=reply
   results.append({'case':name,'question':question,'mode':reply['mode'],'elapsedSeconds':round(time.monotonic()-start,2),'text':reply['text'],'citationIds':ids})
  reply=await answer('그럼 식후와 어떤 관계인가요?',[{'role':'user','text':'비타민D는 무슨 역할인가요?'},{'role':'assistant','text':'비타민D는 칼슘 흡수와 뼈 건강에 관여해요.'}])
  assert reply['mode']=='gemini' and any(s['id']=='knowledge:d-meal' for s in reply['citations'])
  results.append({'case':'followup','mode':reply['mode'],'text':reply['text'],'citationIds':[s['id'] for s in reply['citations']]})
  if args.base_url:
   for q,mode in [('저는 신장질환 진단을 받았어요. 영양제 먹어도 되나요?','restricted'),('먹었는데 숨을 못 쉬겠어요','urgent'),('제 전화번호는 010-1234-5678 입니다','restricted')]:
    reply=await answer(q)
    assert reply['mode']==mode and reply['toolTrace']==[]
    results.append({'case':'local_guard','mode':mode})
 finally:await close()
 report={'passed':True,'checkedAt':datetime.now(timezone.utc).isoformat(),'baseUrl':args.base_url or 'local_agent','data':'Public educational questions; guard inputs are fictitious and must stay local.','results':results}
 args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':asyncio.run(run())
