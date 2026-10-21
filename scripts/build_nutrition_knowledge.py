"""Build reviewed educational knowledge. Edit summaries only after checking primary sources."""
import hashlib,json
from pathlib import Path

DATE='2026-10-21'
SOURCES={}
def source(key,title,slug,excerpt,publisher='NIH ODS'):
    url=slug if slug.startswith('https://') else 'https://ods.od.nih.gov/factsheets/'+slug+'-Consumer/'
    SOURCES[key]={'title':title,'publisher':publisher,'url':url,'checkedAt':DATE,'updatedAt':None,'reviewStatus':'agent_source_checked','reviewMethod':'Primary-source text read using web tools; Korean summary compared to the named sections. Not independent clinical review.','excerpt':excerpt,'excerptSha256':hashlib.sha256(excerpt.encode()).hexdigest(),'scope':'General education only. US numeric intake standards and clinical dosing are not imported.'}
source('general','Dietary Supplements: What You Need to Know','WYNTK','However, supplements can’t take the place of the variety of foods that are important to a healthy eating routine.')
source('c','Vitamin C','VitaminC','Vitamin C, also known as ascorbic acid, is a water-soluble nutrient found in some foods.')
source('d','Vitamin D','VitaminD','Because vitamin D is fat soluble, it is best absorbed when taken with a meal or snack that includes some fat.')
source('b12','Vitamin B12','VitaminB12','Vitamin B12 doesn’t provide these benefits in people who get enough B12 from their diet.')
source('e','Vitamin E','VitaminE','Vitamin E is a fat-soluble nutrient found in many foods.')
source('calcium','Calcium','Calcium','Calcium carbonate is absorbed best when taken with food.')
source('magnesium','Magnesium','Magnesium','High intakes of magnesium from dietary supplements and medications can cause diarrhea, nausea, and abdominal cramping.')
source('zinc','Zinc','Zinc','Your body also uses zinc to make DNA (the genetic material in cells) and proteins.')
source('iron','Iron','Iron','Your body uses iron to make hemoglobin, a protein in red blood cells that carries oxygen from the lungs')
source('omega3','Omega-3 Fatty Acids','Omega3FattyAcids','DHA and EPA are found in fish and other seafood.')
source('probiotics','Probiotics','Probiotics','Higher CFU counts alone do not necessarily mean that the product has greater health benefits.')
source('korea','건강기능식품 정보 · 안전한 섭취방법','https://www.foodsafetykorea.go.kr/portal/board/boardDetail.do?bbs_no=bbs464&menu_grp=MENU_NEW01&menu_no=3811&ntctxt_no=1070219','건강기능식품은 일반식품과 달리 섭취량과 섭취방법이 정해져 있으므로 반드시 확인하고 이를 지켜야 합니다.','식품안전나라')

CARDS=[]
def card(key,title,summary,source_id,tags,questions,ingredient='',topic='basics'):
    CARDS.append({'id':'knowledge:'+key,'title':title,'text':summary,'sourceId':source_id,'tags':tags.split('|'),'questions':questions.split('|'),'ingredient':ingredient,'topic':topic,'reviewStatus':'source_checked','scope':'일반 성인의 영양 정보. 개인 진단·복용 가능 여부·용량 처방에 적용하지 않음.'})

