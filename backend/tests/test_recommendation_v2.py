"""Behavior checks from the agreed purpose table; never calls an external model."""
import copy,itertools,json,re
import pytest
from pydantic import ValidationError
from backend import classification as catalog,policy,repository as repo
from backend.models import INTERESTS,Survey
from backend.privacy import public_survey,public_recommendation

V='일상의 활력';B='뼈·근육 건강';G='장 건강';E='눈 건강';S='혈당 관리';W='다이어트'

def profile(*goals,**changes):
    return Survey(**{'interests':list(goals),'habits':['다양하게 먹는 편이에요'],'existing':'없어요','cautions':['해당 없어요'],'budget':'5,000원 이하','specialtyConfirmed':True,**changes})

def ids(result):return {p['id'] for p in result['products']}

def test_vitality_prioritizes_b_products_over_cheaper_magnesium_and_multi():
    r=policy.recommend(profile(V))
    assert ids(r)=={'600000129','601678603','613602132'}
    assert r['products'][0]['id']=='600000129'

def test_bone_and_muscle_subgroups_are_explained_without_duplicate_pack_sizes():
    r=policy.recommend(profile(B))
    groups={m['subgoal'] for ms in r['purposeMatches'].values() for m in ms}
    assert {'뼈 중심','근육 기능 중심'}<=groups
    assert len(ids(r)&{'600000128','600000270'})<=1

def test_gut_does_not_silently_include_glucose_or_weight_specialties():
    r=policy.recommend(profile(G))
    assert ids(r)=={'034345002','591580521','600651647'}
    assert all(not re.search('혈당|체지방',p['functionText']) for p in r['products'])

@pytest.mark.parametrize('goal',[S,W])
def test_new_specialties_need_explicit_scope_confirmation(goal):
    r=policy.recommend(profile(goal,specialtyConfirmed=False))
    assert r['status']=='insufficient' and r['nextStep']==4 and not r['products']

def test_reviewed_glucose_products_become_candidates_only_in_selected_scope():
    r=policy.recommend(profile(S))
    assert ids(r)=={'601678608','591580761','610910678'}
    assert not r['missingInterests']
    assert '591580761' not in ids(policy.recommend(profile(G)))

def test_weight_returns_one_reviewed_candidate_without_padding_or_sleep_products():
    r=policy.recommend(profile(W))
    assert r['status']=='ok' and ids(r)=={'976195543'}
    assert r['relatedProducts']==[]
    assert policy.exclusion(repo.get_product('032306284'),[W])
    assert policy.exclusion(repo.get_product('968235549'),[W])

def test_multiple_purposes_cover_available_goals_instead_of_generic_multis():
    r=policy.recommend(profile(V,B))
    assert {m['goal'] for ms in r['purposeMatches'].values() for m in ms}=={V,B}
    assert not ids(r)&{'600000135','600000283'}

def test_glucose_gut_combination_may_use_reviewed_dual_purpose_product():
    r=policy.recommend(profile(S,G))
    first=r['products'][0]['id']
    assert first in {'591580761','610910678'}
    assert {m['goal'] for m in r['purposeMatches'][first]}=={S,G}

def test_gut_weight_has_explicit_separate_coverage_not_weight_claim_for_probiotics():
    r=policy.recommend(profile(G,W))
    assert '976195543' in ids(r)
    assert all(m['goal']!=W for sku,ms in r['purposeMatches'].items() if sku!='976195543' for m in ms)

def test_family_grouping_needs_same_daily_labels_not_just_a_family_annotation():
    a=repo.get_product('600000128');b=repo.get_product('600000270')
    assert catalog.family_key(a)==catalog.family_key(b)
    changed=copy.deepcopy(b);changed['nutrients'][0]['amount']='123'
    assert catalog.family_key(a)!=catalog.family_key(changed)

@pytest.mark.parametrize('goal',[S,W])
def test_diagnosis_without_medicine_still_restricts_specialty_recommendations(goal):
    r=policy.recommend(profile(goal,cautions=['질환 진단·치료·의약품 복용 중이에요']))
    assert r['status']=='restricted' and not r['products'] and not r['relatedProducts']

@pytest.mark.parametrize('goal,existing',[(W,'968235549'),(S,'601678608')])
def test_existing_same_specialty_blocks_addition_even_with_different_ingredients(goal,existing):
    r=policy.recommend(profile(goal,existing='제품 선택',productIds=[existing]))
    assert r['status']=='restricted' and not r['products']

