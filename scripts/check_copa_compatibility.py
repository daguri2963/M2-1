"""Explicit live Codyssey compatibility check. Uses only synthetic/public data."""
import argparse,asyncio,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from openai import OpenAIError
from backend import config
from backend.copa import create_client,complete
from backend.agent import SupplementAgent,AIError,ANSWER_SCHEMA
from backend.models import AgentAnswer,ChatRequest


async def run(args):
    if not config.API_KEY:
        print(json.dumps({'passed':False,'status':'key_required','file':str(config.ROOT/'.env'),'setting':'COPA_API_KEY'},ensure_ascii=False))
        return 2
    if not args.run_live:
        print('Key entry detected. No request sent. Add --run-live to run the paid/quota-consuming check.')
        return 0
    report={'checkedAt':datetime.now(timezone.utc).isoformat(),'passed':False,'baseUrl':config.BASE_URL,'model':config.MODEL,'data':'synthetic status and public product/knowledge only','checks':[]}
    stage='configuration';agent=None;started=time.monotonic()
    try:
        agent=SupplementAgent(create_client())
        stage='plain_chat'
        response=await complete(agent.client,[{'role':'user','content':'연결 확인용입니다. 짧게 인사해 주세요.'}])
        assert response.choices[0].message.content
        report['checks'].append(stage)
        stage='function_call'
        tool={'type':'function','function':{'name':'get_check_status','description':'검증용 공개 연결 상태를 조회합니다.','strict':True,'parameters':{'type':'object','properties':{},'required':[],'additionalProperties':False}}}
        messages=[{'role':'user','content':'반드시 먼저 get_check_status 도구로 검증용 상태를 조회하고 근거 id compat:status를 사용해 설명해 주세요.'}]
        response=await complete(agent.client,messages,tools=[tool],tool_choice='auto')
        calls=response.choices[0].message.tool_calls or []
        assert len(calls)==1 and calls[0].function.name=='get_check_status' and json.loads(calls[0].function.arguments)=={}
        call=calls[0]
        messages.extend([{'role':'assistant','content':response.choices[0].message.content,'tool_calls':[{'id':call.id,'type':'function','function':{'name':call.function.name,'arguments':call.function.arguments}}]},
                         {'role':'tool','tool_call_id':call.id,'content':json.dumps({'id':'compat:status','state':'ready'})}])
        report['checks'].append(stage)
        stage='server_validated_tool_result'
        messages.append({'role':'user','content':json.dumps({'instruction':'이 스키마를 따르는 JSON 객체 하나만 출력하세요. 코드 블록과 부연 문구 금지. 조회한 상태만 설명하고 citationIds는 ["compat:status"], productIds는 []로 쓰세요.','responseSchema':ANSWER_SCHEMA},ensure_ascii=False)})
        response=await complete(agent.client,messages)
        answer=AgentAnswer.model_validate_json(response.choices[0].message.content)
        assert answer.citationIds==['compat:status'] and answer.productIds==[]
        report['checks'].append({'case':stage,'outputValidation':'server Pydantic; provider response_format is not supported'})
        stage='knowledge_agent'
        answer=await agent.answer(ChatRequest(question='비타민D와 식사의 관계가 궁금해요.'))
        assert answer['mode']=='ai' and any(c['id']=='knowledge:d-meal' for c in answer['citations']) and answer['productIds']==[]
        assert any(t['ok'] for t in answer['toolTrace'])
        report['checks'].append({'case':stage,'toolTrace':answer['toolTrace'],'citationIds':[e['id'] for e in answer['citations']]})
        stage='product_agent'
        answer=await agent.answer(ChatRequest(question='이 제품의 표시 기능과 주의사항을 확인하는 방법을 설명해 주세요.',productId='600000128'))
        assert answer['mode']=='ai' and any(e['productId']=='600000128' for e in answer['citations']) and any(t['ok'] for t in answer['toolTrace'])
        report['checks'].append({'case':stage,'toolTrace':answer['toolTrace'],'citationIds':[e['id'] for e in answer['citations']]})
        report['passed']=True
    except AIError as error:
        report['error']={'stage':stage,'code':error.code}
    except OpenAIError as error:
        report['error']={'stage':stage,'code':type(error).__name__,'httpStatus':getattr(error,'status_code',None)}
    except (AssertionError,ValueError,TypeError,AttributeError,IndexError):
        report['error']={'stage':stage,'code':'COMPATIBILITY_NOT_CONFIRMED'}
    finally:
        if agent:await agent.close()
    report['elapsedSeconds']=round(time.monotonic()-started,2)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-live',action='store_true',help='Send quota-consuming requests with the local COPA virtual key.')
    p.add_argument('--report',type=Path,default=config.ROOT/'docs/copa-compatibility-check.json')
    raise SystemExit(asyncio.run(run(p.parse_args())))
