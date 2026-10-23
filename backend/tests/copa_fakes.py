"""Public fixtures for the Chat Completions contract, not live model evidence."""
import json
from types import SimpleNamespace

def reply(payload=None,tool=None,args=None,finish=None,refusal=None):
    calls=[SimpleNamespace(id='call_'+tool,function=SimpleNamespace(name=tool,arguments=json.dumps(args or {})))] if tool else None
    message=SimpleNamespace(content=json.dumps(payload,ensure_ascii=False) if payload is not None else None,tool_calls=calls,refusal=refusal)
    return SimpleNamespace(choices=[SimpleNamespace(message=message,finish_reason=finish or ('tool_calls' if tool else 'stop'))])

def client(models):
    return SimpleNamespace(chat=SimpleNamespace(completions=models))
