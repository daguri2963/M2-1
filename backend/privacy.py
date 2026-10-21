"""Local screening and provider payload minimization; not a general-purpose PII detector."""
import re

def sensitive_text(text):
    return bool(re.search(r'임신|수유|알레르기|의약품|항응고|혈압약|당뇨약|처방|진단|질환|치료\s*중|증량|두\s*배|제\s*이름|주민번호|전화번호|신장병|간경화|당뇨병|암\s*환자|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b01[016789][-\s]?\d{3,4}[-\s]?\d{4}\b|\b\d{6}[-\s]?[1-4]\d{6}\b',text))

def public_survey(survey):
    if not survey:return None
    return {'interests':survey.interests,'budget':survey.budget,'form':survey.form}

def public_recommendation(data):
    return {k:data[k] for k in ('status','message','products','reasons','evidence','policyVersion') if k in data}
