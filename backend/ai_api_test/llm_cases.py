import json

from .llm_parser import parse_json_array

CASE_PROMPT = """你是接口测试用例设计助手。根据给定的 HTTP 接口定义，生成可执行的接口测试用例。

要求：
1. 覆盖正向、反向、边界、缺参、鉴权（如接口需要）等场景，生成 4～8 条，不要重复。
2. 请求体、Query、Header 必须贴合接口字段，不要编造接口里没有的业务路径。
3. 若提供了「已配置测试数据」，优先用这些 JSON 作为正向/反向用例的请求体。
4. 先写思考，再写用例。不要 Markdown。

输出格式：
【思考】
用 3～8 条短句说明将覆盖的场景、关键入参和断言思路。

【用例】
JSON 数组，不要解释。

每条用例字段：
name（用例名称）,
priority（P0|P1|P2|P3）,
case_type（正向|反向|边界|异常）,
description（步骤与预期的简要说明）,
preconditions（前置条件，可空）,
request_headers（[{{"key","value","enabled":true}}]，可空数组）,
request_query（同上，可空数组）,
request_body（字符串，JSON 请求体或空字符串）,
expected_status（如 200、400、401）,
expected_body（期望响应片段或空字符串）,
assertions（[{{"name","expected"}}]，至少 1 条）

接口定义：
{interface}

已配置测试数据：
{datasets}
"""


def interface_spec(interface):
    return {
        'id': interface.id,
        'name': interface.name,
        'method': interface.method,
        'url': interface.url,
        'path': interface.path,
        'description': interface.description,
        'headers': interface.headers,
        'query_params': interface.query_params,
        'path_params': interface.path_params,
        'body_mode': interface.body_mode,
        'body_raw': interface.body_raw,
        'body_form': interface.body_form,
        'auth_type': interface.auth_type,
        'content_type': interface.content_type,
        'request_example': interface.request_example,
        'response_status': interface.response_status,
        'response_body': interface.response_body,
    }


def datasets_spec(rows):
    return [
        {'id': item.id, 'description': item.description, 'payload': item.payload}
        for item in rows
    ]


def normalize_case(item):
    name = str(item.get('name') or '').strip()
    if not name:
        return None
    priority = str(item.get('priority') or 'P2').upper().strip()
    if priority not in {'P0', 'P1', 'P2', 'P3'}:
        priority = 'P2'
    case_type = str(item.get('case_type') or '正向').strip() or '正向'
    body = item.get('request_body')
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False)
    else:
        body = str(body or '').strip()
    assertions = item.get('assertions')
    if not isinstance(assertions, list):
        assertions = []
    clean_assertions = []
    for row in assertions:
        if not isinstance(row, dict):
            continue
        clean_assertions.append(
            {
                'name': str(row.get('name') or row.get('check') or '').strip(),
                'expected': str(row.get('expected') or row.get('value') or '').strip(),
            }
        )
    headers = item.get('request_headers') if isinstance(item.get('request_headers'), list) else []
    query = item.get('request_query') if isinstance(item.get('request_query'), list) else []
    return {
        'name': name[:255],
        'priority': priority,
        'case_type': case_type[:32],
        'description': str(item.get('description') or '').strip(),
        'preconditions': str(item.get('preconditions') or '').strip(),
        'request_headers': headers,
        'request_query': query,
        'request_body': body,
        'expected_status': str(item.get('expected_status') or '200').strip()[:16],
        'expected_body': str(item.get('expected_body') or '').strip(),
        'assertions': clean_assertions,
    }


def generate_cases_with_llm(llm, interface, dataset_rows):
    prompt = CASE_PROMPT.format(
        interface=json.dumps(interface_spec(interface), ensure_ascii=False, indent=2),
        datasets=json.dumps(datasets_spec(dataset_rows), ensure_ascii=False, indent=2) or '[]',
    )
    answer = llm.chat(
        [{'role': 'user', 'content': prompt}],
        temperature=0.2,
        max_tokens=8192,
    )
    if '【用例】' in answer:
        answer = answer.split('【用例】', 1)[-1]
    parsed = parse_json_array(answer)
    cases = []
    for item in parsed:
        normalized = normalize_case(item)
        if normalized:
            cases.append(normalized)
    if not cases:
        raise ValueError('大模型未返回有效测试用例，请检查模型配置后重试')
    return cases


