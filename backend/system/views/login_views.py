from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from system.serializers import RegisterSerializer, LoginSerializer


def ok(data=None, msg='ok', http_status=status.HTTP_200_OK):
    return Response({'code': 0, 'msg': msg, 'data': data}, status=http_status)


def fail(msg='操作失败', data=None, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({'code': 1, 'msg': msg, 'data': data}, status=http_status)


def first_error_msg(errors):
    if isinstance(errors, dict):
        for value in errors.values():
            return first_error_msg(value)
    if isinstance(errors, list) and errors:
        return first_error_msg(errors[0])
    return str(errors)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    user = serializer.save()
    return ok(
        {'id': user.id, 'username': user.username},
        msg='注册成功',
        http_status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))

    username = serializer.validated_data['username'].strip()
    password = serializer.validated_data['password']
    user = authenticate(username=username, password=password)
    if user is None:
        return fail('用户名或密码错误')
    if not user.is_active:
        return fail('账号已被禁用', http_status=status.HTTP_403_FORBIDDEN)

    token, _ = Token.objects.get_or_create(user=user)
    return ok(
        {
            'token': token.key,
            'id': user.id,
            'username': user.username,
        },
        msg='登录成功',
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return ok(msg='退出成功')
