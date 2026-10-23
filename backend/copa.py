"""Codyssey-only Chat Completions transport. No fallback to another provider."""
from urllib.parse import urlsplit
import httpx
from openai import AsyncOpenAI
from . import config


def valid_base_url(value):
    u=urlsplit(value)
    return (u.scheme=='https' and u.netloc=='copa.codyssey.kr'
            and u.path.rstrip('/')=='/v1' and not u.query and not u.fragment)


def create_client():
    # A virtual key must never be sent to the OpenAI default host or a mistyped URL.
    if not valid_base_url(config.BASE_URL):
        from .agent import AIError
        raise AIError('AI_CONFIGURATION','코디세이 API 접속 주소를 확인해야 해요.')
    return AsyncOpenAI(api_key=config.API_KEY,base_url=config.BASE_URL,
                       max_retries=0,timeout=config.AI_TIMEOUT,
                       http_client=httpx.AsyncClient(follow_redirects=False))


async def complete(client,messages,**options):
    from .agent import AIError
    response=await client.chat.completions.create(
        model=config.MODEL,messages=messages,reasoning_effort='none',
        store=False,max_completion_tokens=1800,**options)
    if not response.choices:
        raise AIError('AI_INVALID_RESPONSE','AI 답변 형식을 확인하지 못했어요.')
    choice=response.choices[0]
    if getattr(choice.message,'refusal',None) or choice.finish_reason=='content_filter':
        raise AIError('AI_REFUSED','AI가 이 질문에 답변하지 못했어요. 일반적인 성분·제품 정보로 질문해 주세요.')
    if choice.finish_reason not in ('stop','tool_calls'):
        raise AIError('AI_INVALID_RESPONSE','AI 답변이 완성되지 않았어요. 질문을 좁혀 다시 시도해 주세요.')
    return response
