"""Comparison explanation contract: actual labels, isolated failures and bounded reuse."""
import asyncio
import copy
import json
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from backend import comparison as c, config, repository as repo
from backend.agent import AIError
from backend.main import app
from backend.tests.copa_fakes import reply, client

PAIR=['600000128','600000270']

def answer():
    return {'summary':{'text':'두 제품은 주요 표시 성분이 같고 포장 규격에 차이가 있어요.','factIds':['composition','package']},
        'highlights':[{'factId':'package','text':'같은 성분을 살펴보되 포장 규격을 구분해 보세요.'},{'factId':'price','text':'관찰 당시 단품 가격을 함께 확인해 보세요.'}],
        'selectionGuide':{'text':'주요 성분과 표시 섭취방법을 확인한 뒤 포장 규격과 관찰 가격을 비교해 보세요.','factIds':['composition','intake','package','price']}}

class Responses:
    def __init__(self,payload=None):self.calls=[];self.payload=payload or answer()
    async def create(self,**kwargs):
        self.calls.append(kwargs)
        return reply(self.payload)

def explainer(responses):
    return c.ComparisonExplainer(SimpleNamespace(client=client(responses),configured=lambda:True,semaphore=asyncio.Semaphore(2)))


def test_same_formula_pack_sizes_have_real_sources_and_equal_daily_quantities():
    context=c.comparison_facts(PAIR)
    facts={f['id']:f for f in context['facts']}
    assert not facts['composition']['different'] and facts['package']['different']
    assert facts['nutrient:마그네슘']['comparable'] and facts['nutrient:마그네슘']['direction']=='equal'
    sources={s['id']:s for s in context['sources']}
    for f in facts.values():
        assert {sources[s]['productId'] for s in f['citationIds']}==set(PAIR)
    assert all(s['url'].startswith('https://') for s in context['sources'])

@pytest.mark.parametrize('field,value',[('basis','총 포장 기준'),('unit','IU'),('operator','<'),('amount','미확인')])
def test_unknown_or_mismatched_quantity_never_gets_a_higher_claim(monkeypatch,field,value):
    ps=copy.deepcopy(repo.get_many(PAIR))
    next(n for n in ps[1]['nutrients'] if n['name']=='마그네슘')[field]=value
    monkeypatch.setattr(c.repo,'get_many',lambda ids:ps)
    fact=next(f for f in c.comparison_facts(PAIR)['facts'] if f['id']=='nutrient:마그네슘')
    assert not fact['comparable'] and fact['direction'] is None


def test_ingredient_missing_from_one_label_is_not_zero():
    f=next(f for f in c.comparison_facts(['600000129','600000128'])['facts'] if f['id']=='nutrient:비타민B1')
    assert f['values'][1]=='표시 정량 없음' and not f['comparable']
    assert '0이 아니에요' in f['notice']

@pytest.mark.parametrize('text',['제품 A는 300 mg이에요.','제품 A가 더 좋아요.','제품 A를 추천해요.','함께 먹어도 괜찮아요.','제품 A에는 이 성분이 없어요.','내용물 차이는 거의 없습니다.'])
def test_unverified_numbers_and_personal_or_absence_claims_are_rejected(text):
    payload=answer();payload['summary']['text']=text
    with pytest.raises(AIError):c.validate_answer(c.ComparisonAnswer(**payload),c.comparison_facts(PAIR))


def test_foreign_fact_and_duplicate_highlights_rejected():
    payload=answer();payload['summary']['factIds']=['other-product:fact']
    with pytest.raises(AIError):c.validate_answer(c.ComparisonAnswer(**payload),c.comparison_facts(PAIR))
    payload=answer();payload['highlights']*=2
    with pytest.raises(ValueError):c.ComparisonAnswer(**payload)


def test_cache_uses_order_data_model_and_expiry_without_survey_data(monkeypatch):
    async def run():
        responses=Responses();e=explainer(responses)
        assert not (await e.explain(PAIR))['cached']
        assert (await e.explain(PAIR))['cached'] and len(responses.calls)==1
        await e.explain(list(reversed(PAIR)))
        assert len(responses.calls)==2
        key=next(reversed(e.cache));_,value=e.cache[key];e.cache[key]=(0,value)
        await e.explain(list(reversed(PAIR)))
        assert len(responses.calls)==3
        monkeypatch.setattr(config,'MODEL','test-new-model')
        await e.explain(PAIR)
        assert len(responses.calls)==4
        content=json.loads(responses.calls[0]['messages'][1]['content'])
        assert set(content)=={'comparison','responseSchema'}
        assert set(content['comparison'])=={'version','products','productIds','facts','sources'}
        assert responses.calls[0]['store'] is False and 'response_format' not in responses.calls[0]
        await e.close()
    asyncio.run(run())


