import json
import re

VAR_PATTERN = re.compile(r'\$\{([A-Za-z0-9_]+)\}')


def apply_vars(value, variables):
    variables = variables or {}
    if isinstance(value, dict):
        return {key: apply_vars(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [apply_vars(item, variables) for item in value]
    if not isinstance(value, str):
        return value

    def replacer(match):
        name = match.group(1)
        if name in variables:
            return str(variables[name])
        return match.group(0)

    return VAR_PATTERN.sub(replacer, value)


def apply_vars_to_spec(spec, variables):
    skip = {'_session'}
    result = {}
    for key, value in (spec or {}).items():
        if key in skip:
            result[key] = value
            continue
        result[key] = apply_vars(value, variables)
    return result


def extract_by_path(payload, path):
    text = (path or '').strip()
    if text.startswith('$.'):
        text = text[2:]
    elif text.startswith('$'):
        text = text[1:].lstrip('.')
    current = payload
    if not text:
        return current
    for part in text.split('.'):
        if current is None:
            return None
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return None
            current = current[index]
            continue
        if isinstance(current, dict):
            current = current.get(part)
            continue
        return None
    return current


def parse_response_json(response_text):
    raw = (response_text or '').strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, (dict, list)) else {}


def extract_variables(response_text, extractors):
    data = parse_response_json(response_text)
    result = {}
    for item in extractors or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        path = str(item.get('path') or '').strip()
        if not name or not path:
            continue
        value = extract_by_path(data, path)
        if value is not None:
            result[name] = value
    return result
