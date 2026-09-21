import json
import re

from .importers import HTTP_METHODS, kv_item

EXTRACT_PROMPT = """你是接口文档结构化抽取助手。必须严格依据「文档原文」抽取其中出现的全部 HTTP 接口。

硬性要求：
1. 严禁编造文档没有的路径、方法、参数名、字段、示例。
2. 严禁改写、合并、删减或遗漏文档中的任何接口。
3. 文档写了什么就抽什么；未写明的字段用空字符串、空数组或 none，不要猜测补全。
4. 请求/响应示例、表格单元格原文尽量原样保留。
5. 只输出 JSON 数组，不要 Markdown、不要解释。

每个对象字段：
name, method, url, path, host, protocol, version, description,
headers, query_params, path_params（均为 [{{"key","value","description","enabled":true}}]）,
body_mode（none|json|raw|form-data|urlencoded）,
body_raw, body_form, auth_type（none|bearer|basic|apikey）, auth_config,
content_type, request_example, response_status, response_headers, response_body

文档原文：
{document}
"""

CHUNK_PROMPT = EXTRACT_PROMPT + "\n\n说明：以上只是完整文档的一个片段，只抽取本片段中已经写明的接口，不要因为前后文缺失而丢弃本片段里的接口。"


def parse_json_array(text):
    raw = (text or '').strip()
    if not raw:
        return []
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s*```$', '', raw)
    match = re.search(r'\[[\s\S]*\]', raw)
    candidate = match.group(0) if match else raw
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        try:
            data = json.loads(re.sub(r',\s*]', ']', candidate))
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def split_document(text, chunk_size=7000, overlap=400):
    content = (text or '').strip()
    if len(content) <= chunk_size:
        return [content]
    chunks = []
    start = 0
    length = len(content)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            cut = content.rfind('\n', start + chunk_size // 2, end)
            if cut > start:
                end = cut
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks or [content]


def normalize_llm_interface(item, filename='', version=''):
    method = str(item.get('method') or 'GET').upper().strip()
    if method.lower() not in HTTP_METHODS:
        method = 'GET'
    name = str(item.get('name') or item.get('接口名称') or '').strip()
    url = str(item.get('url') or item.get('请求地址') or '').strip()
    path = str(item.get('path') or item.get('路径') or '').strip()
    if not name:
        name = f'{method} {path or url or "未命名接口"}'
    body_mode = str(item.get('body_mode') or 'none').strip() or 'none'
    auth_type = str(item.get('auth_type') or 'none').strip() or 'none'
    return {
        'name': name[:255],
        'method': method,
        'url': url[:2048],
        'path': path[:1024],
        'host': str(item.get('host') or '')[:255],
        'protocol': str(item.get('protocol') or 'https')[:16],
        'version': (version or str(item.get('version') or ''))[:64],
        'description': str(item.get('description') or item.get('描述') or ''),
        'headers': _as_kv(item.get('headers') or item.get('请求头')),
        'query_params': _as_kv(item.get('query_params') or item.get('Query')),
        'path_params': _as_kv(item.get('path_params')),
        'body_mode': body_mode if body_mode in {'none', 'raw', 'json', 'form-data', 'urlencoded'} else 'none',
        'body_raw': str(item.get('body_raw') or item.get('请求体') or ''),
        'body_form': _as_kv(item.get('body_form')),
        'auth_type': auth_type if auth_type in {'none', 'bearer', 'basic', 'apikey'} else 'none',
        'auth_config': item.get('auth_config') if isinstance(item.get('auth_config'), dict) else {},
        'content_type': str(item.get('content_type') or '')[:128],
        'request_example': str(item.get('request_example') or ''),
        'response_status': str(item.get('response_status') or '')[:16],
        'response_headers': _as_kv(item.get('response_headers')),
        'response_body': str(item.get('response_body') or item.get('响应体') or ''),
        'source_type': 'word',
        'source_filename': filename[:255],
    }


def _as_kv(value):
    if not value:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        return [kv_item('raw', text)]
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if isinstance(item, dict):
            key = item.get('key') or item.get('name') or item.get('字段') or ''
            if not key:
                continue
            rows.append(
                kv_item(
                    key,
                    item.get('value') or item.get('示例') or '',
                    item.get('description') or item.get('说明') or '',
                    item.get('enabled', True),
                )
            )
    return rows


def merge_interfaces(items):
    merged = []
    index = {}
    for item in items:
        key = (
            (item.get('method') or '').upper(),
            item.get('url') or item.get('path') or '',
            item.get('name') or '',
        )
        if key in index:
            old = merged[index[key]]
            if _filled_score(item) > _filled_score(old):
                merged[index[key]] = item
            continue
        index[key] = len(merged)
        merged.append(item)
    return merged


def _filled_score(item):
    score = 0
    for key in ('description', 'body_raw', 'request_example', 'response_body', 'url', 'path'):
        score += len(str(item.get(key) or ''))
    for key in ('headers', 'query_params', 'path_params'):
        score += 10 * len(item.get(key) or [])
    return score


def extract_interfaces_with_llm(llm, document_text, filename='', version=''):
    text = (document_text or '').strip()
    if not text:
        raise ValueError('Word 文档没有可解析的文本')
    chunks = split_document(text)
    collected = []
    last_error = ''
    for index, chunk in enumerate(chunks):
        prompt = (EXTRACT_PROMPT if len(chunks) == 1 else CHUNK_PROMPT).format(document=chunk)
        try:
            answer = llm.chat(
                [{'role': 'user', 'content': prompt}],
                temperature=0,
                max_tokens=8192,
            )
        except Exception as exc:
            last_error = str(exc)
            continue
        parsed = parse_json_array(answer)
        if not parsed:
            last_error = '大模型未返回有效 JSON 数组'
            continue
        for item in parsed:
            collected.append(normalize_llm_interface(item, filename=filename, version=version))
    if not collected:
        raise ValueError(last_error or '未能从 Word 文档解析出接口，请检查文档内容或模型配置')
    return merge_interfaces(collected)
