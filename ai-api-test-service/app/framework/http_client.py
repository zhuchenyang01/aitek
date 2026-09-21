import json

import requests


def kv_to_dict(rows):
    result = {}
    for item in rows or []:
        if not isinstance(item, dict):
            continue
        if item.get('enabled') is False:
            continue
        key = str(item.get('key') or '').strip()
        if key:
            result[key] = str(item.get('value') or '')
    return result


def apply_auth(headers, auth_type, auth_config):
    config = auth_config or {}
    auth = (auth_type or 'none').lower()
    if auth == 'bearer' and config.get('token'):
        headers['Authorization'] = f"Bearer {config['token']}"
    elif auth == 'basic' and config.get('credential'):
        headers['Authorization'] = f"Basic {config['credential']}"
    elif auth == 'apikey' and config.get('key'):
        header_name = config.get('header') or 'X-API-Key'
        headers[header_name] = str(config['key'])
    return headers


def parse_body(raw):
    if raw is None or raw == '':
        return None, None
    if isinstance(raw, (dict, list)):
        return json.dumps(raw, ensure_ascii=False), raw
    text = str(raw).strip()
    if not text:
        return None, None
    try:
        return text, json.loads(text)
    except json.JSONDecodeError:
        return text, text


def apply_path_params(url, rows):
    result = url or ''
    for item in rows or []:
        if not isinstance(item, dict) or item.get('enabled') is False:
            continue
        key = str(item.get('key') or '').strip()
        if not key:
            continue
        value = str(item.get('value') or '')
        result = result.replace('{' + key + '}', value)
    return result


def send_request(spec, timeout, session=None):
    method = (spec.get('method') or 'GET').upper()
    url = apply_path_params((spec.get('url') or spec.get('path') or '').strip(), spec.get('path_params'))
    if not url:
        raise ValueError('缺少请求地址')
    headers = kv_to_dict(spec.get('headers'))
    headers.update(kv_to_dict(spec.get('request_headers')))
    apply_auth(headers, spec.get('auth_type'), spec.get('auth_config'))
    params = kv_to_dict(spec.get('query'))
    params.update(kv_to_dict(spec.get('request_query')))
    cookies = kv_to_dict(spec.get('cookies'))
    body_text, body_json = parse_body(spec.get('body'))
    kwargs = {
        'method': method,
        'url': url,
        'headers': headers or None,
        'params': params or None,
        'cookies': cookies or None,
        'timeout': timeout,
    }
    if body_json is not None and not isinstance(body_json, str):
        kwargs['json'] = body_json
        headers.setdefault('Content-Type', 'application/json')
        kwargs['headers'] = headers
    elif body_text:
        kwargs['data'] = body_text
    client = session or spec.get('_session') or requests
    response = client.request(**kwargs)
    return {
        'method': method,
        'url': response.url,
        'request_headers': headers,
        'request_params': params,
        'request_cookies': cookies,
        'request_body': body_text or '',
        'status_code': response.status_code,
        'response_headers': dict(response.headers),
        'response_text': response.text,
        'elapsed_ms': int(response.elapsed.total_seconds() * 1000),
    }
