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


def check_assertion_item(actual_text, item):
    if not isinstance(item, dict):
        return True, '忽略非法断言项'
    name = str(item.get('name') or '').strip()
    expected = str(item.get('expected') or '')
    if not name and not expected:
        return True, '空断言'
    text = actual_text or ''
    if name.lower() in ('status', 'status_code') and expected:
        return True, f'状态码断言交由 expected_status 处理（{expected}）'
    target = expected if expected else name
    if target and target not in text:
        return False, f'断言失败 [{name or target}]：响应未包含 {target[:200]}'
    return True, f'断言通过 [{name or target}]'