def test_existing_b_vitamins_cannot_be_ignored_for_new_vitality_candidates():
    r=policy.recommend(profile(V,existing='제품 선택',productIds=['600000129']))
    assert not r['products'] and r['excludedCounts']['기존 제품과 표시 성분 중복']>0

def test_preferences_never_promote_related_products_to_direct_candidates():
    r=policy.recommend(profile(V,form='필름·액상',budget='3,000원 이하'))
    assert r['status']=='empty' and not r['products']

def test_200_percent_policy_is_not_implicitly_disabled_by_new_mapping():
    assert '200%' in policy.exclusion(repo.get_product('610911093'),[V])
    assert '610911093' not in ids(policy.recommend(profile(V)))

def test_specialty_without_versioned_scope_review_stays_held(monkeypatch):
    entries=copy.deepcopy(catalog.CATALOG['entries']);entries['601678608'].pop('scopeReviewVersion')
    monkeypatch.setitem(catalog.CATALOG,'entries',entries)
    assert '검토 미완료' in policy.exclusion(repo.get_product('601678608'),[S])

@pytest.mark.parametrize('field,value',[('basis','총 포장 기준'),('operator','<'),('unit','')])
def test_unconfirmed_daily_quantities_are_not_eligible(field,value):
    p=copy.deepcopy(repo.get_product('600000129'));policy.functional(p)[0][field]=value
    assert policy.exclusion(p,[V]) is not None

def test_luteolin_is_not_a_lutein_eye_match():
    p=repo.get_product('976195543')
    assert any(n['name']=='루테올린' for n in p['nutrients'])
    assert catalog.matches_for(p,[E])==[]

@pytest.mark.parametrize('goals',[[E],['잘 모르겠어요'],[V,E],['잘 모르겠어요',S],['다양한 성분 보기']])
def test_old_or_conflicting_interest_payloads_are_rejected(goals):
    with pytest.raises(ValidationError):profile(*goals)

def test_gummy_and_chewable_are_a_distinct_preference_and_can_return_only_two():
    r=policy.recommend(profile(V,form='구미·츄어블'))
    assert ids(r)=={'601678603','613602132'}
    assert ids(policy.recommend(profile(V,form='정제·캡슐')))=={'600000129'}

def test_each_catalog_annotation_preserves_ingredient_claim_and_real_evidence_id():
    for sku,entry in catalog.CATALOG['entries'].items():
        p=repo.get_product(sku)
        assert catalog.entry_for(p)==entry
        assert all(m['evidenceId']==sku+':function' for m in entry['matches'])
    r=policy.recommend(profile(V))
    for e in r['evidence']:
        assert e['matchedClaims']==r['purposeMatches'][e['productId']]

def test_changed_label_or_wrong_ingredient_cannot_reuse_old_classification():
    p=copy.deepcopy(repo.get_product('600000129'))
    p['functionText']=p['functionText'].replace('비타민B1','비타민C')
    assert catalog.entry_for(p) is None
    assert policy.exclusion(p,[V])

def test_specialty_screening_is_not_in_provider_preferences_or_recommendation_context():
    s=profile(S)
    assert set(public_survey(s))=={'interests','budget','form'}
    r=public_recommendation(policy.recommend(s))
    assert 'specialtyConfirmed' not in json.dumps(r) and 'cautions' not in r

def test_interest_selection_order_does_not_change_selected_products():
    results=[ids(policy.recommend(profile(*goals))) for goals in itertools.permutations([V,B,G])]
    assert all(value==results[0] for value in results)

def test_five_supported_goals_have_direct_candidates_and_no_eye_annotations():
    assert INTERESTS==tuple(catalog.GOAL_DESCRIPTIONS)==(V,B,G,S,W)
    for goal in INTERESTS:
        result=policy.recommend(profile(goal))
        assert result['status']=='ok' and result['products']
        assert all(m['goal']==goal for ms in result['purposeMatches'].values() for m in ms)
    assert all(m['goal'] in INTERESTS for e in catalog.CATALOG['entries'].values() for m in e['matches'])
    assert Survey(**profile(V,B,G,S,W).model_dump()).interests==list(INTERESTS)
