import asyncio
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from google.genai import types
from backend import config, policy, repository as repo
from backend.agent import AIError, GeminiAgent, sanitize_answer
from backend.main import app, sessions, traffic
from backend.models import AgentAnswer, ChatRequest, Survey

def survey(**changes):
    return Survey(**{'interests':['뼈·근육 건강'],'habits':['다양하게 먹는 편이에요'],'existing':'없어요','cautions':['해당 없어요'],**changes})

@pytest.fixture
def client():
    sessions.clear();traffic.clear()
    with TestClient(app) as c:yield c

def headers(client):
    r=client.post('/api/sessions',json={'adultConfirmed':True,'privacyAccepted':True,'aiAccepted':True,'version':config.CONSENT_VERSION})
    assert r.status_code==200
    return {'X-Session-Token':r.json()['token']}

def test_sqlite_public_export_parity_and_held_gate():
    saved=json.loads((Path(__file__).resolve().parents[2]/'frontend/src/data/products.json').read_text())
    assert repo.list_products()==saved
    with pytest.raises(LookupError):repo.get_product('600651654')
    with pytest.raises(LookupError):repo.get_product("' OR 1=1 --")

def test_policy_goals_budget_and_form_change_candidates():
    bone=policy.recommend(survey())
    gut=policy.recommend(survey(interests=['장 건강']))
    assert bone['status']==gut['status']=='ok'
    assert {p['id'] for p in bone['products']}!={p['id'] for p in gut['products']}
    cheap=policy.recommend(survey(budget='3,000원 이하',form='정제·캡슐'))
    assert cheap['status']=='ok'
    assert all(p['price']<=3000 and any(t in p['form'] for t in ['정제','캡슐']) for p in cheap['products'])
    assert all(e['id'].endswith(':function') for e in cheap['evidence'])
    assert policy.recommend(survey(budget='3,000원 이하',form='필름·액상'))['status']=='empty'

@pytest.mark.parametrize('caution',['의약품 복용·치료 중이에요','임신·수유 중이에요','알레르기를 확인해야 해요'])
def test_sensitive_conditions_never_produce_candidates(caution):
    result=policy.recommend(survey(cautions=[caution]))
    assert result['status']=='restricted' and result['products']==[]

@pytest.mark.parametrize('changes',[{'cautions':['잘 모르겠어요']},{'existing':'목록에 없어요'},{'existing':'잘 모르겠어요'},{'interests':['잘 모르겠어요']}])
def test_unknown_is_not_assumed_clear(changes):
    assert policy.recommend(survey(**changes))['status']=='insufficient'

def test_existing_products_exclude_duplicate_functional_ingredients():
    s=survey(existing='제품 선택',productIds=['600000128'])
    result=policy.recommend(s)
    taken={policy.canonical(n['name']) for n in policy.functional(repo.get_product('600000128'))}
    assert all(not taken.intersection(policy.canonical(n['name']) for n in policy.functional(p)) for p in result['products'])
    assert result['excludedCounts']['기존 제품과 표시 성분 중복']>0

def test_overlap_aliases_daily_units_and_unsupported_basis():
    assert policy.canonical('셀레늄')==policy.canonical('셀렌')
    assert policy.quantity({'amount':'1000','operator':'=','unit':'μg','basis':'1일 섭취량: 1정'})==(Decimal(1),'mg')
    assert policy.quantity({'amount':'70000','operator':'=','unit':'μg','basis':'총내용량 14포'}) is None
    assert policy.quantity({'amount':'1','operator':'<','unit':'mg','basis':'1일 1정'}) is None
    assert policy.quantity({'amount':'400','operator':'=','unit':'IU','basis':'1일 1정'})==(Decimal(400),'IU')
    result=policy.overlap(['600000128','600000270'])
    magnesium=next(d for d in result['duplicates'] if d['name']=='마그네슘')
    assert magnesium['dailyTotal']=={'amount':'630','unit':'mg'}

