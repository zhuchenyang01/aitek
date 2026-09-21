"""DeepSeek / OpenAI 兼容对话客户端。"""
from __future__ import annotations

import json
from typing import Any, Iterator

import httpx

from rag import config
from rag.utils.timing import timed


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else config.DEEPSEEK_API_KEY
        self.base_url = (base_url or config.DEEPSEEK_BASE_URL).rstrip("/")
        self.model = model or config.DEEPSEEK_CHAT_MODEL
        self.timeout = timeout or config.HTTP_TIMEOUT

    @timed("llm.chat")
    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("缺少 DEEPSEEK_API_KEY，无法调用对话模型")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        print(f"[LLM] POST {url} model={self.model}")
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        print(f"[LLM] 返回长度={len(content)}")
        return content

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Iterator[str]:
        """流式输出增量文本。"""
        for event in self.iter_chat_events(messages, temperature=temperature, max_tokens=max_tokens):
            if event.get("type") == "answer" and event.get("content"):
                yield event["content"]

    def iter_chat_events(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Iterator[dict[str, str]]:
        """流式输出思考/正文事件。"""
        if not self.api_key:
            raise RuntimeError("缺少 DEEPSEEK_API_KEY，无法调用对话模型")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        print(f"[LLM] STREAM POST {url} model={self.model}")
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        line = line.decode("utf-8")
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
                    if reasoning:
                        yield {"type": "thinking", "content": reasoning}
                    content = delta.get("content") or ""
                    if content:
                        yield {"type": "answer", "content": content}
