import asyncio,json
import httpx
import pytest
from openai import AsyncOpenAI
from backend import config
from backend.agent import SupplementAgent,AIError,TOOLS
from backend.copa import create_client,valid_base_url
from backend.models import ChatRequest


def envelope(content=None,calls=None,finish='stop',refusal=None):
    return {'id':'chatcmpl-test','object':'chat.completion','created':0,'model':'gpt-5.4',
            'choices':[{'index':0,'finish_reason':finish,'message':{'role':'assistant','content':content,'tool_calls':calls,'refusal':refusal}}]}


def test_real_sdk_wire_contract_keeps_tool_ids_and_structured_grounding():
    sent=[]
    def handle(request):
        assert str(request.url)=='https://copa.codyssey.kr/v1/chat/completions'
        assert request.headers['authorization']=='Bearer test-virtual-key'
        body=json.loads(request.content);sent.append(body)
        assert body['model']=='gpt-5.4' and 'reasoning_effort' not in body
        assert 'response_format' not in body
        assert body['store'] is False and body['max_completion_tokens']==1800
        if 'tools' in body:
            assert body['tool_choice']=='auto'
            assert body['tools'][0]['function']['strict'] is True
            return httpx.Response(200,json=envelope(calls=[{'id':'call-evidence','type':'function','function':{'name':'search_nutrition_knowledge','arguments':json.dumps({'query':'비타민D 식사'})}}],finish='tool_calls'))
        assert json.loads(body['messages'][-1]['content'])['responseSchema']['additionalProperties'] is False
        assert any(m.get('tool_call_id')=='call-evidence' and m['role']=='tool' for m in body['messages'])
        assert body['messages'][-1]['role']=='user'
        return httpx.Response(200,json=envelope(content=json.dumps({'text':'비타민D는 식사와 관련해 흡수를 살펴볼 수 있어요.','citationIds':['knowledge:d-meal'],'productIds':[]})))
    async def run():
        c=AsyncOpenAI(api_key='test-virtual-key',base_url=config.BASE_URL,max_retries=0,http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))
        agent=SupplementAgent(c)
        try:return await agent.answer(ChatRequest(question='비타민D와 식사의 관계가 궁금해요.'))
        finally:await agent.close()
    result=asyncio.run(run())
    assert result['mode']=='ai' and result['provider']=='codyssey'
    assert result['toolTrace']==[{'tool':'search_nutrition_knowledge','ok':True}]
    assert len(sent)==2


@pytest.mark.parametrize('url',[
    'https://api.openai.com/v1','http://copa.codyssey.kr/v1',
    'https://copa.codyssey.kr.evil.example/v1','https://user:secret@copa.codyssey.kr/v1',
    'https://copa.codyssey.kr/v1?api_key=secret','https://copa.codyssey.kr/v1/chat/completions',
])
def test_virtual_key_destination_is_not_silently_changed(url,monkeypatch):
    assert not valid_base_url(url)
    monkeypatch.setattr(config,'BASE_URL',url)
    with pytest.raises(AIError) as e:create_client()
    assert e.value.code=='AI_CONFIGURATION'


def test_existing_gemini_key_is_not_a_copa_credential(monkeypatch):
    monkeypatch.setattr(config,'API_KEY','')
    monkeypatch.setenv('GEMINI_API_KEY','legacy-not-copa')
    assert not SupplementAgent().configured()


@pytest.mark.parametrize('status,expected',[(400,'AI_CONFIGURATION'),(401,'AI_CONFIGURATION'),(403,'AI_CONFIGURATION'),(404,'AI_CONFIGURATION'),(429,'AI_RATE_LIMIT'),(500,'AI_UNAVAILABLE')])
def test_sdk_errors_are_normalized_without_retry_or_provider_body_leak(status,expected):
    requests=[]
    def handle(request):
        requests.append(request)
        return httpx.Response(status,json={'error':{'message':'private-marker-should-not-escape','type':'invalid_request_error','code':'test'}})
    async def run():
        c=AsyncOpenAI(api_key='test-virtual-key',base_url=config.BASE_URL,max_retries=0,http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))
        agent=SupplementAgent(c)
        try:
            with pytest.raises(AIError) as e:await agent.answer(ChatRequest(question='비타민D 역할'))
            assert e.value.code==expected and 'private-marker' not in e.value.message
        finally:await agent.close()
    asyncio.run(run());assert len(requests)==1


