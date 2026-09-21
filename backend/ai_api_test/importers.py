import json
from urllib.parse import urlparse

HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}


def empty_kv():
    return []


def kv_item(key, value='', description='', enabled=True, location=''):
    item = {
        'key': str(key or ''),
        'value': '' if value is None else str(value),
        'description': str(description or ''),
        'enabled': bool(enabled),
    }
    if location:
        item['in'] = location
    return item


def parse_api_document(raw_text, filename=''):
    text = (raw_text or '').strip()
    if not text:
        raise ValueError('文档内容为空')
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError('仅支持 JSON 格式的 OpenAPI/Swagger 或 Postman Collection') from exc
    if not isinstance(payload, dict):
        raise ValueError('文档根节点必须是对象')

    if payload.get('openapi') or payload.get('swagger'):
        return parse_openapi(payload, filename=filename)
    if payload.get('info', {}).get('schema') == 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json' or (
        isinstance(payload.get('item'), list) and payload.get('info')
    ):
        return parse_postman(payload, filename=filename)
    raise ValueError('无法识别文档类型，请上传 OpenAPI/Swagger 或 Postman Collection JSON')


def parse_openapi(doc, filename=''):
    info = doc.get('info') or {}
    version = str(info.get('version') or '').strip()
    source_type = 'openapi'
    items = []
    if doc.get('openapi'):
        base = ''
        servers = doc.get('servers') or []
        if servers and isinstance(servers[0], dict):
            base = (servers[0].get('url') or '').rstrip('/')
        paths = doc.get('paths') or {}
        for path, ops in paths.items():
            if not isinstance(ops, dict):
                continue
            shared_params = ops.get('parameters') if isinstance(ops.get('parameters'), list) else []
            for method, operation in ops.items():
                if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                items.append(
                    _from_openapi_operation(
                        method,
                        path,
                        operation,
                        shared_params,
                        base,
                        version,
                        source_type,
                        filename,
                    )
                )
        return items

    host = str(doc.get('host') or '').strip()
    base_path = str(doc.get('basePath') or '').rstrip('/')
    schemes = doc.get('schemes') or ['https']
    protocol = schemes[0] if schemes else 'https'
    base = f'{protocol}://{host}{base_path}' if host else base_path
    paths = doc.get('paths') or {}
    for path, ops in paths.items():
        if not isinstance(ops, dict):
            continue
        shared_params = ops.get('parameters') if isinstance(ops.get('parameters'), list) else []
        for method, operation in ops.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            items.append(
                _from_openapi_operation(
                    method,
                    path,
                    operation,
                    shared_params,
                    base,
                    version,
                    source_type,
                    filename,
                    protocol=protocol,
                    host=host,
                )
            )
    return items


def _from_openapi_operation(method, path, operation, shared_params, base, version, source_type, filename, protocol='', host=''):
    params = list(shared_params or [])
    extra = operation.get('parameters') if isinstance(operation.get('parameters'), list) else []
    params.extend(extra)
    headers, query_params, path_params = [], [], []
    for param in params:
        if not isinstance(param, dict):
            continue
        location = (param.get('in') or '').lower()
        item = kv_item(param.get('name'), param.get('default') or '', param.get('description') or '', True, location)
        if location == 'header':
            headers.append(item)
        elif location == 'query':
            query_params.append(item)
        elif location == 'path':
            path_params.append(item)

    body_mode = 'none'
    body_raw = ''
    content_type = ''
    request_body = operation.get('requestBody') or {}
    content = request_body.get('content') if isinstance(request_body, dict) else None
    if isinstance(content, dict) and content:
        content_type = next(iter(content.keys()))
        media = content.get(content_type) or {}
        example = media.get('example')
        if example is None:
            examples = media.get('examples') or {}
            if isinstance(examples, dict) and examples:
                first = next(iter(examples.values()))
                if isinstance(first, dict):
                    example = first.get('value')
        if example is not None:
            body_raw = json.dumps(example, ensure_ascii=False, indent=2)
        if 'json' in content_type:
            body_mode = 'json'
        elif 'x-www-form-urlencoded' in content_type:
            body_mode = 'urlencoded'
        elif 'form-data' in content_type or 'multipart' in content_type:
            body_mode = 'form-data'
        else:
            body_mode = 'raw'

    response_status = ''
    response_body = ''
    response_headers = []
    responses = operation.get('responses') or {}
    if isinstance(responses, dict) and responses:
        for code in ('200', '201', 'default'):
            if code in responses:
                response_status = '200' if code == 'default' else str(code)
                resp = responses[code] or {}
                resp_content = resp.get('content') if isinstance(resp, dict) else None
                if isinstance(resp_content, dict) and resp_content:
                    media = next(iter(resp_content.values())) or {}
                    example = media.get('example')
                    if example is not None:
                        response_body = (
                            json.dumps(example, ensure_ascii=False, indent=2)
                            if not isinstance(example, str)
                            else example
                        )
                break
        if not response_status:
            response_status = str(next(iter(responses.keys())))

    parsed_base = urlparse(base) if base else None
    full_url = f'{base}{path}' if base and not path.startswith('http') else (path if path.startswith('http') else f'{base}{path}')
    if parsed_base and parsed_base.scheme:
        protocol = protocol or parsed_base.scheme
        host = host or parsed_base.netloc

    name = (operation.get('summary') or operation.get('operationId') or f'{method.upper()} {path}').strip()
    return {
        'name': name[:255],
        'method': method.upper(),
        'url': full_url[:2048],
        'path': path[:1024],
        'host': (host or '')[:255],
        'protocol': (protocol or 'https')[:16],
        'version': (version or '')[:64],
        'description': str(operation.get('description') or ''),
        'headers': headers,
        'query_params': query_params,
        'path_params': path_params,
        'body_mode': body_mode,
        'body_raw': body_raw,
        'body_form': empty_kv(),
        'auth_type': 'none',
        'auth_config': {},
        'content_type': content_type[:128],
        'request_example': body_raw,
        'response_status': response_status[:16],
        'response_headers': response_headers,
        'response_body': response_body,
        'source_type': source_type,
        'source_filename': filename[:255],
    }