def test_source_change_invalidates_cached_result(monkeypatch):
    async def run():
        responses=Responses();e=explainer(responses)
        context=c.comparison_facts(PAIR)
        monkeypatch.setattr(c,'comparison_facts',lambda ids:copy.deepcopy(context))
        await e.explain(PAIR)
        context['sources'][0]['observedAt']='2099-01-01'
        await e.explain(PAIR)
        assert len(responses.calls)==2
        await e.close()
    asyncio.run(run())


def test_concurrent_same_pair_shares_one_call_and_disconnected_waiter_is_safe():
    async def run():
        started=asyncio.Event();release=asyncio.Event()
        class Slow(Responses):
            async def create(self,**kwargs):
                self.calls.append(kwargs);started.set();await release.wait();return reply(answer())
        responses=Slow();e=explainer(responses)
        first=asyncio.create_task(e.explain(PAIR));await started.wait()
        second=asyncio.create_task(e.explain(PAIR));first.cancel()
        with pytest.raises(asyncio.CancelledError):await first
        release.set();result=await second
        assert result['mode']=='ai' and len(responses.calls)==1
        assert (await e.explain(PAIR))['cached']
        await e.close()
    asyncio.run(run())


def test_failed_ai_is_not_cached_and_can_be_retried():
    async def run():
        responses=Responses({'unexpected':'shape'});e=explainer(responses)
        with pytest.raises(AIError):await e.explain(PAIR)
        assert not e.cache
        responses.payload=answer()
        assert (await e.explain(PAIR))['mode']=='ai' and len(responses.calls)==2
        e.max_entries=1
        await e.explain(list(reversed(PAIR)))
        assert len(e.cache)==1
        await e.close()
    asyncio.run(run())


def test_ai_timeout_does_not_poison_capacity_or_cache(monkeypatch):
    async def run():
        class Timeout(Responses):
            async def create(self,**kwargs):raise asyncio.TimeoutError()
        e=explainer(Timeout())
        with pytest.raises(AIError) as error:await e.explain(PAIR)
        assert error.value.code=='AI_TIMEOUT' and e.agent.semaphore._value==2 and not e.cache
        await e.close()
    asyncio.run(run())


def test_compare_table_public_but_explanation_requires_consent_and_exact_pair(monkeypatch):
    import backend.main as main
    responses=Responses();e=explainer(responses)
    monkeypatch.setattr(main,'comparison_explainer',e)
    with TestClient(app) as browser:
        assert browser.post('/api/compare',json={'productIds':PAIR}).status_code==200
        assert browser.post('/api/compare/explanation',json={'productIds':PAIR}).status_code==401
        assert not responses.calls
        consent=browser.post('/api/sessions',json={'provider':'codyssey','adultConfirmed':True,'privacyAccepted':True,'aiAccepted':True,'version':config.CONSENT_VERSION})
        headers={'X-Session-Token':consent.json()['token']}
        for ids,status in [([PAIR[0]],422),([PAIR[0]]*2,422),([PAIR[0],'600651654'],404)]:
            assert browser.post('/api/compare/explanation',json={'productIds':ids},headers=headers).status_code==status
        assert not responses.calls
        result=browser.post('/api/compare/explanation',json={'productIds':PAIR},headers=headers)
        assert result.status_code==200 and result.json()['productIds']==PAIR
        assert {e['productId'] for e in result.json()['citations']}==set(PAIR)
        assert browser.post('/api/compare/explanation',json={'productIds':PAIR,'survey':{}},headers=headers).status_code==422
        browser.delete('/api/sessions/current',headers=headers)
        assert browser.post('/api/compare/explanation',json={'productIds':PAIR},headers=headers).status_code==401
        assert browser.post('/api/compare',json={'productIds':PAIR}).status_code==200

def test_incomparable_nutrient_cannot_support_a_higher_amount_claim():
    context=c.comparison_facts(['600000129','600000128'])
    payload=answer();payload['highlights']=[{'factId':'nutrient:비타민B1','text':'제품 A의 함량이 높아요.'}]
    with pytest.raises(AIError):c.validate_answer(c.ComparisonAnswer(**payload),context)

@pytest.mark.parametrize('status,expected',[(429,'AI_RATE_LIMIT'),(401,'AI_CONFIGURATION'),(500,'AI_UNAVAILABLE')])
def test_provider_failure_is_sanitized_and_does_not_disable_public_table(status,expected):
    async def run():
        class Failed(Responses):
            async def create(self,**kwargs):
                error=RuntimeError('private provider error must not be exposed');error.status_code=status;raise error
        e=explainer(Failed())
        with pytest.raises(AIError) as caught:await e.explain(PAIR)
        assert caught.value.code==expected and 'private' not in caught.value.message
        assert repo.compare(PAIR)['rows'] and not e.cache
        await e.close()
    asyncio.run(run())
