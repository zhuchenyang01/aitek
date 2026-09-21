import io
import json

from django.conf import settings
from django.http import JsonResponse

from utils.aes_crypto import decrypt_text, encrypt_text


def _need_crypto(path: str) -> bool:
    """路径是否在加解密白名单中（见 settings.CRYPTO_API_PATHS）"""
    paths = getattr(settings, 'CRYPTO_API_PATHS', [])
    return any(path == item or path.startswith(item) for item in paths)


class CryptoMiddleware:
    """仅对白名单接口做请求解密 / 响应加密"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _need_crypto(request.path):
            return self.get_response(request)

        error_response = self._decrypt_request(request)
        if error_response is not None:
            return error_response

        response = self.get_response(request)
        if getattr(request, '_crypto_plain_request', False):
            return response
        return self._encrypt_response(response)

    def _decrypt_request(self, request):
        method = request.method.upper()
        if method in ('GET', 'HEAD', 'OPTIONS'):
            return None

        raw = request.body
        if not raw:
            return None

        try:
            data = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JsonResponse(
                {'code': 1, 'msg': '请求体必须是 JSON', 'data': None},
                status=400,
            )

        if not isinstance(data, dict) or 'payload' not in data:
            # 接口自动化可直接提交业务 JSON；浏览器登录仍走加密 payload
            request._crypto_plain_request = True
            return None

        try:
            plain = decrypt_text(data['payload'])
            json.loads(plain)
        except Exception:
            return JsonResponse(
                {'code': 1, 'msg': '请求解密失败', 'data': None},
                status=400,
            )

        encoded = plain.encode('utf-8')
        request._body = encoded
        request._stream = io.BytesIO(encoded)
        request.META['CONTENT_LENGTH'] = str(len(encoded))
        if hasattr(request, '_read_started'):
            request._read_started = False
        return None

    def _encrypt_response(self, response):
        content_type = response.get('Content-Type', '')
        if 'application/json' not in content_type:
            return response

        try:
            content = response.content.decode('utf-8')
            if not content:
                return response
            data = json.loads(content)
        except Exception:
            return response

        if isinstance(data, dict) and 'payload' in data and len(data) == 1:
            return response

        try:
            cipher = encrypt_text(json.dumps(data, ensure_ascii=False))
            new_body = json.dumps({'payload': cipher}, ensure_ascii=False).encode('utf-8')
            response.content = new_body
            response['Content-Length'] = str(len(new_body))
            response['Content-Type'] = 'application/json; charset=utf-8'
        except Exception:
            return response

        return response