def test_foods_specialized_and_high_percentage_not_auto_candidates():
    result=policy.recommend(survey(interests=['다양한 성분 보기']))
    for p in result['products']:
        assert policy.exclusion(p) is None and '건강기능식품' in p['type']
    assert policy.exclusion(repo.get_product('610911095')) is not None
    # A gut-health marketing name must not conceal an additional glucose-care function.
    assert policy.exclusion(repo.get_product('591580761')) is not None
    assert all(p['id'] not in {'032306212','591580761','591580891'} for p in policy.recommend(survey(interests=['장 건강']))['products'])

def test_query_specific_rag_has_real_sources_and_changes_by_question():
    muscle=repo.evidence('근육',['600000128'])
    dose=repo.evidence('섭취',['600000128'])
    assert muscle and dose and muscle[0]['id']!=dose[0]['id']
    assert all(e['url'].startswith('https://cdn.daisomall.co.kr/') for e in muscle+dose)

def test_api_requires_consent_validates_and_withdraws(client):
    assert client.get('/api/health').json()['ready']
    assert client.post('/api/recommendations',json=survey().model_dump()).status_code==401
    assert client.post('/api/sessions',json={'adultConfirmed':False,'privacyAccepted':True,'aiAccepted':True,'version':config.CONSENT_VERSION}).status_code==400
    h=headers(client)
    invalid=survey().model_dump();invalid['cautions']=['해당 없어요','임신·수유 중이에요']
    response=client.post('/api/recommendations',json=invalid,headers=h)
    assert response.status_code==422 and 'input' not in response.text
    assert client.delete('/api/sessions/current',headers=h).json()['deleted']
    assert client.post('/api/recommendations',json=survey().model_dump(),headers=h).status_code==401

def test_api_missing_key_is_explicit_not_fake_ai(client,monkeypatch):
    import backend.main as main
    monkeypatch.setattr(config,'API_KEY','')
    monkeypatch.setattr(main.agent,'client',None)
    h=headers(client)
    result=client.post('/api/recommendations',json=survey().model_dump(),headers=h)
    assert result.status_code==200 and result.json()['status']=='ok'
    assert result.json()['ai']['mode']=='unavailable'
    assert result.json()['ai']['code']=='AI_NOT_CONFIGURED'
    chat=client.post('/api/chat',json={'question':'마그네슘 표시 설명'},headers=h)
    assert chat.status_code==503 and chat.json()['error']['code']=='AI_NOT_CONFIGURED'

def test_api_compare_and_unreviewed_identifiers(client):
    assert len(client.get('/api/products').json()['products'])==87
    assert client.get('/api/products/600651654').status_code==404
    assert client.post('/api/compare',json={'productIds':['600000128','600651654']}).status_code==404
    result=client.post('/api/compare',json={'productIds':['600000128','600000147']}).json()
    assert next(r for r in result['rows'] if r['label']=='관찰 가격')['values']==['3,000원','5,000원']
    assert next(r for r in result['rows'] if r['label']=='가격 확인일')['values']==['2026-10-19','2026-10-19']
    calcium=next(r for r in result['rows'] if r['label']=='칼슘')
    assert '4정' in calcium['values'][1]

def test_chat_sensitive_scope_is_server_guarded_without_ai(client):
    response=client.post('/api/chat',json={'question':'임신 중에 용량을 두 배로 먹어도 되나요?'},headers=headers(client))
    assert response.status_code==200 and response.json()['mode']=='restricted'
    assert response.json()['productIds']==[]

def test_session_expiry_and_bounded_requests(client):
    h=headers(client)
    sessions[h['X-Session-Token']]=0
    assert client.post('/api/chat',json={'question':'표시 설명'},headers=h).status_code==401
    h=headers(client)
    for _ in range(10):
        assert client.post('/api/chat',json={'question':'임신 중 추천'},headers=h).status_code==200
    assert client.post('/api/chat',json={'question':'임신 중 추천'},headers=h).status_code==429

