import json

import httpx
from django.conf import settings


class ApiTestServiceError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _base_url():
    return (getattr(settings, 'API_TEST_SERVICE_BASE_URL', '') or 'http://127.0.0.1:8003').rstrip('/')


def _headers(user_id):
    headers = {
        'Content-Type': 'application/json',
        'X-User-Id': str(user_id),
    }
    token = (
        getattr(settings, 'API_TEST_SERVICE_INTERNAL_TOKEN', None)
        or getattr(settings, 'AI_SERVICE_INTERNAL_TOKEN', '')
        or ''
    ).strip()
    if token:
        headers['X-Internal-Token'] = token
    return headers


def run_api_case(user_id, payload, timeout=60):
    url = f'{_base_url()}/api/run'
    try:
        response = httpx.post(url, json=payload, headers=_headers(user_id), timeout=timeout)
    except httpx.RequestError as exc:
        raise ApiTestServiceError(f'接口测试服务不可用：{exc}') from exc
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise ApiTestServiceError(f'接口测试服务返回异常：HTTP {response.status_code}') from exc
    if response.status_code >= 400 or (isinstance(data, dict) and data.get('code') not in (0, None)):
        raise ApiTestServiceError(data.get('msg') if isinstance(data, dict) else '执行失败')
    return data


def run_api_suite(user_id, payload, timeout=120):
    url = f'{_base_url()}/api/run-suite'
    try:
        response = httpx.post(url, json=payload, headers=_headers(user_id), timeout=timeout)
    except httpx.RequestError as exc:
        raise ApiTestServiceError(f'接口测试服务不可用：{exc}') from exc
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise ApiTestServiceError(f'接口测试服务返回异常：HTTP {response.status_code}') from exc
    if response.status_code >= 400 or (isinstance(data, dict) and data.get('code') not in (0, None)):
        raise ApiTestServiceError(data.get('msg') if isinstance(data, dict) else '执行失败')
    return data
