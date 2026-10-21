import asyncio,json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from google.genai import types
from backend import config,knowledge,repository as repo
from backend.agent import GeminiAgent,AIError,sanitize_answer
from backend.main import app,sessions,traffic
from backend.models import ChatRequest,HistoryMessage,AgentAnswer,Survey
from backend.privacy import question_kind,safe_history

@pytest.mark.parametrize('question,expected',[
 ('영양제에도 알레르기 표시가 있나요?','knowledge:allergy'),
 ('약과 영양제의 상호작용은 무엇인가요?','knowledge:interaction'),
 ('비타민D는 왜 식사와 관련이 있나요?','knowledge:d-meal'),
 ('유산균은 무조건 냉장해야 하나요?','knowledge:pro-storage'),
 ('유산균은 균수가 많을수록 좋은가요?','knowledge:pro-cfu'),
 ('비타민B12와 활력은 어떤 관계인가요?','knowledge:b12-energy'),
 ('마그네슘의 일반적인 주의사항은 무엇인가요?','knowledge:mg-risk'),
 ('탄산칼슘과 구연산칼슘의 차이가 궁금해요.','knowledge:ca-form'),
 ('임신과 수유 때 주의하는 이유가 궁금해요.','knowledge:pregnancy'),
 ('천연이면 무조건 안전한가요?','knowledge:natural'),
 ('밥 대신 영양제로 식사를 대체할 수 있나요?','knowledge:food'),
 ('종합비타민과 단일 제품의 중복은 왜 확인하나요?','knowledge:multiple'),
])
def test_public_questions_have_relevant_evidence_not_blanket_restrictions(question,expected):
 assert question_kind(question)=='general'
 assert expected in [e['id'] for e in knowledge.search(question)]

@pytest.mark.parametrize('question,kind',[
 ('저는 알레르기가 있어요. 이 제품 먹어도 되나요?','personal'),
 ('혈압약 복용 중인데 오메가3 같이 먹어도 돼요?','personal'),
 ('임신 중 영양제를 추천해줘','personal'),
 ('하루 몇 알을 먹으면 되나요?','personal'),
 ('비타민D 4000 IU 먹어도 괜찮나요?','personal'),
 ('저는 신장질환 진단을 받았어요','personal'),
 ('비타민D 혈중 검사 결과가 나왔어요. 저는 부족한가요?','personal'),
 ('먹고 나서 두드러기가 생겼어요','personal'),
 ('저는 임산부예요. 영양제를 알고 싶어요','personal'),
 ('감기약 먹고 있는데 비타민C는 어때요?','personal'),
 ('비타민D 혈중 수치는 18입니다','personal'),
 ('몇 정 먹으면 되나요?','personal'),
 ('비타민C와 비타민D를 같이 먹어도 되나요?','personal'),
 ('영양제를 먹었는데 숨을 못 쉬겠어요','urgent'),
 ('입술이 붓고 호흡곤란이 있어요','urgent'),
 ('제 전화번호는 010-1234-5678 입니다','privacy'),
 ('test-person@example.com 으로 알려줘','privacy'),
])
def test_personal_and_urgent_input_stays_local(question,kind):
 assert question_kind(question)==kind

def test_corpus_integrity_and_every_advertised_starter_has_retrievable_evidence():
 data=knowledge.corpus()
 assert len(data['cards'])>=30 and len({c['ingredient'] for c in data['cards'] if c['ingredient']})==10
 assert len({c['id'] for c in data['cards']})==len(data['cards'])
 for c in data['cards']:
  source=data['sources'][c['sourceId']]
  assert source['url'].startswith(('https://ods.od.nih.gov/','https://www.foodsafetykorea.go.kr/'))
  assert source['checkedAt'] and source['excerpt'] and c['reviewStatus']=='source_checked'
  for question in c['questions']:
   assert c['id'] in [e['id'] for e in knowledge.search(question,limit=8)],question
 starters=json.loads((Path(__file__).resolve().parents[2]/'frontend/src/data/chat-prompts.json').read_text())
 for question in starters:
  assert question_kind(question)=='general'
  assert knowledge.search(question) or repo.guide_evidence(question)
 assert knowledge.search('오늘 서울 날씨와 주식 시세는?')==[]