def parse_postman(doc, filename=''):
    version = str((doc.get('info') or {}).get('version') or '').strip()
    items = []

    def walk(nodes):
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            if isinstance(node.get('item'), list):
                walk(node.get('item'))
                continue
            request = node.get('request')
            if not request:
                continue
            if isinstance(request, str):
                items.append(_from_postman_request(node.get('name') or request, {'method': 'GET', 'url': request}, version, filename))
                continue
            items.append(_from_postman_request(node.get('name') or '', request, version, filename))

    walk(doc.get('item') or [])
    return items


def _from_postman_request(name, request, version, filename):
    method = str(request.get('method') or 'GET').upper()
    if method.lower() not in HTTP_METHODS:
        method = 'GET'
    url_obj = request.get('url')
    raw_url = ''
    path = ''
    host = ''
    protocol = 'https'
    query_params = []
    if isinstance(url_obj, str):
        raw_url = url_obj
        parsed = urlparse(url_obj)
        path = parsed.path or url_obj
        host = parsed.netloc
        protocol = parsed.scheme or 'https'
    elif isinstance(url_obj, dict):
        raw_url = url_obj.get('raw') or ''
        path_parts = url_obj.get('path') or []
        if isinstance(path_parts, list):
            path = '/' + '/'.join(str(part).lstrip('/') for part in path_parts if part is not None)
        else:
            path = str(path_parts or '')
        host_parts = url_obj.get('host') or []
        host = '.'.join(host_parts) if isinstance(host_parts, list) else str(host_parts or '')
        protocol = str(url_obj.get('protocol') or 'https')
        for q in url_obj.get('query') or []:
            if isinstance(q, dict):
                query_params.append(kv_item(q.get('key'), q.get('value') or '', q.get('description') or ''))
        if not raw_url:
            raw_url = f'{protocol}://{host}{path}'

    headers = []
    for header in request.get('header') or []:
        if isinstance(header, dict):
            headers.append(
                kv_item(
                    header.get('key'),
                    header.get('value') or '',
                    header.get('description') or '',
                    not header.get('disabled'),
                )
            )

    body = request.get('body') or {}
    body_mode = 'none'
    body_raw = ''
    body_form = []
    content_type = ''
    mode = (body.get('mode') if isinstance(body, dict) else '') or ''
    if mode == 'raw':
        body_raw = str(body.get('raw') or '')
        language = ((body.get('options') or {}).get('raw') or {}).get('language') or ''
        body_mode = 'json' if language == 'json' or (body_raw.strip().startswith('{') or body_raw.strip().startswith('[')) else 'raw'
        content_type = 'application/json' if body_mode == 'json' else ''
    elif mode in ('urlencoded', 'formdata'):
        body_mode = 'urlencoded' if mode == 'urlencoded' else 'form-data'
        rows = body.get(mode) or []
        for row in rows:
            if isinstance(row, dict):
                body_form.append(kv_item(row.get('key'), row.get('value') or '', row.get('description') or ''))
    desc = request.get('description')
    if isinstance(desc, dict):
        desc = desc.get('content') or ''

    return {
        'name': (name or f'{method} {path}' or raw_url)[:255],
        'method': method,
        'url': raw_url[:2048],
        'path': path[:1024],
        'host': host[:255],
        'protocol': protocol[:16],
        'version': version[:64],
        'description': str(desc or ''),
        'headers': headers,
        'query_params': query_params,
        'path_params': [],
        'body_mode': body_mode,
        'body_raw': body_raw,
        'body_form': body_form,
        'auth_type': 'none',
        'auth_config': {},
        'content_type': content_type[:128],
        'request_example': body_raw,
        'response_status': '',
        'response_headers': [],
        'response_body': '',
        'source_type': 'postman',
        'source_filename': filename[:255],
    }
