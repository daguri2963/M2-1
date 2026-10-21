"""Live provider smoke test using public product facts only. Never prints credentials."""
import asyncio
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.agent import GeminiAgent,AIError
from backend.models import ChatRequest

async def main():
    agent=GeminiAgent();started=time.monotonic()
    try:
        result=await agent.answer(ChatRequest(question='이 제품의 표시 기능과 주의사항을 확인하는 방법을 설명해 주세요.',productId='600000128'))
        report={'passed':True,'mode':result['mode'],'model':result['model'],'elapsedSeconds':round(time.monotonic()-started,2),'toolTrace':result['toolTrace'],'citationIds':[c['id'] for c in result['citations']],'productIds':result['productIds'],'testData':'public product only; no personal health data'}
        print(json.dumps(report,ensure_ascii=False,indent=2))
        (Path(__file__).resolve().parents[1]/'docs/gemini-live-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        return 0
    except AIError as error:
        print(json.dumps({'passed':False,'code':error.code,'message':error.message},ensure_ascii=False))
        return 1
    finally:
        await agent.close()

if __name__=='__main__':
    raise SystemExit(asyncio.run(main()))