card('purpose','영양제는 어떤 역할을 하나요?','영양제는 식사로 섭취하는 영양을 보충하는 데 쓰인다. 모든 사람이 모든 성분을 추가로 섭취해야 한다는 뜻은 아니다.','general','영양제란|영양제역할|처음|시작|필수|꼭먹|누구나','영양제를 처음 알아보는데 어떤 역할을 하나요?|영양제는 누구나 꼭 먹어야 하나요?')
card('food','영양제로 식사를 대신할 수 있나요?','다양한 식품은 영양소와 식이섬유 등을 제공한다. 영양제는 다양하고 균형 잡힌 식사의 대체품이 아니다.','general','식사대신|밥대신|식단|음식|균형|불규칙|채소|식습관|밥|대신','밥을 잘 못 먹으면 영양제로 대신해도 되나요?|식습관과 영양제는 어떤 관계인가요?')
card('medicine','건강기능식품과 의약품','건강기능식품에는 표시된 기능과 섭취방법이 있다. 질병 치료를 목적으로 사용하는 의약품과 구별하며, 치료 약을 영양제로 바꾸는 근거가 되지 않는다.','korea','의약품차이|약차이|의약품이란|건강기능식품|치료약대신','건강기능식품과 약은 어떻게 다른가요?')
card('more','많이 섭취하면 더 좋은가요?','필요 이상으로 섭취한다고 이점이 커지는 것은 아니며, 고함량이나 여러 제품의 병용은 이상반응 가능성을 높일 수 있다. 제품 표시량을 임의로 늘리는 근거로 사용하지 않는다.','general','많이|고함량|메가도스|과다|많을수록|높을수록|고용량','함량이 높을수록 좋은 제품인가요?|메가도스가 무슨 뜻인가요?')
card('natural','천연이면 안전한가요?','천연이라는 표현만으로 안전성을 판단할 수 없다. 성분의 성질, 사용량, 제조와 사용 조건 등도 중요하다.','general','천연|자연유래|합성|안전성','천연 영양제는 무조건 안전한가요?')
card('interaction','약과 영양제의 상호작용','상호작용은 성분이 의약품의 흡수나 작용 등에 영향을 줄 수 있다는 뜻이다. 예로 비타민K는 와파린의 작용에 영향을 줄 수 있다. 일반 원리 설명이며 개인의 병용 가능 여부는 확인하지 않는다.','general','상호작용|약과|의약품|병용|항생제|와파린|혈압약|비타민k','약과 영양제가 상호작용한다는 게 무슨 뜻인가요?|와파린과 비타민K의 상호작용 원리가 궁금해요.','', 'interaction')
card('allergy','알레르기 표시는 왜 확인하나요?','원료의 특성이나 알레르기 등으로 섭취 시 주의가 필요한 경우가 있다. 원재료와 주의사항을 확인하며, 표시 일부만으로 개인의 알레르기 안전성을 확정하지 않는다.','korea','알레르기|알러지|원재료|교차오염','영양제에도 알레르기 표시가 있나요?|원재료와 주의사항은 왜 확인하나요?','', 'caution')
card('pregnancy','임신·수유 때 주의가 필요한 이유','임신·수유 등에서는 성분별 주의가 필요할 수 있으며 안전성 검토가 충분하지 않은 보충제도 있다. 일반 성인 제품 정보를 개인에게 그대로 적용하는 근거가 되지 않는다.','general','임신|수유|임산부','임신과 수유 때 영양제에 더 주의하는 이유가 궁금해요.','', 'caution')
card('symptoms','증상만으로 결핍을 알 수 있나요?','영양 상태와 보충제 필요 여부는 건강 상태 등을 함께 확인해야 한다. 피로 등 한 가지 증상이나 식습관만으로 특정 영양소 결핍을 확정하지 않는다.','general','피로|결핍|부족|눈떨림|증상','피곤하면 무조건 영양소가 부족한가요?|눈 떨림만으로 마그네슘 부족을 알 수 있나요?','', 'evidence')
card('evidence','효과 근거는 모두 같은가요?','일부 용도의 근거와 달리 추가 연구가 필요한 보충제도 있다. 알려진 영양소의 역할이 모든 보충제 제품의 효과 보장을 의미하지 않는다.','general','효과|근거|연구|보장|얼마나먹|효과없|체감','영양제 효과는 어떻게 판단하나요?|먹자마자 효과를 느껴야 하나요?','', 'evidence')
card('multiple','여러 제품을 고를 때 확인할 점','여러 보충제와 강화식품을 통해 같은 성분을 예상보다 많이 섭취할 수 있다. 성분과 표시량의 중복을 확인해야 하며 중복이 없다는 사실이 병용 안전을 보장하지 않는다.','general','여러|중복|종합비타민|멀티비타민|겹치|동시에','종합비타민과 단일 영양제는 무엇을 비교하나요?|여러 영양제의 중복 성분을 왜 확인하나요?','', 'overlap')
card('consult','약사에게 무엇을 확인하면 좋을까요?','사용 중인 영양제와 의약품의 이름, 섭취량과 빈도, 섭취 이유를 정리하면 전문가와 상의할 때 도움이 된다. 이 기록은 이 사이트나 외부 AI에 제출하는 대신 전문가에게 직접 전달한다.','general','약사|상담|의사|준비|확인할점','약사에게 영양제를 물어볼 때 무엇을 준비하면 좋을까요?')
card('timing','공복·식후·섭취 시간','섭취방법은 제품과 성분의 특성에 따라 확인한다. 모든 영양제에 공통으로 적용되는 아침·저녁 또는 공복 규칙을 임의로 정하지 않는다. 구체적인 제품은 표시 섭취방법을 우선 확인한다.','korea','공복|식전|식후|시간|아침|저녁|밤|언제|커피|빼먹|잊었','영양제는 아침과 저녁 중 언제 먹는 게 좋나요?|공복과 식후 중 무엇을 확인해야 하나요?|하루 빼먹었다면 어떤 정보를 확인해야 하나요?','', 'timing')

