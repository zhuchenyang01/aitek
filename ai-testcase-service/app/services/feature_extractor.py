from app.services.config_factory import build_llm_client
from app.utils.json_parser import parse_json_array
from app.utils.prompt_loader import render_prompt


MAX_RETRIES = 2


def extract_features(document_content, llm_config=None):
    """Yield {'kind':'chunk','content':...} then {'kind':'result','features':...}."""
    llm = build_llm_client(llm_config or {})
    prompt = render_prompt('feature_extraction', document_content=document_content)
    messages = [{'role': 'user', 'content': prompt}]

    last_error = ''
    for _ in range(MAX_RETRIES + 1):
        try:
            if not llm.api_key:
                yield {'kind': 'result', 'features': _fallback_features(document_content)}
                return
            parts = []
            for delta in llm.chat_stream(messages, temperature=0.1, max_tokens=8192):
                if not delta:
                    continue
                parts.append(delta)
                yield {'kind': 'chunk', 'content': delta}
            features = parse_json_array(''.join(parts))
            if features:
                yield {'kind': 'result', 'features': _normalize_features(features)}
                return
            last_error = 'JSON 解析失败'
        except Exception as exc:
            last_error = str(exc)
    raise RuntimeError(f'功能点提取失败：{last_error}')


def _normalize_features(items):
    normalized = []
    for item in items:
        module = (item.get('模块') or item.get('module') or '').strip()
        feature = (item.get('功能点') or item.get('feature') or '').strip()
        if module and feature:
            normalized.append({'模块': module, '功能点': feature})
    return normalized


def _fallback_features(document_content):
    lines = [line.strip() for line in (document_content or '').splitlines() if line.strip()]
    if not lines:
        return [{'模块': '默认模块', '功能点': '请配置对话模型后重新提取功能点'}]
    return [{'模块': '默认模块', '功能点': line[:200]} for line in lines[:5]]
