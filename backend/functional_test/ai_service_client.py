import json

import httpx
from django.conf import settings

from ai_testcase.generator import sse_bytes


class AIServiceError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _base_url():
    return (getattr(settings, 'AI_SERVICE_BASE_URL', '') or 'http://127.0.0.1:8002').rstrip('/')


def _headers(user_id):
    headers = {
        'Content-Type': 'application/json',
        'X-User-Id': str(user_id),
    }
    token = (getattr(settings, 'AI_SERVICE_INTERNAL_TOKEN', '') or '').strip()
    if token:
        headers['X-Internal-Token'] = token
    return headers


def serialize_llm_client(client):
    if client is None:
        return {}
    return {
        'api_key': getattr(client, 'api_key', '') or '',
        'base_url': getattr(client, 'base_url', '') or '',
        'model': getattr(client, 'model', '') or '',
        'timeout': float(getattr(client, 'timeout', 120) or 120),
    }


def serialize_embedding_client(client):
    if client is None:
        return {}
    return {
        'api_key': getattr(client, 'api_key', '') or '',
        'base_url': getattr(client, 'base_url', '') or '',
        'model': getattr(client, 'model', '') or '',
        'timeout': float(getattr(client, 'timeout', 120) or 120),
        'use_local': bool(getattr(client, 'use_local', False)),
    }


def serialize_rerank_client(client):
    if client is None:
        return {}
    return {
        'api_key': getattr(client, 'api_key', '') or '',
        'base_url': getattr(client, 'base_url', '') or '',
        'model': getattr(client, 'model', '') or '',
        'timeout': float(getattr(client, 'timeout', 120) or 120),
    }


def serialize_vision_client(client):
    if client is None:
        return {}
    return {
        'api_key': getattr(client, 'api_key', '') or '',
        'base_url': getattr(client, 'base_url', '') or '',
        'model': getattr(client, 'model', '') or '',
        'timeout': float(getattr(client, 'timeout', 120) or 120),
    }


def ingest_document(user_id, knowledge_base_id, title, content_text, source_filename='', embedding_config=None):
    payload = {
        'knowledge_base_id': knowledge_base_id,
        'title': title,
        'content_text': content_text,
        'source_filename': source_filename,
        'embedding_config': embedding_config or {},
    }
    timeout = float(getattr(settings, 'RAG_HTTP_TIMEOUT', 120))
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f'{_base_url()}/internal/v1/ingest',
                headers=_headers(user_id),
                json=payload,
            )
            data = response.json()
    except httpx.RequestError as exc:
        raise AIServiceError(f'AI 服务暂不可用：{exc}', status_code=503) from exc

    if response.status_code >= 400 or data.get('code') != 0:
        raise AIServiceError(data.get('msg') or 'AI 入库失败', status_code=response.status_code)

    return data.get('data') or {}


def _friendly_stream_error(exc):
    text = str(exc)
    if (
        isinstance(exc, httpx.RemoteProtocolError)
        or 'illegal chunk header' in text
        or 'Internal Server Error' in text
    ):
        return (
            'AI 服务在生成过程中异常退出（服务端 500）。'
            '常见原因是 gunicorn 超时杀掉进程，或向量/模型调用崩溃。'
            '请查看 journalctl -u aitek-ai，并确认超时已加大后重试。'
        )
    return f'AI 服务暂不可用：{exc}'


def _is_terminal_ai_event(event):
    response_type = event.get('response_type')
    if response_type == 'error':
        return True
    if response_type == 'answer' and event.get('done'):
        return True
    if response_type == 'pipeline' and event.get('status') == 'error':
        return True
    return False


def iter_generate_stream(
    user_id,
    query,
    requirement_kb_id,
    testcase_kb_id,
    llm_config=None,
    embedding_config=None,
    rerank_config=None,
    vision_config=None,
    file_path=None,
    pipeline=True,
):
    payload = {
        'query': query,
        'requirement_kb_id': requirement_kb_id,
        'testcase_kb_id': testcase_kb_id,
        'llm_config': llm_config or {},
        'embedding_config': embedding_config or {},
        'rerank_config': rerank_config or {},
        'vision_config': vision_config or {},
        'file_path': file_path,
        'pipeline': bool(pipeline),
    }
    connect_timeout = float(getattr(settings, 'RAG_HTTP_TIMEOUT', 120))
    read_timeout = float(getattr(settings, 'AI_SERVICE_STREAM_READ_TIMEOUT', 3600))
    timeout = httpx.Timeout(connect_timeout, read=read_timeout)
    # 禁用 keep-alive，避免上一请求的 500 页被当成下一帧 chunk
    client = httpx.Client(
        timeout=timeout,
        limits=httpx.Limits(max_keepalive_connections=0, max_connections=1),
    )

    def _parse_sse_part(part):
        try:
            text = part.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise AIServiceError(f'AI 服务返回数据解码失败：{exc}', status_code=502) from exc
        for line in text.split('\n'):
            if not line.startswith('data:'):
                continue
            raw = line[5:].strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError:
                continue

    try:
        with client.stream(
            'POST',
            f'{_base_url()}/internal/v1/generate/stream',
            headers=_headers(user_id),
            json=payload,
        ) as response:
            if response.status_code >= 400:
                try:
                    data = json.loads(response.read().decode('utf-8'))
                    message = data.get('msg') or 'AI 生成失败'
                except Exception:
                    message = f'AI 生成失败（HTTP {response.status_code}）'
                raise AIServiceError(message, status_code=response.status_code)

            buffer = b''
            saw_terminal = False
            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                buffer += chunk
                parts = buffer.split(b'\n\n')
                buffer = parts.pop() or b''
                for part in parts:
                    for event in _parse_sse_part(part):
                        if _is_terminal_ai_event(event):
                            saw_terminal = True
                        yield event
            if buffer.strip():
                for event in _parse_sse_part(buffer):
                    if _is_terminal_ai_event(event):
                        saw_terminal = True
                    yield event
            if not saw_terminal:
                raise AIServiceError('AI 服务连接中断，未完成生成流程', status_code=502)
    except httpx.ReadTimeout as exc:
        raise AIServiceError(
            f'AI 服务响应超时（超过 {int(read_timeout)} 秒），请稍后重试或缩小需求范围',
            status_code=504,
        ) from exc
    except httpx.RequestError as exc:
        raise AIServiceError(_friendly_stream_error(exc), status_code=503) from exc
    finally:
        client.close()


def proxy_sse_event(event):
    return sse_bytes(event)
