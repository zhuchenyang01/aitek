import json
import re


def parse_json_array(text):
    raw = (text or '').strip()
    if not raw:
        return []
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s*```$', '', raw)

    candidates = [raw]
    match = re.search(r'\[[\s\S]*\]', raw)
    if match:
        candidates.insert(0, match.group(0))

    for candidate in candidates:
        parsed = _load_list(candidate)
        if parsed:
            return parsed

    return _salvage_objects(raw)


def _load_list(candidate):
    variants = [
        candidate,
        re.sub(r',\s*]', ']', candidate),
        candidate.replace("'", '"'),
        re.sub(r',\s*]', ']', candidate.replace("'", '"')),
    ]
    for variant in variants:
        try:
            data = json.loads(variant)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
    return []


def _salvage_objects(text):
    items = []
    for blob in _iter_complete_objects(text):
        parsed = _load_list(blob)
        if parsed:
            items.extend(parsed)
            continue
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            try:
                data = json.loads(blob.replace("'", '"'))
            except json.JSONDecodeError:
                continue
        if isinstance(data, dict):
            items.append(data)
    return items


def _iter_complete_objects(text):
    index = 0
    while index < len(text):
        if text[index] != '{':
            index += 1
            continue
        end = _match_brace(text, index)
        if end is None:
            break
        yield text[index : end + 1]
        index = end + 1


def _match_brace(text, start):
    depth = 0
    in_string = False
    escape = False
    quote = ''
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == quote:
                in_string = False
            continue
        if char in {'"', "'"}:
            in_string = True
            quote = char
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return index
    return None
