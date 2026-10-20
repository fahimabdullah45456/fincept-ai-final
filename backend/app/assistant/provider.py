"""Small async provider boundary. Never log prompts, response bodies or credentials."""
from dataclasses import dataclass, field
import os
from typing import Protocol
import httpx

@dataclass(frozen=True)
class ProviderConfig:
    provider: str = field(default_factory=lambda: os.getenv('AI_PROVIDER', '').strip())
    api_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', '').strip(), repr=False)
    apmix_api_key: str = field(default_factory=lambda: os.getenv('APMIX_API_KEY', '').strip(), repr=False)
    model: str = field(default_factory=lambda: os.getenv('AI_MODEL', '').strip())
    timeout_seconds: float = 25.0  # Application deadline, not a provider capability claim.
    max_output_tokens: int = 3000

@dataclass(frozen=True)
class ProviderTurn:
    content: str
    tool_calls: list[dict] = field(default_factory=list)

class ProviderError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

class Provider(Protocol):
    configured: bool
    name: str
    model: str
    async def generate(self, messages: list[dict]) -> str: ...

class OpenAIProvider:
    def __init__(self, config: ProviderConfig, transport=None):
        self.config, self.model, self.transport = config, config.model, transport
        self.name = config.provider if config.provider in ('openai', 'apmix') else 'openai'
        self.api_key = config.apmix_api_key if config.provider == 'apmix' else config.api_key
        self.endpoint = ('https://api.apmix.ai/v1/chat/completions'
                         if config.provider == 'apmix' else 'https://api.openai.com/v1/chat/completions')
        self.configured = config.provider in ('openai', 'apmix') and bool(self.api_key and config.model)

    async def generate(self, messages):
        turn=await self._generate(messages,None)
        if not turn.content:raise ProviderError('invalid_response')
        return turn.content

    async def generate_tools(self,messages,tools):
        return await self._generate(messages,tools)

    async def _generate(self, messages, tools):
        if not self.configured:
            raise ProviderError('not_configured')
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds, transport=self.transport,
                                         follow_redirects=False, trust_env=False) as client:
                # Fixed trusted provider endpoints: prompts cannot select URLs, tools or credentials.
                async with client.stream('POST', self.endpoint,
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    json={'model': self.model, 'messages': messages,
                          'max_completion_tokens': self.config.max_output_tokens, 'store': False,
                          **({'tools':tools,'tool_choice':'auto','parallel_tool_calls':False} if tools else {})}) as response:
                    if response.status_code == 429:
                        raise ProviderError('provider_rate_limit')
                    if response.status_code >= 400:
                        raise ProviderError('provider_unavailable')
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 262144:
                            raise ProviderError('invalid_response')
                    import json
                    data = json.loads(raw)
            message=data['choices'][0]['message'];text=message.get('content') or ''
            calls=message.get('tool_calls') or []
            if not isinstance(text,str) or len(text)>16000 or not isinstance(calls,list) or len(calls)>8:raise ProviderError('invalid_response')
            if calls and not tools:raise ProviderError('invalid_response')
            seen=set()
            for call in calls:
                if not isinstance(call,dict) or call.get('type')!='function':raise ProviderError('invalid_tool')
                id=call.get('id');f=call.get('function')
                if not isinstance(id,str) or not 1<=len(id)<=160 or id in seen or not isinstance(f,dict):raise ProviderError('invalid_tool')
                seen.add(id)
                if not isinstance(f.get('name'),str) or not isinstance(f.get('arguments'),str) or len(f['arguments'])>32000:raise ProviderError('invalid_tool')
                # Retain only the supported protocol fields, not arbitrary provider output.
            calls=[{'id':x['id'],'type':'function','function':{'name':x['function']['name'],'arguments':x['function']['arguments']}} for x in calls]
            if not text.strip() and not calls:raise ProviderError('invalid_response')
            return ProviderTurn(text.strip(),calls)
        except ProviderError:
            raise
        except httpx.TimeoutException:
            raise ProviderError('timeout') from None
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            raise ProviderError('provider_unavailable') from None
