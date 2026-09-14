from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """兼容前端 Authorization: Bearer <token>"""

    keyword = 'Bearer'
