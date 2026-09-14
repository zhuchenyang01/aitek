"""Ollama 本地模型发现。"""
from __future__ import annotations

import httpx

from .llm import OLLAMA_BASE_URL


def ollama_native_base(base_url: str | None = None) -> str:
    url = (base_url or OLLAMA_BASE_URL).strip().rstrip('/')
    if url.endswith('/v1'):
        url = url[:-3]
    return url.rstrip('/')


def fetch_ollama_models(base_url: str | None = None, timeout: float = 10) -> list[dict]:
    native = ollama_native_base(base_url)
    endpoint = f'{native}/api/tags'
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(endpoint)
        resp.raise_for_status()
        data = resp.json()

    models = []
    for item in data.get('models') or []:
        name = (item.get('name') or item.get('model') or '').strip()
        if not name:
            continue
        models.append(
            {
                'name': name,
                'size': item.get('size'),
                'modified_at': item.get('modified_at'),
                'digest': item.get('digest'),
            }
        )
    models.sort(key=lambda row: row['name'])
    return models