def test_safe_history_removes_private_turn_and_its_reply_but_retains_later_general_context():
 history=[HistoryMessage(role='user',text='혈압약 복용 중인데 괜찮나요?'),HistoryMessage(role='assistant',text='개인 복용 내용은 외부로 보내지 않습니다.'),HistoryMessage(role='user',text='비타민D는 무슨 역할인가요?'),HistoryMessage(role='assistant',text='비타민D는 칼슘 흡수에 관여해요.')]
 clean=safe_history(history)
 assert len(clean)==2 and '혈압약' not in json.dumps([h.model_dump() for h in clean],ensure_ascii=False)
 assert '비타민D' in knowledge.context_query('그럼 식후와 어떤 관계인가요?',history)
 assert knowledge.search(knowledge.context_query('그럼 식후와 어떤 관계인가요?',history))[0]['id']=='knowledge:d-meal'
 assert safe_history([HistoryMessage(role='assistant',text='검사 결과는 개인 정보입니다.')])==[]

class KnowledgeModels:
 def __init__(self):self.calls=[]
 async def generate_content(self,**kwargs):
  self.calls.append(kwargs)
  if kwargs['config'].response_mime_type=='application/json':
   return SimpleNamespace(text=json.dumps({'text':'비타민D는 지용성 영양소예요. 지방을 조금 포함한 식사와 함께 있을 때 흡수가 더 잘 돼요.','citationIds':['knowledge:d-meal'],'productIds':[]}))
  part=types.Part.from_function_call(name='search_nutrition_knowledge',args={'query':'비타민D 식사 흡수'})
  return SimpleNamespace(candidates=[SimpleNamespace(content=types.Content(role='model',parts=[part]))])

def test_agent_uses_new_tool_and_never_sends_unsafe_history_or_survey_cautions():
 models=KnowledgeModels()
 history=[HistoryMessage(role='user',text='저는 신장질환 진단을 받았어요'),HistoryMessage(role='assistant',text='개인의 상황은 전문가에게 확인해 주세요.')]
 s=Survey(interests=['뼈·근육 건강'],habits=['다양하게 먹는 편이에요'],existing='없어요',cautions=['임신·수유 중이에요'])
 result=asyncio.run(GeminiAgent(SimpleNamespace(aio=SimpleNamespace(models=models))).answer(ChatRequest(question='비타민D와 식사의 관계가 궁금해요.',history=history,survey=s)))
 assert result['mode']=='gemini' and result['productIds']==[] and result['toolTrace'][0]['tool']=='search_nutrition_knowledge'
 for call in models.calls:
  sent=json.dumps([c.model_dump(mode='json',exclude_none=True) for c in call['contents']],ensure_ascii=False)
  assert '신장질환' not in sent and '임신·수유 중이에요' not in sent

def test_general_questions_work_with_caution_profile_but_personal_questions_never_call_agent(monkeypatch):
 import backend.main as main
 seen=[]
 async def answer(request,recommendation=None):
  seen.append(request.question)
  return {'mode':'gemini','text':'일반 안내','citations':[],'productIds':[]}
 monkeypatch.setattr(main.agent,'answer',answer)
 sessions.clear();traffic.clear()
 with TestClient(app) as c:
  token=c.post('/api/sessions',json={'adultConfirmed':True,'privacyAccepted':True,'aiAccepted':True,'version':config.CONSENT_VERSION}).json()['token']
  headers={'X-Session-Token':token}
  s={'interests':['장 건강'],'habits':['다양하게 먹는 편이에요'],'existing':'없어요','cautions':['임신·수유 중이에요']}
  r=c.post('/api/chat',headers=headers,json={'question':'영양제에도 알레르기 표시가 있나요?','survey':s})
  assert r.status_code==200 and r.json()['mode']=='gemini'
  for question in ('임신 중 영양제를 추천해줘','제 전화번호는 010-1234-5678 입니다','숨을 못 쉬겠어요'):
   r=c.post('/api/chat',headers=headers,json={'question':question})
   assert r.status_code==200 and r.json()['mode'] in ('restricted','urgent')
  assert seen==['영양제에도 알레르기 표시가 있나요?']
  assert c.post('/api/chat',headers=headers,json={'question':'비타민D 역할의 공식 근거를 찾아주세요.'}).json()['mode']=='gemini'

@pytest.mark.parametrize('text',[
 '하루 99 mg을 먹으면 됩니다.',
 '하루에 두 알이면 충분해요.',
 '이 영양제는 암을 치료합니다.',
 '저는 약사입니다.',
 '의사로서 설명할게요.',
 '의약품과 함께 먹어도 안전해요.',
])
def test_unsupported_dose_cure_and_professional_identity_are_rejected(text):
 with pytest.raises(AIError):sanitize_answer(AgentAnswer(text=text,citationIds=['knowledge:d-meal']),{'knowledge:d-meal':{}},{})

def test_ingredient_name_digits_are_not_confused_with_dose_instructions():
 result=sanitize_answer(AgentAnswer(text='비타민B12와 오메가3는 서로 다른 성분이에요.',citationIds=['valid']),{'valid':{}},{})
 assert 'B12' in result['text']
