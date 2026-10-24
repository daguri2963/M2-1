import asyncio
from copy import deepcopy
import pytest
from backend import repository as repo
from backend.agent import SupplementAgent, AIError
from backend.models import ChatRequest
from backend.product_summary import nutrition_summary, overview_requested
from backend.tests.copa_fakes import reply, client as fake_client


def test_magnesium_label_amounts_and_percentages_are_exact_not_generated():
    summary = nutrition_summary(repo.get_product('600000128'))
    assert [(n['name'], n['amount'], n['unit'], n['percent']) for n in summary['nutrients']] == [
        ('마그네슘', '315', 'mg', '100'), ('비타민D', '10', 'μg', '100')]
    assert all(n['basis'] == '1일 섭취량: 1정(1,000 mg)' for n in summary['nutrients'])
    assert '개인의 하루 필요량' in summary['notice']
    assert summary['label']['functionText'] and summary['label']['cautions'] and summary['sourceUrl']


def test_four_tablet_calcium_basis_is_not_rewritten_as_one_tablet():
    summary = nutrition_summary(repo.get_product('600000147'))
    calcium = next(n for n in summary['nutrients'] if n['name'] == '칼슘')
    assert calcium['amount'] == '700' and calcium['percent'] == '100'
    assert calcium['basis'] == '1일 섭취량: 4정(3.6 g)'


def test_missing_percent_is_not_derived_from_another_nutrient_or_zero():
    product = deepcopy(repo.get_product('600000128'))
    product['nutrients'] = [
        {'name': '미확인성분', 'amount': '2', 'operator': '<', 'unit': 'mg', 'basis': '총 내용량 20 g', 'percent': None},
        {'name': '비타민D', 'amount': '0', 'operator': '=', 'unit': 'μg', 'basis': None, 'percent': '0'},
        {'name': '칼슘', 'amount': '5', 'operator': '=', 'unit': 'mg', 'basis': None, 'percent': '미확인'}]
    nutrients = nutrition_summary(product)['nutrients']
    assert nutrients[0] == product['nutrients'][0]
    assert nutrients[1]['percent'] == '0' and nutrients[1]['basis'] is None
    assert nutrients[2]['percent'] is None
    assert product['nutrients'][2]['percent'] == '미확인'  # no mutation of source facts


@pytest.mark.parametrize('question,expected', [
    ('이 제품의 주요 성분과 기능을 설명해 주세요.', True),
    ('주성분의 함량이 궁금해요.', True),
    ('이 제품의 영양 정보를 알려 주세요.', True),
    ('이 제품의 식사·섭취 시간은 어떻게 안내되어 있나요?', False),
    ('이 제품의 보관 방법을 알려 주세요.', False),
    ('이 제품의 일반적인 주의사항은 무엇인가요?', False)])
def test_overview_does_not_replace_other_topic_answers(question, expected):
    assert overview_requested(question) == expected


class OverviewModels:
    def __init__(self, numeric=False):
        self.calls = []
        self.numeric = numeric

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if 'tools' in kwargs:
            return reply(tool='get_product_details', args={'product_id': '600000128'})
        text = '마그네슘은 몸이 에너지를 쓰고 근육과 신경이 움직이는 데 필요한 성분이에요. 비타민D는 칼슘을 활용하고 뼈를 유지하는 데 필요해요.'
        if self.numeric:
            text += ' 마그네슘은 999 mg이에요.'
        return reply({'text': text, 'citationIds': ['600000128:function'], 'productIds': []})


def test_agent_overview_adds_verified_card_and_plain_language_prompt():
    models = OverviewModels()
    result = asyncio.run(SupplementAgent(fake_client(models)).answer(ChatRequest(
        question='이 제품의 주요 성분과 기능을 설명해 주세요.', productId='600000128')))
    assert result['nutritionSummary']['productId'] == '600000128'
    assert result['nutritionSummary']['nutrients'][0]['amount'] == '315'
    assert '두세 문장' in models.calls[-1]['messages'][0]['content']
    assert '접힌 상세 영역' in models.calls[-1]['messages'][0]['content']
    assert result['toolTrace'][0]['ok']
    tool_results = [message for message in models.calls[-1]['messages'] if message['role'] == 'tool']
    assert tool_results and all('우유 함유' not in message['content'] for message in tool_results)
    assert all('cautions' not in message['content'] and 'allergen' not in message['content'] for message in tool_results)


def test_storage_answer_does_not_gain_an_unrequested_nutrition_card():
    result = asyncio.run(SupplementAgent(fake_client(OverviewModels())).answer(ChatRequest(
        question='이 제품의 보관 방법을 알려 주세요.', productId='600000128')))
    assert 'nutritionSummary' not in result


def test_numeric_card_does_not_relax_the_generated_number_guard():
    with pytest.raises(AIError, match='AI_UNSUPPORTED_CLAIM'):
        asyncio.run(SupplementAgent(fake_client(OverviewModels(numeric=True))).answer(ChatRequest(
            question='이 제품의 주요 성분과 기능을 설명해 주세요.', productId='600000128')))