card('c-role','비타민C의 역할','비타민C는 수용성 영양소로 항산화 작용과 콜라겐 형성에 필요하며 식물성 식품의 철 흡수를 돕는다. 이 역할을 질병 치료나 개인별 보충제 필요량으로 해석하지 않는다.','c','비타민c|비타민씨|아스코르빈산','비타민C는 무슨 역할을 하나요?','c')
card('d-role','비타민D의 역할','비타민D는 칼슘 흡수와 뼈 건강에 관여하고 근육·신경·면역 기능에도 필요하다. 개인의 부족 여부는 실내 생활이나 증상만으로 확정할 수 없다.','d','비타민d|비타민디|지용성','비타민D는 왜 필요한가요?','d')
card('b12-role','비타민B12의 역할','비타민B12는 혈액과 신경 세포의 건강, DNA 형성 등에 필요하다. 동물성 식품과 일부 강화식품에 들어 있다.','b12','비타민b12|b12|비타민비12|채식|비건','비타민B12는 무슨 역할을 하나요?|채식 식단에서 B12는 어떤 식품을 확인하나요?','b12')
card('e-role','비타민E의 역할','비타민E는 지용성 영양소로 항산화 작용을 하며 면역 기능 등에 관여한다. 식물성 기름·견과류·씨앗 등에 들어 있다.','e','비타민e|비타민이|항산화','비타민E와 항산화가 무엇인지 궁금해요.','e')
card('ca-role','칼슘의 역할','칼슘은 뼈와 치아의 구조를 유지하고 근육·신경 기능 등에도 필요하다. 식품과 영양제를 통한 섭취를 함께 고려해야 한다.','calcium','칼슘|calcium','칼슘은 뼈 이외에도 역할이 있나요?','calcium')
card('mg-role','마그네슘의 역할','마그네슘은 근육과 신경의 기능, 단백질과 뼈 형성 등 여러 과정에 관여하는 무기질이다. 특정 증상만으로 결핍이나 보충제 효과를 판단하지 않는다.','magnesium','마그네슘|magnesium','마그네슘은 무슨 역할을 하나요?','magnesium')
card('zn-role','아연의 역할','아연은 면역 기능, DNA와 단백질 형성, 상처 회복과 미각 등에 필요하다. 기본적인 영양소 역할이 감염 예방이나 치료 효과를 보장하지 않는다.','zinc','아연|zinc','아연은 어떤 영양소인가요?','zinc')
card('fe-role','철의 역할','철은 산소를 운반하는 헤모글로빈과 근육에 산소를 공급하는 미오글로빈을 만드는 데 필요하다. 피곤함만으로 철 결핍을 판단하지 않는다.','iron','철분|철영양제|헤모글로빈|iron','철분과 헤모글로빈은 어떤 관계인가요?','iron')
card('omega-role','오메가3의 종류','오메가3 지방산에는 ALA, EPA, DHA 등이 있다. ALA는 식물성 기름 등에, EPA와 DHA는 생선과 해산물 등에 들어 있다. 원료유 전체와 표시된 성분을 구별해 확인한다.','omega3','오메가3|오메가-3|epa|dha|어유','오메가3의 EPA와 DHA는 무엇인가요?','omega3')
card('pro-role','프로바이오틱스란?','프로바이오틱스는 적절한 양에서 건강상 이점을 줄 수 있는 살아 있는 미생물이다. 주로 소화관에서 작용하며 균의 종류와 균주에 따라 연구 결과가 다를 수 있다. 모든 발효식품의 미생물에 건강상 이점이 입증된 것은 아니다.','probiotics','유산균|프로바이오틱스|probiotic','유산균과 프로바이오틱스가 궁금해요.','probiotics')

