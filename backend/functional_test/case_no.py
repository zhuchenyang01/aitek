import os
import re

# GBK 区位到拼音首字母（用于需求名称缩写）
_GBK_INITIAL_STARTS = (
    (0xB0A1, 'A'),
    (0xB0C5, 'B'),
    (0xB2C1, 'C'),
    (0xB4EE, 'D'),
    (0xB6EA, 'E'),
    (0xB7A2, 'F'),
    (0xB8C1, 'G'),
    (0xB9FE, 'H'),
    (0xBBF7, 'J'),
    (0xBFA6, 'K'),
    (0xC0AC, 'L'),
    (0xC2E8, 'M'),
    (0xC4C3, 'N'),
    (0xC5B6, 'O'),
    (0xC5BE, 'P'),
    (0xC6DA, 'Q'),
    (0xC8BB, 'R'),
    (0xC8F6, 'S'),
    (0xCBFA, 'T'),
    (0xCDDA, 'W'),
    (0xCEF4, 'X'),
    (0xD1B9, 'Y'),
    (0xD4D1, 'Z'),
)

_STRIP_EXT = {'.doc', '.docx', '.pdf', '.txt', '.md', '.xls', '.xlsx'}
_SKIP_CHARS_RE = re.compile(r'[\s\-—_~～、，,。．.：:；;！!？?（）()【】\[\]《》<>/\\|]+')


def _cjk_initial(ch):
    try:
        encoded = ch.encode('gbk')
    except UnicodeEncodeError:
        return ''
    if len(encoded) != 2:
        return ''
    code = encoded[0] * 256 + encoded[1]
    if code < _GBK_INITIAL_STARTS[0][0] or code > 0xD7F9:
        return ''
    letter = 'Z'
    for start, item in _GBK_INITIAL_STARTS:
        if code >= start:
            letter = item
        else:
            break
    return letter


def requirement_initials(name, max_len=8):
    raw = (name or '').strip()
    root, ext = os.path.splitext(raw)
    if ext.lower() in _STRIP_EXT:
        raw = root
    raw = _SKIP_CHARS_RE.sub('', raw)
    letters = []
    for ch in raw:
        if 'A' <= ch <= 'Z' or 'a' <= ch <= 'z':
            letters.append(ch.upper())
        elif '0' <= ch <= '9':
            letters.append(ch)
        elif '\u4e00' <= ch <= '\u9fff':
            initial = _cjk_initial(ch)
            if initial:
                letters.append(initial)
        if len(letters) >= max_len:
            break
    return ''.join(letters) or 'REQ'


def assign_unique_case_nos(cases, requirement_name, used_nos=None):
    used = {item for item in (used_nos or []) if item}
    prefix = f'TC-{requirement_initials(requirement_name)}-'
    next_seq = 1
    for item in used:
        match = re.match(rf'^{re.escape(prefix)}(\d+)$', item, re.IGNORECASE)
        if match:
            next_seq = max(next_seq, int(match.group(1)) + 1)

    assigned = []
    for item in cases:
        case = dict(item)
        while True:
            candidate = f'{prefix}{next_seq:03d}'
            next_seq += 1
            if candidate not in used:
                break
        used.add(candidate)
        case['case_no'] = candidate
        assigned.append(case)
    return assigned
