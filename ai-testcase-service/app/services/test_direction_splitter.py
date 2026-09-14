from app.services.config_factory import build_llm_client
from app.utils.json_parser import parse_json_array
from app.utils.prompt_loader import render_prompt


MAX_RETRIES = 2


def split_test_directions(features, matched_requirements, llm_config=None):
    """Yield {'kind':'chunk','content':...} then {'kind':'result','directions':...}."""
    context = _build_context(features, matched_requirements)
    llm = build_llm_client(llm_config or {})
    prompt = render_prompt('test_direction_split', context=context)
    messages = [{'role': 'user', 'content': prompt}]

    last_error = ''
    for _ in range(MAX_RETRIES + 1):
        try:
            if not llm.api_key:
                yield {'kind': 'result', 'directions': _fallback_directions(features)}
                return
            parts = []
            for delta in llm.chat_stream(messages, temperature=0.1, max_tokens=8192):
                if not delta:
                    continue
                parts.append(delta)
                yield {'kind': 'chunk', 'content': delta}
            directions = parse_json_array(''.join(parts))
            if directions:
                yield {'kind': 'result', 'directions': _normalize_directions(directions)}
                return
            last_error = 'JSON 解析失败'
        except Exception as exc:
            last_error = str(exc)
    raise RuntimeError(f'测试方向拆分失败：{last_error}')


def _build_context(features, matched_requirements):
    matched_map = {}
    for item in matched_requirements or []:
        key = (item.get('模块') or '', item.get('功能点') or '')
        matched_map[key] = item.get('hits') or []

    lines = []
    for feature in features or []:
        module = feature.get('模块') or ''
        point = feature.get('功能点') or ''
        hits = matched_map.get((module, point), [])
        hit_text = '\n'.join(f'- {hit.get("content", "")}' for hit in hits[:3]) or '- （无关联需求）'
        lines.append(f'模块：{module}\n功能点：{point}\n关联需求：\n{hit_text}')
    return '\n\n'.join(lines)


def _normalize_directions(items):
    allowed = {'业务测试', '功能测试', '其他测试'}
    normalized = []
    for item in items:
        module = (item.get('模块') or '').strip()
        point = (item.get('功能点') or '').strip()
        direction = (item.get('方向') or '').strip()
        note = (item.get('说明') or '').strip()
        if direction not in allowed:
            direction = '功能测试'
        if module and point:
            normalized.append({'模块': module, '功能点': point, '方向': direction, '说明': note})
    return normalized


def _fallback_directions(features):
    return [
        {
            '模块': feature.get('模块') or '',
            '功能点': feature.get('功能点') or '',
            '方向': '功能测试',
            '说明': '未配置对话模型，默认功能测试方向',
        }
        for feature in (features or [])
    ]