card('d-meal','비타민D와 식사','비타민D는 지용성이므로 지방을 조금 포함한 식사나 간식과 함께 있을 때 흡수가 더 잘 된다. 특정 개인의 복용 시간표나 용량 변경 지시는 제공하지 않는다.','d','식사|식후|공복|흡수|지용성|언제','비타민D와 식사의 관계가 궁금해요.','d','timing')
card('ca-form','탄산칼슘과 구연산칼슘','탄산칼슘은 음식과 함께 있을 때 흡수가 더 잘 되고, 구연산칼슘은 공복 또는 식사 상태에서 흡수될 수 있다. 같은 칼슘이라도 원료 형태와 제품 표시를 확인해야 한다.','calcium','탄산|구연산|식사|식후|공복|흡수|형태','탄산칼슘과 구연산칼슘은 어떻게 다른가요?','calcium','timing')
card('b12-energy','B12와 피로·활력 광고','식사로 충분한 B12를 섭취하는 사람에서 B12 보충제가 에너지나 지구력을 높인다는 근거는 없다. 피로의 원인을 단순히 B12 부족으로 단정하지 않는다.','b12','피로|활력|에너지|지구력|효과','비타민B12를 먹으면 무조건 활력이 생기나요?','b12','evidence')
card('c-risk','비타민C를 많이 섭취할 때','비타민C를 과량 섭취하면 설사·메스꺼움·복부 경련 등이 생길 수 있다. 수용성이라는 이유로 고함량을 무제한 섭취해도 된다는 뜻은 아니다.','c','과량|고함량|메가도스|설사|부작용|주의|수용성','수용성 비타민C는 많이 먹어도 괜찮다는 말이 맞나요?','c','caution')
card('mg-risk','마그네슘과 일반 주의정보','보충제·의약품을 통한 마그네슘의 높은 섭취는 설사·메스꺼움·복부 경련 등을 일으킬 수 있다. 일부 의약품의 흡수에도 영향을 줄 수 있어 개인별 병용 판단은 전문가 확인이 필요하다.','magnesium','과량|설사|부작용|주의|약|항생제|상호작용','마그네슘의 일반적인 주의사항은 무엇인가요?','magnesium','caution')
card('zinc-risk','아연 과량 섭취의 주의점','아연을 지나치게 섭취하면 메스꺼움 등 문제가 생길 수 있고, 장기간 높은 섭취는 구리 수준 등에 영향을 줄 수 있다. 개인의 안전 용량이나 섭취 기간을 이 정보로 정하지 않는다.','zinc','과량|장기간|구리|부작용|주의|고함량','아연을 과량 섭취할 때 왜 주의해야 하나요?','zinc','caution')
card('pro-cfu','유산균 수와 균주','CFU는 살아 있는 미생물 수를 나타내는 지표다. CFU가 높다는 것만으로 이점이 더 크다고 볼 수 없으며, 균의 종류·균주와 연구된 용도를 함께 살펴야 한다.','probiotics','cfu|균수|균주|많을수록|고함량|고르는','유산균은 균수가 많을수록 좋은가요?','probiotics','evidence')
card('pro-storage','유산균 보관과 사용기한','프로바이오틱스는 냉장이 필요한 제품과 실온 보관 가능한 제품이 있다. 제품의 보관방법과 소비기한을 확인하며, 제조 시점 균수와 사용기한까지의 균수 보장은 다를 수 있다.','probiotics','냉장|보관|실온|소비기한|유통기한|제조','유산균은 무조건 냉장 보관해야 하나요?|유산균 제품의 소비기한은 왜 중요한가요?','probiotics','storage')
card('iron-food','철과 식품의 관계','식품에는 헴철과 비헴철이 있으며 비타민C는 식물성 식품의 철 흡수를 돕는다. 이 원리는 개인에게 두 보충제를 함께 사용하라는 지시가 아니다.','iron','철분|흡수|식물|음식|비타민c','식물성 식품의 철과 비타민C는 어떤 관계인가요?','iron','timing')
card('long-term','오래 섭취할 때 확인할 정보','건강기능식품은 표시 섭취량과 주의사항을 확인해야 한다. 모든 제품에 적용되는 휴약 기간이나 복용 기간을 임의로 정하지 않고, 개인의 필요·복용 상황은 전문가에게 확인한다.','korea','오래|장기|계속|휴약|기간|몇달','영양제를 오래 먹을 때 어떤 정보를 확인해야 하나요?','', 'caution')


card('water-soluble','수용성이란 무엇인가요?','비타민C는 물에 녹는 수용성 영양소다. 수용성이라는 성질만으로 고함량을 무제한 섭취해도 된다고 판단하지 않는다.','c','수용성|물에녹|물에잘|지용성과|비타민종류','수용성과 지용성 비타민의 차이가 궁금해요.|수용성이라는 말은 무슨 뜻인가요?')
card('fat-soluble','지용성이란 무엇인가요?','비타민D는 지방에 녹는 지용성 영양소이며 지방을 포함한 식사와 흡수가 관련된다. 성분의 성질과 개별 제품의 표시 섭취방법을 함께 구별해서 확인한다.','d','지용성|기름에녹|지방에녹|수용성과','수용성과 지용성 비타민의 차이가 궁금해요.|지용성이면 식사와 관련이 있나요?')

if __name__=='__main__':
    assert len(CARDS)>=30 and len({c['ingredient'] for c in CARDS if c['ingredient']})==10
    result={'version':'2026-10-21.1','sources':SOURCES,'cards':CARDS}
    path=Path(__file__).resolve().parents[1]/'backend/nutrition-knowledge.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'sources':len(SOURCES),'knowledgeCards':len(CARDS),'exampleQuestions':len({q for c in CARDS for q in c['questions']}),'ingredients':10}))