class FakeModels:
    """Contract test only. Live Gemini verification is reported separately."""
    def __init__(self):self.calls=[]
    async def generate_content(self,**kwargs):
        self.calls.append(kwargs)
        if kwargs['config'].response_mime_type=='application/json':
            return SimpleNamespace(text=json.dumps({'text':'공식 표시에는 근육 기능 유지와 관련된 기능정보가 있어요. 표시 섭취방법과 주의사항을 함께 확인해 주세요.','citationIds':['600000128:function'],'productIds':['600000128']}))
        if len(self.calls)==1:
            part=types.Part.from_function_call(name='search_evidence',args={'query':'근육','product_ids':['600000128']})
        elif len(self.calls)==2:
            part=types.Part.from_function_call(name='get_product_details',args={'product_id':'600000128'})
        else:
            return SimpleNamespace(text=json.dumps({'text':'공식 표시에는 근육 기능 유지와 관련된 기능정보가 있어요. 표시 섭취방법과 주의사항을 함께 확인해 주세요.','citationIds':['600000128:function'],'productIds':['600000128']}))
        return SimpleNamespace(candidates=[SimpleNamespace(content=types.Content(role='model',parts=[part]))])

def test_agent_selects_and_executes_multiple_tools_then_validates_grounding():
    models=FakeModels();client=SimpleNamespace(aio=SimpleNamespace(models=models))
    result=asyncio.run(GeminiAgent(client).answer(ChatRequest(question='마그네슘 표시 설명')))
    assert [t['tool'] for t in result['toolTrace']]==['search_evidence','get_product_details']
    assert result['citations'][0]['productId']=='600000128'
    assert len(models.calls)==3
    assert models.calls[0]['config'].automatic_function_calling.disable is True

@pytest.mark.parametrize('answer',[
    {'text':'출처 설명','citationIds':['fake'],'productIds':[]},
    {'text':'출처 설명','citationIds':['valid'],'productIds':['600651654']},
    {'text':'하루 99정을 먹으세요','citationIds':['valid'],'productIds':[]},
    {'text':'https://fake.example/','citationIds':['valid'],'productIds':[]},
])
def test_unverified_model_output_rejected(answer):
    with pytest.raises(AIError):sanitize_answer(AgentAnswer(**answer),{'valid':{}},{'600000128':{}})

def test_agent_timeout_is_bounded(monkeypatch):
    class Slow:
        async def generate_content(self,**kwargs):await asyncio.sleep(1)
    client=SimpleNamespace(aio=SimpleNamespace(models=Slow()))
    monkeypatch.setattr(config,'AI_TIMEOUT',.01)
    with pytest.raises(AIError) as error:asyncio.run(GeminiAgent(client).answer(ChatRequest(question='마그네슘')))
    assert error.value.code=='AI_TIMEOUT'

def test_provider_receives_preferences_not_health_screen_or_existing_record():
    models=FakeModels();client=SimpleNamespace(aio=SimpleNamespace(models=models))
    s=survey(habits=['식사 시간이 불규칙해요'])
    result=asyncio.run(GeminiAgent(client).answer(ChatRequest(question='후보의 근거를 설명해 주세요.',survey=s),policy.recommend(s)))
    context=json.loads(models.calls[0]['contents'][0].parts[0].text)
    assert set(context['preferences'])=={'interests','budget','form'}
    assert 'survey' not in context and 'overlap' not in context['recommendation']
    assert '식사 시간이 불규칙해요' not in json.dumps(context,ensure_ascii=False)
    assert result['mode']=='gemini'

def test_no_profile_recommendation_and_personal_identifiers_stay_local(client):
    h=headers(client)
    response=client.post('/api/chat',json={'question':'나에게 추천해줘'},headers=h)
    assert response.json()['mode']=='insufficient'
    response=client.post('/api/chat',json={'question':'제 전화번호는 010-1234-5678 입니다'},headers=h)
    assert response.json()['mode']=='restricted'

