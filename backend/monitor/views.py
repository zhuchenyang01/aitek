from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .collector import SSHCollectError
from .models import MetricSample, MonitorServer
from .serializers import (
    MetricSampleSerializer,
    MonitorServerSerializer,
    MonitorServerWriteSerializer,
)
from .services import collect_and_store, run_test


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


def owned_server(user, pk):
    return MonitorServer.objects.filter(pk=pk, user=user).first()


RANGE_MAP = {
    '15m': timedelta(minutes=15),
    '1h': timedelta(hours=1),
    '6h': timedelta(hours=6),
    '24h': timedelta(hours=24),
}


@api_view(['GET', 'POST'])
def server_list_create(request):
    if request.method == 'GET':
        qs = MonitorServer.objects.filter(user=request.user)
        return ok(MonitorServerSerializer(qs, many=True).data, msg='查询成功')

    serializer = MonitorServerWriteSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    server = serializer.save()
    return ok(MonitorServerSerializer(server).data, msg='创建成功', http_status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def server_detail(request, pk):
    server = owned_server(request.user, pk)
    if not server:
        return fail('服务器不存在', http_status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return ok(MonitorServerSerializer(server).data, msg='查询成功')

    if request.method == 'DELETE':
        server.delete()
        return ok(msg='删除成功')

    serializer = MonitorServerWriteSerializer(
        server,
        data=request.data,
        partial=True,
        context={'request': request},
    )
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    server = serializer.save()
    return ok(MonitorServerSerializer(server).data, msg='更新成功')


@api_view(['POST'])
def server_test(request, pk):
    server = owned_server(request.user, pk)
    if not server:
        return fail('服务器不存在', http_status=status.HTTP_404_NOT_FOUND)
    if not server.password_enc:
        return fail('未配置 SSH 密码')
    try:
        info = run_test(server)
        return ok(info, msg='连接成功')
    except SSHCollectError as exc:
        return fail(str(exc))


@api_view(['POST'])
def server_collect(request, pk):
    server = owned_server(request.user, pk)
    if not server:
        return fail('服务器不存在', http_status=status.HTTP_404_NOT_FOUND)
    if not server.password_enc:
        return fail('未配置 SSH 密码')
    try:
        sample = collect_and_store(server)
        return ok(MetricSampleSerializer(sample).data, msg='采集成功')
    except SSHCollectError as exc:
        return fail(str(exc))


@api_view(['GET'])
def server_metrics(request, pk):
    server = owned_server(request.user, pk)
    if not server:
        return fail('服务器不存在', http_status=status.HTTP_404_NOT_FOUND)

    range_key = (request.query_params.get('range') or '1h').strip()
    delta = RANGE_MAP.get(range_key, RANGE_MAP['1h'])
    since = timezone.now() - delta
    samples = (
        MetricSample.objects.filter(server=server, collected_at__gte=since)
        .order_by('collected_at')
    )
    return ok(
        {
            'range': range_key if range_key in RANGE_MAP else '1h',
            'items': MetricSampleSerializer(samples, many=True).data,
        },
        msg='查询成功',
    )


@api_view(['GET'])
def server_latest(request, pk):
    server = owned_server(request.user, pk)
    if not server:
        return fail('服务器不存在', http_status=status.HTTP_404_NOT_FOUND)
    sample = (
        MetricSample.objects.filter(server=server)
        .order_by('-collected_at')
        .first()
    )
    if not sample:
        return ok(None, msg='暂无数据')
    return ok(MetricSampleSerializer(sample).data, msg='查询成功')
