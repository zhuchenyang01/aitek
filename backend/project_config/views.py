from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import ProjectConfig
from .serializers import ProjectConfigSerializer


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


@api_view(['GET', 'POST'])
def config_list_create(request):
    if request.method == 'GET':
        queryset = ProjectConfig.objects.all()
        serializer = ProjectConfigSerializer(queryset, many=True)
        return ok(serializer.data, msg='查询成功')

    serializer = ProjectConfigSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    serializer.save()
    return ok(serializer.data, msg='新增成功', http_status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
def config_detail(request, pk):
    try:
        instance = ProjectConfig.objects.get(pk=pk)
    except ProjectConfig.DoesNotExist:
        return fail('配置不存在', http_status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        instance.delete()
        return ok(msg='删除成功')

    serializer = ProjectConfigSerializer(instance, data=request.data, partial=True)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    serializer.save()
    return ok(serializer.data, msg='修改成功')
