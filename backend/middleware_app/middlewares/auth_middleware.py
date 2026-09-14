from django.http import JsonResponse
from rest_framework.authtoken.models import Token


class AuthMiddleware:
    """API Bearer Token 鉴权中间件"""

    WHITELIST_PREFIXES = (
        '/api/system/login/',
        '/api/system/register/',
        '/api/test/',
        '/admin/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if self._is_whitelisted(path) or not path.startswith('/api/'):
            return self.get_response(request)

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return self._unauthorized('未登录或登录已失效')

        token_key = auth_header[7:].strip()
        if not token_key:
            return self._unauthorized('未登录或登录已失效')

        try:
            token = Token.objects.select_related('user').get(key=token_key)
        except Token.DoesNotExist:
            return self._unauthorized('未登录或登录已失效')

        if not token.user.is_active:
            return self._unauthorized('账号已被禁用')

        request.user = token.user
        request.auth = token
        return self.get_response(request)

    def _is_whitelisted(self, path):
        return any(path.startswith(prefix) for prefix in self.WHITELIST_PREFIXES)

    @staticmethod
    def _unauthorized(msg):
        return JsonResponse(
            {'code': 401, 'msg': msg, 'data': None},
            status=401,
        )
