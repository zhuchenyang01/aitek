import json
from typing import Any, Iterator

import httpx


class LLMClient:
    def __init__(self, api_key='', base_url=None, model=None, timeout=120.0):
        self.api_key = api_key or ''
        self.base_url = (base_url or 'https://api.deepseek.com/v1').rstrip('/')
        self.model = model or 'deepseek-chat'
        self.timeout = float(timeout or 120)

    def chat(self, messages: list[dict[str, Any]], temperature=0.2, max_tokens=2048) -> str:
        if not self.api_key:
            raise RuntimeError('缺少 API Key，无法调用对话模型')
        url = f'{self.base_url}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data['choices'][0]['message']['content']

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        temperature=0.2,
        max_tokens=2048,
    ) -> Iterator[str]:
        if not self.api_key:
            raise RuntimeError('缺少 API Key，无法调用对话模型')
        url = f'{self.base_url}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': True,
        }
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream('POST', url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        line = line.decode('utf-8')
                    if not line.startswith('data:'):
                        continue
                    data = line[5:].strip()
                    if data == '[DONE]':
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get('choices') or []
                    if not choices:
                        continue
                    delta = choices[0].get('delta') or {}
                    content = delta.get('content') or ''
                    if content:
                        yield content