@pytest.mark.parametrize('question',[
    '함량과 기준량의 차이가 궁금해요.',
    '함량 과 기준량 의 차이 를 알려 주세요',
    '기준량은 무슨 뜻인가요?',
    '영양성분 기준치가 무엇인가요?',
    '영양성분표 읽는 법이 궁금해요.',
])
def test_label_concepts_have_official_guides_without_selecting_a_product(question):
    sources=repo.evidence(question)
    assert sources and all(e['kind']=='label_guide' for e in sources)
    assert all(e['productId'] is None and e['productUrl'] is None for e in sources)
    assert all(e['url'].startswith(('https://www.fda.gov/','https://www.foodsafetykorea.go.kr/')) for e in sources)
    assert repo.guide_evidence('마그네슘 함량이 얼마인가요?')==[]

def test_guide_with_selected_product_keeps_product_specific_label_evidence():
    sources=repo.evidence('함량과 기준량의 차이가 궁금해요.',['600000147'])
    assert any(e.get('kind')=='label_guide' for e in sources)
    assert {'600000147:nutrition','600000147:intake'}<=set(e['id'] for e in sources)
    assert all(e['productId'] in (None,'600000147') for e in sources)

def test_starter_question_works_when_model_chooses_an_empty_search():
    class GuideModels:
        def __init__(self):self.calls=[]
        async def generate_content(self,**kwargs):
            self.calls.append(kwargs)
            if kwargs['config'].response_mime_type=='application/json':
                payload=json.loads(kwargs['contents'][-1].parts[0].text)
                assert any(e['id']=='label-guide:amount-and-basis' for e in payload['evidence'])
                return SimpleNamespace(text=json.dumps({'text':'함량은 표시된 분량에 들어 있는 성분의 양이고, 기준량은 그 함량을 읽는 분량 기준이에요. 영양성분 기준치는 식품을 비교하기 위한 값이에요.','citationIds':['label-guide:amount-and-basis','label-guide:daily-reference'],'productIds':[]}))
            part=types.Part.from_function_call(name='search_products',args={'query':'존재하지않는표시용어'})
            return SimpleNamespace(candidates=[SimpleNamespace(content=types.Content(role='model',parts=[part]))])
    models=GuideModels()
    result=asyncio.run(GeminiAgent(SimpleNamespace(aio=SimpleNamespace(models=models))).answer(ChatRequest(question='함량과 기준량의 차이가 궁금해요.')))
    assert result['mode']=='gemini' and result['productIds']==[]
    assert result['citations'][0]['kind']=='label_guide' and len(models.calls)==2

def test_missing_evidence_requests_clarification_but_provider_failure_stays_error(client,monkeypatch):
    import backend.main as main
    async def no_evidence(*args):raise AIError('AI_NO_EVIDENCE','제품을 선택하거나 질문을 구체적으로 적어 주세요.')
    monkeypatch.setattr(main.agent,'answer',no_evidence)
    h=headers(client)
    response=client.post('/api/chat',json={'question':'근거가 없는 질문'},headers=h)
    assert response.status_code==200 and response.json()['mode']=='insufficient'
    assert response.json()['citations']==[] and response.json()['productIds']==[]
    async def unavailable(*args):raise AIError('AI_UNAVAILABLE','AI 연결 실패')
    monkeypatch.setattr(main.agent,'answer',unavailable)
    response=client.post('/api/chat',json={'question':'근거가 없는 질문'},headers=h)
    assert response.status_code==503 and response.json()['error']['code']=='AI_UNAVAILABLE'

def test_general_guide_is_not_product_recommendation_evidence():
    sources={e['id']:e for e in repo.guide_evidence('함량과 기준량')}
    answer=AgentAnswer(text='제품 설명',citationIds=['label-guide:amount-and-basis'],productIds=[])
    with pytest.raises(AIError) as error:sanitize_answer(answer,sources,{},['600000128'])
    assert error.value.code=='AI_POLICY_MISMATCH'
    assert repo.evidence('존재하지않는자료표현')==[]