@pytest.mark.parametrize('body',[
    envelope(content='도구 없이 답변'),
    envelope(content='잘린 답변',finish='length'),
    envelope(refusal='provider refusal'),
])
def test_missing_tools_incomplete_or_refused_output_never_becomes_a_success(body):
    async def run():
        c=AsyncOpenAI(api_key='test-virtual-key',base_url=config.BASE_URL,max_retries=0,http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=body))))
        agent=SupplementAgent(c)
        try:
            with pytest.raises(AIError):await agent.answer(ChatRequest(question='비타민D 역할'))
        finally:await agent.close()
    asyncio.run(run())


@pytest.mark.parametrize('content,expected',[
    ('```json\n{}\n```','AI_INVALID_RESPONSE'),
    ('[]','AI_INVALID_RESPONSE'),
    (json.dumps({'text':'설명','citationIds':['knowledge:d-meal'],'productIds':[],'extra':'untrusted'}),'AI_INVALID_RESPONSE'),
    (json.dumps({'text':'설명','citationIds':['invented'],'productIds':[]}),'AI_INVALID_EVIDENCE'),
    (json.dumps({'text':'설명','citationIds':['knowledge:d-meal'],'productIds':['invented']}),'AI_INVALID_PRODUCT'),
    (json.dumps({'text':'함량은 99mg이에요.','citationIds':['knowledge:d-meal'],'productIds':[]}),'AI_UNSUPPORTED_CLAIM'),
])
def test_plain_json_output_still_requires_server_schema_and_grounding(content,expected):
    def handle(request):
        body=json.loads(request.content)
        assert 'response_format' not in body
        if 'tools' in body:
            return httpx.Response(200,json=envelope(calls=[{'id':'evidence','type':'function','function':{'name':'search_nutrition_knowledge','arguments':json.dumps({'query':'비타민D 식사'})}}],finish='tool_calls'))
        return httpx.Response(200,json=envelope(content=content))
    async def run():
        c=AsyncOpenAI(api_key='test-virtual-key',base_url=config.BASE_URL,max_retries=0,http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))
        agent=SupplementAgent(c)
        try:
            with pytest.raises(AIError) as error:await agent.answer(ChatRequest(question='비타민D와 식사의 관계가 궁금해요.'))
            assert error.value.code==expected
        finally:await agent.close()
    asyncio.run(run())


def test_strict_tools_have_closed_objects_and_nullable_optional_arguments():
    for tool in TOOLS:
        function=tool['function'];schema=function['parameters']
        assert function['strict'] and schema['additionalProperties'] is False
        assert set(schema['required'])==set(schema['properties'])
    evidence=next(t for t in TOOLS if t['function']['name']=='search_evidence')
    assert evidence['function']['parameters']['properties']['product_ids']['type']==['array','null']


def test_legacy_consent_cannot_silently_authorize_the_new_provider():
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as c:
        payload={'adultConfirmed':True,'privacyAccepted':True,'aiAccepted':True,'version':config.CONSENT_VERSION}
        assert c.post('/api/sessions',json=payload).status_code==422
        assert c.post('/api/sessions',json={**payload,'provider':'gemini'}).status_code==422
        r=c.post('/api/sessions',json={**payload,'provider':'codyssey'})
        assert r.status_code==200
        assert c.delete('/api/sessions/current',headers={'X-Session-Token':r.json()['token']}).status_code==200
