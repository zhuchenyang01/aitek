import json
import re

from app.framework.vars import extract_by_path, parse_response_json

OPERATOR_ALIASES = {
    'eq': 'eq',
    'equal': 'eq',
    'equals': 'eq',
    'eql': 'eq',
    '==': 'eq',
    '=': 'eq',
    '等于': 'eq',
    'ne': 'ne',
    'not_eq': 'ne',
    'not_equal': 'ne',
    '!=': 'ne',
    '不等于': 'ne',
    'contains': 'contains',
    'contain': 'contains',
    'include': 'contains',
    'includes': 'contains',
    '包含': 'contains',
    'not_contains': 'not_contains',
    'not_contain': 'not_contains',
    'excludes': 'not_contains',
    '不包含': 'not_contains',
    'exists': 'exists',
    'exist': 'exists',
    '存在': 'exists',
    'not_exists': 'not_exists',
    'not_exist': 'not_exists',
    '不存在': 'not_exists',
    'matches': 'matches',
    'match': 'matches',
    'regex': 'matches',
    '正则': 'matches',
    'gt': 'gt',
    '>': 'gt',
    'gte': 'gte',
    '>=': 'gte',
    'lt': 'lt',
    '<': 'lt',
    'lte': 'lte',
    '<=': 'lte',
}


def check_status(actual, expected):
    if expected in (None, ''):
        return True, '未配置期望状态码'
    want = str(expected).strip()
    got = str(actual)
    if got != want:
        return False, f'状态码断言失败：期望 {want}，实际 {got}'
    return True, f'状态码断言通过：{got}'


def check_body_contains(actual_text, expected_fragment):
    if expected_fragment in (None, ''):
        return True, '未配置期望响应'
    fragment = str(expected_fragment)
    if fragment not in (actual_text or ''):
        return False, f'响应内容不包含：{fragment[:200]}'
    return True, '响应内容包含期望片段'


def normalize_operator(value):
    key = str(value or 'eq').strip().lower()
    return OPERATOR_ALIASES.get(key, 'eq')


def _as_http(http_or_text):
    if isinstance(http_or_text, dict):
        return http_or_text
    return {
        'response_text': http_or_text or '',
        'status_code': None,
        'response_headers': {},
        'elapsed_ms': None,
    }


def _header_value(headers, name):
    if not name:
        return None
    want = str(name).strip().lower()
    for key, value in (headers or {}).items():
        if str(key).lower() == want:
            return value
    return None


def _stringify(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    return str(value)


def _numbers(left, right):
    try:
        return float(left), float(right)
    except (TypeError, ValueError):
        return None


def _equal(actual, expected):
    if actual is True and str(expected).lower() in ('true', '1'):
        return True
    if actual is False and str(expected).lower() in ('false', '0'):
        return True
    nums = _numbers(actual, expected)
    if nums is not None and not isinstance(actual, bool):
        return nums[0] == nums[1]
    return _stringify(actual) == _stringify(expected)


def compare(actual, operator, expected):
    op = normalize_operator(operator)
    if op == 'exists':
        return actual is not None, actual
    if op == 'not_exists':
        return actual is None, actual
    text = _stringify(actual)
    want = '' if expected is None else str(expected)
    if op == 'eq':
        return _equal(actual, expected), actual
    if op == 'ne':
        return not _equal(actual, expected), actual
    if op == 'contains':
        return want in text, actual
    if op == 'not_contains':
        return want not in text, actual
    if op == 'matches':
        try:
            return bool(re.search(want, text)), actual
        except re.error:
            return False, actual
    nums = _numbers(actual, expected)
    if nums is None:
        return False, actual
    left, right = nums
    if op == 'gt':
        return left > right, actual
    if op == 'gte':
        return left >= right, actual
    if op == 'lt':
        return left < right, actual
    if op == 'lte':
        return left <= right, actual
    return _equal(actual, expected), actual


def resolve_source(item):
    name = str(item.get('name') or item.get('check') or '').strip()
    source = str(item.get('source') or item.get('target') or '').strip().lower()
    path = str(item.get('path') or item.get('jsonpath') or item.get('key') or '').strip()
    if not source:
        lowered = name.lower()
        if lowered in ('status', 'status_code'):
            source = 'status'
        elif lowered in ('body', 'response', 'text'):
            source = 'body'
        elif lowered in ('header', 'headers'):
            source = 'header'
        elif lowered in ('time', 'elapsed', 'responsetime'):
            source = 'time'
        elif name:
            source = 'json'
            path = path or name
        else:
            source = 'body'
    elif source in ('json', 'jsonpath', 'field') and not path:
        path = name
    if source in ('status_code',):
        source = 'status'
    if source in ('response', 'text'):
        source = 'body'
    if source in ('headers',):
        source = 'header'
    if source in ('elapsed', 'responsetime', 'response_time'):
        source = 'time'
    if source in ('jsonpath', 'field'):
        source = 'json'
    return source, path, name


def pick_actual(http, source, path):
    if source == 'status':
        return http.get('status_code')
    if source == 'time':
        return http.get('elapsed_ms')
    if source == 'header':
        return _header_value(http.get('response_headers') or {}, path)
    text = http.get('response_text') or ''
    if source == 'json':
        data = parse_response_json(text)
        if not path:
            return data
        return extract_by_path(data, path)
    return text


def check_assertion_item(http_or_text, item):
    if not isinstance(item, dict):
        return True, '忽略非法断言项'
    item = dict(item)
    explicit_source = bool(str(item.get('source') or item.get('target') or '').strip())
    explicit_op = bool(str(item.get('operator') or item.get('type') or item.get('compare') or '').strip())
    legacy_name = str(item.get('name') or item.get('check') or '').strip()
    if not explicit_source and not explicit_op:
        if legacy_name.lower() in ('status', 'status_code'):
            item['source'] = 'status'
            item['operator'] = 'eq'
        elif item.get('expected') not in (None, '') or item.get('value') not in (None, ''):
            item['source'] = 'json'
            item['path'] = item.get('path') or legacy_name
            item['operator'] = 'eq'
        elif legacy_name:
            item['source'] = 'body'
            item['operator'] = 'contains'
            item['expected'] = legacy_name
    expected = item.get('expected')
    if expected is None:
        expected = item.get('value')
    operator = item.get('operator') or item.get('type') or item.get('compare') or 'eq'
    source, path, name = resolve_source(item)
    if not source and expected in (None, '') and not path:
        return True, '空断言'

    http = _as_http(http_or_text)
    actual = pick_actual(http, source, path)
    ok, got = compare(actual, operator, expected)
    label = path or name or source
    op = normalize_operator(operator)
    op_label = {
        'eq': '等于',
        'ne': '不等于',
        'contains': '包含',
        'not_contains': '不包含',
        'exists': '存在',
        'not_exists': '不存在',
        'matches': '匹配正则',
        'gt': '大于',
        'gte': '大于等于',
        'lt': '小于',
        'lte': '小于等于',
    }.get(op, op)
    source_label = {
        'status': '状态码',
        'body': '响应体',
        'json': f'JSON.{path}' if path else 'JSON',
        'header': f'响应头.{path}' if path else '响应头',
        'time': '响应时间(ms)',
    }.get(source, source)
    if ok:
        return True, f'断言通过 [{source_label} {op_label} {expected if op not in ("exists", "not_exists") else ""}]'.rstrip()
    return False, (
        f'断言失败 [{label}]：期望 {op_label} {expected if expected is not None else ""}，实际 {"" if got is None else _stringify(got)[:200]}'
    )
