import asyncio
import secrets
import time
from collections import defaultdict,deque
from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends,HTTPException,Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from . import config,policy,repository as repo
from .agent import GeminiAgent,AIError
from .models import Consent,Survey,Selection,OverlapRequest,ChatRequest
from .privacy import question_kind,local_reply

agent=GeminiAgent()
sessions={}
traffic=defaultdict(deque)

@asynccontextmanager
async def lifespan(app):
    repo.list_products()  # Fail startup if the reviewed DB cannot be opened.
    yield
    await agent.close()

app=FastAPI(title='영양제 첫걸음 API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=config.ORIGINS,allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type','X-Session-Token'])

@app.middleware('http')
async def privacy_headers(request,call_next):
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response

@app.exception_handler(RequestValidationError)
async def invalid_input(request,error):
    return JSONResponse(status_code=422,content={'error':{'code':'INVALID_INPUT','message':'입력 항목을 확인해 주세요. 허용된 선택지와 제품만 사용할 수 있어요.'}})

@app.exception_handler(HTTPException)
async def http_error(request,error):
    detail=error.detail if isinstance(error.detail,dict) else {'code':'REQUEST_ERROR','message':str(error.detail)}
    return JSONResponse(status_code=error.status_code,content={'error':detail})

@app.exception_handler(LookupError)
async def not_found(request,error):
    return JSONResponse(status_code=404,content={'error':{'code':'PRODUCT_NOT_FOUND','message':'검수 완료 제품을 찾을 수 없어요. 보류 제품은 조회 대상에서 제외합니다.'}})

@app.exception_handler(AIError)
async def ai_error(request,error):
    return JSONResponse(status_code=error.status,content={'error':{'code':error.code,'message':error.message}})

def session(request:Request):
    now=time.monotonic()
    for token,expiry in list(sessions.items()):
        if expiry<=now:
            sessions.pop(token,None);traffic.pop(token,None)
    token=request.headers.get('X-Session-Token','')
    if token not in sessions:raise HTTPException(401,{'code':'CONSENT_REQUIRED','message':'이용 동의를 다시 확인해 주세요. 임시 연결은 일정 시간이 지나면 종료돼요.'})
    return token

def rate_limit(token):
    now=time.monotonic();queue=traffic[token]
    while queue and queue[0]<now-60:queue.popleft()
    if len(queue)>=10:raise HTTPException(429,{'code':'TOO_MANY_REQUESTS','message':'요청이 많아요. 잠시 후 다시 시도해 주세요.'})
    queue.append(now)

@app.get('/api/health')
def health():
    return {'ready':True,'aiConfigured':agent.configured(),'consentVersion':config.CONSENT_VERSION,'policyVersion':config.POLICY_VERSION}

@app.post('/api/sessions')
def create_session(consent:Consent):
    if consent.version!=config.CONSENT_VERSION or not all([consent.adultConfirmed,consent.privacyAccepted,consent.aiAccepted]):
        raise HTTPException(400,{'code':'CONSENT_REQUIRED','message':'성인 이용과 정보 처리·AI 전송 안내에 동의해야 진행할 수 있어요.'})
    now=time.monotonic()
    for token,expiry in list(sessions.items()):
        if expiry<=now:sessions.pop(token,None);traffic.pop(token,None)
    if len(sessions)>=1000:raise HTTPException(503,{'code':'SESSION_CAPACITY','message':'접속이 많아요. 잠시 후 다시 시도해 주세요.'})
    token=secrets.token_urlsafe(32);sessions[token]=now+config.SESSION_TTL
    return {'token':token,'expiresIn':config.SESSION_TTL,'consentVersion':config.CONSENT_VERSION}

@app.delete('/api/sessions/current')
def delete_session(token=Depends(session)):
    sessions.pop(token,None);traffic.pop(token,None)
    return {'deleted':True}

@app.get('/api/products')
def products():return {'products':repo.list_products()}

@app.get('/api/products/{product_id}')
def product_detail(product_id:str):return repo.get_product(product_id)

@app.post('/api/compare')
def compare(request:Selection):return repo.compare(request.productIds)

@app.post('/api/overlap')
def overlap(request:OverlapRequest,token=Depends(session)):
    return policy.overlap(request.productIds)

@app.post('/api/recommendations')
async def recommendations(survey:Survey,token=Depends(session)):
    rate_limit(token)
    result=await asyncio.to_thread(policy.recommend,survey)
    result['ai']={'mode':'not_requested'}
    if result['status']=='ok':
        try:
            reply=await agent.answer(ChatRequest(question='이 후보가 설문 조건과 연결되는 이유와 확인할 점을 설명해 주세요.',survey=survey),result)
            result['ai']=reply
        except AIError as error:
            result['ai']={'mode':'unavailable','code':error.code,'message':error.message}
    return result

@app.post('/api/chat')
async def chat(request:ChatRequest,token=Depends(session)):
    import re
    rate_limit(token)
    if request.productId:repo.get_product(request.productId)
    if request.survey:repo.get_many(request.survey.productIds)
    kind=question_kind(request.question)
    if kind!='general':return local_reply(kind)
    wants_recommendation=re.search(r'(?:추천|골라|선택해).*(?:줘|주세요)|(?:저|나)(?:에게|한테|는).*(?:추천|골라)|^\s*추천(?:해|요|부탁)?[.!?\s]*$',request.question)
    if wants_recommendation and not request.survey:
        return {'mode':'insufficient','text':'추천받기 설문에서 관심 분야·기존 제품·주의조건을 먼저 확인해 주세요. 확인하지 않은 조건으로 개인 후보를 고르지 않습니다.','citations':[],'productIds':[],'toolTrace':[]}
    recommendation=policy.recommend(request.survey) if request.survey and wants_recommendation else None
    if recommendation and recommendation['status']!='ok':
        return {'mode':recommendation['status'],'text':recommendation['message'],'citations':recommendation['evidence'],'productIds':[],'toolTrace':[]}
    try:
        return await agent.answer(request,recommendation)
    except AIError as error:
        if error.code!='AI_NO_EVIDENCE':raise
        return {'mode':'insufficient','text':error.message,'citations':[],'productIds':[],'toolTrace':[]}
