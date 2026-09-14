import json


def sse_bytes(event: dict) -> bytes:
    payload = json.dumps(event, ensure_ascii=False)
    return f'event: message\ndata: {payload}\n\n'.encode('utf-8')