def _iter_llm_events(llm, prompt):
    messages = [{'role': 'user', 'content': prompt}]
    iterator = getattr(llm, 'iter_chat_events', None)
    if callable(iterator):
        yield from iterator(messages, temperature=0.2, max_tokens=8192)
        return
    stream = getattr(llm, 'chat_stream', None)
    if callable(stream):
        for chunk in stream(messages, temperature=0.2, max_tokens=8192):
            if chunk:
                yield {'type': 'answer', 'content': chunk}
        return
    answer = llm.chat(messages, temperature=0.2, max_tokens=8192)
    if answer:
        yield {'type': 'answer', 'content': answer}


def generate_cases_stream(llm, interface, dataset_rows):
    prompt = CASE_PROMPT.format(
        interface=json.dumps(interface_spec(interface), ensure_ascii=False, indent=2),
        datasets=json.dumps(datasets_spec(dataset_rows), ensure_ascii=False, indent=2) or '[]',
    )
    yield {'response_type': 'step', 'content': f'正在读取接口「{interface.name}」…', 'done': False}
    yield {'response_type': 'step', 'content': '正在整理方法、地址、参数与鉴权信息…', 'done': False}
    if dataset_rows:
        yield {'response_type': 'step', 'content': f'已带入 {len(dataset_rows)} 条测试数据', 'done': False}
    yield {'response_type': 'step', 'content': '正在调用大模型思考测试场景…', 'done': False}

    raw_parts = []
    mode = 'pre'
    hold = ''
    think_emitted = 0
    for event in _iter_llm_events(llm, prompt):
        kind = event.get('type')
        chunk = event.get('content') or ''
        if not chunk:
            continue
        if kind == 'thinking':
            yield {'response_type': 'thinking', 'content': chunk, 'done': False}
            continue
        raw_parts.append(chunk)
        if mode == 'json':
            yield {'response_type': 'answer', 'content': chunk, 'done': False}
            continue
        hold += chunk
        if '【用例】' in hold:
            before, after = hold.split('【用例】', 1)
            think = before.replace('【思考】', '')
            extra = think[think_emitted:]
            if extra.strip():
                yield {'response_type': 'thinking', 'content': extra, 'done': False}
            mode = 'json'
            hold = after
            if after:
                yield {'response_type': 'answer', 'content': after, 'done': False}
            continue
        json_at = hold.find('[')
        if json_at >= 0 and '【思考】' not in hold:
            prefix = hold[:json_at]
            extra = prefix[think_emitted:]
            if extra.strip():
                yield {'response_type': 'thinking', 'content': extra, 'done': False}
            mode = 'json'
            rest = hold[json_at:]
            hold = rest
            if rest:
                yield {'response_type': 'answer', 'content': rest, 'done': False}
            continue
        if '【思考】' in hold:
            visible = hold.split('【思考】', 1)[-1]
            extra = visible[think_emitted:]
            if extra:
                yield {'response_type': 'thinking', 'content': extra, 'done': False}
                think_emitted = len(visible)

    answer = ''.join(raw_parts)
    if '【用例】' in answer:
        answer = answer.split('【用例】', 1)[-1]
    parsed = parse_json_array(answer)
    cases = []
    for item in parsed:
        normalized = normalize_case(item)
        if normalized:
            cases.append(normalized)
    if not cases:
        raise ValueError('大模型未返回有效测试用例，请检查模型配置后重试')
    yield {'response_type': 'parsed', 'content': f'已解析出 {len(cases)} 条用例，正在保存…', 'count': len(cases), 'done': False}
    yield {'response_type': 'cases', 'cases': cases, 'done': False}
