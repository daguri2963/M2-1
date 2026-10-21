"""Local intent screening and provider payload minimization; not a universal PII detector."""
import re

PERSONAL_INFO=r'제\s*이름|주민번호|전화번호|주소는|계좌번호|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b01[016789][-\s]?\d{3,4}[-\s]?\d{4}\b|\b\d{6}[-\s]?[1-4]\d{6}\b'
HEALTH=r'임신|임산부|수유|알레르기|의약품|[가-힣]+약|약(?:과|을|은|이|랑|하고|\s)|항응고|혈압약|당뇨약|항생제|와파린|처방|진단|질환|치료|수술|신장병|신장질환|간경화|당뇨병|고혈압|혈압|혈당|혈중|검사|암\s*환자|부작용|속쓰림|두드러기|설사|복통|메스꺼|구토|어지러|속이.{0,4}(?:안좋|불편)'
DISCLOSURE=r'저는|제가|저의|나는|내가|저희|(?:^|\s)(?:나|저)(?:\s|는|가)|우리\s*(?:엄마|아빠|어머니|아버지)|제\s*(?:엄마|아빠|어머니|아버지|검사|혈압|복용)|복용\s*중|치료\s*중|먹고\s*있|먹었|먹은\s*후|먹고\s*나서|복용\s*후|진단\s*받|수술\s*예정|먹는\s*약|앓고|생겼|났어|아파|쓰려|가려워'
PERMISSION=r'먹어도|복용해도|함께\s*먹|같이\s*먹|괜찮|가능한가|추천|골라|섭취해도|안전한가'

def question_kind(text):
    if re.search(PERSONAL_INFO,text,re.I):return 'privacy'
    # General questions about these signs can be explained; active danger stays local.
    if re.search(r'숨(?:을)?\s*(?:못|쉬기\s*힘)|호흡곤란|목이?\s*붓|입술이?\s*붓|의식이?\s*없|실신',text) and not re.search(r'뜻|정의|원리|무슨\s*의미',text):return 'urgent'
    if re.search(r'증량|두\s*배|용량\s*(?:늘|줄|바꿔)|(?:하루|한번에|한\s*번에)\s*몇\s*(?:알|정|캡슐)|(?:저|나)(?:에게|한테|는)\s*.*(?:몇|얼마나)',text):return 'personal'
    if re.search(r'몇\s*(?:알|정|캡슐|mg|mcg|IU)|얼마나\s*(?:먹|복용|섭취)',text,re.I) and not re.search(r'표시|라벨|기준량|뜻|의미',text):return 'personal'
    if re.search(r'(?:같이|함께).{0,4}(?:먹|복용|섭취)|먹어도\s*(?:돼|되)|복용해도|섭취해도',text) and not re.search(r'원리|의미|일반|이유|라는\s*말',text):return 'personal'
    if re.search(HEALTH,text) and (re.search(DISCLOSURE,text) or re.search(PERMISSION,text)):return 'personal'
    if re.search(r'(?:혈중|혈압|혈당|검사\s*결과).{0,15}\d',text):return 'personal'
    if re.search(r'\d[\d,.]*\s*(?:mg|mcg|μg|ug|IU|정|알|캡슐)',text,re.I) and re.search(r'먹어도|괜찮|복용해도|충분|적당|필요',text):return 'personal'
    return 'general'

def sensitive_text(text):
    return question_kind(text)!='general'

def safe_history(history):
    """Discard unsafe turns and their following assistant; don't poison later public questions."""
    clean=[];skip_reply=True
    for message in history:
        if message.role=='user':
            skip_reply=sensitive_text(message.text)
            if not skip_reply:clean.append(message)
        elif not skip_reply and not sensitive_text(message.text):clean.append(message)
    clean=clean[-6:]
    while clean and clean[0].role!='user':clean.pop(0)
    return clean

def local_reply(kind):
    if kind=='privacy':text='개인정보가 포함되어 있어 이 질문은 AI로 보내지 않았어요. 이름·연락처·진단·개인 복용 내역을 빼고 성분이나 표시의 일반적인 궁금증을 물어봐 주세요.'
    elif kind=='urgent':text='지금 숨쉬기 어렵거나 입술·목이 붓는 등의 증상이 있다면 채팅 답변을 기다리지 말고 즉시 응급의료기관의 도움을 받으세요. 제품 포장과 섭취한 내용을 의료진에게 전달해 주세요. 이 질문은 외부 AI에 보내지 않았어요.'
    else:text='개인의 복용 가능 여부나 용량 변경은 건강 상태와 의약품 등을 확인한 전문가의 판단이 필요해요. 제품명·표시 섭취량·최근 섭취 시점·궁금한 증상을 정리해 약사나 의사에게 확인해 주세요. 실제 건강·복용 정보는 외부 AI로 보내지 않았어요. 성분의 일반적인 역할이나 주의 이유는 이어서 물어보실 수 있어요.'
    return {'mode':'restricted' if kind!='urgent' else 'urgent','text':text,'citations':[],'productIds':[],'toolTrace':[]}

def public_survey(survey):
    if not survey:return None
    return {'interests':survey.interests,'budget':survey.budget,'form':survey.form}

def public_recommendation(data):
    return {k:data[k] for k in ('status','message','products','reasons','evidence','policyVersion') if k in data}
