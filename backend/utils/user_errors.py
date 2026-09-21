import re

_CODE_DUMP_RE = re.compile(
    r'Traceback \(most recent call last\)|File "[^"]+\.py"|AssertionError:|app\.framework\.|IntegrityError|OperationalError',
    re.I,
)
_HTML_RE = re.compile(r'<!DOCTYPE|<html[\s>]', re.I)


def user_facing_error(exc, fallback='操作失败，请稍后重试'):
    text = str(exc or '').strip()
    if not text:
        return fallback
    if _HTML_RE.search(text) or _CODE_DUMP_RE.search(text):
        chinese = next(
            (
                line.strip()
                for line in text.splitlines()
                if re.search(r'[\u4e00-\u9fff]', line) and 'File "' not in line
            ),
            '',
        )
        return chinese[:180] if chinese else fallback
    if len(text) > 180:
        return text[:180] + '…'
    return text
