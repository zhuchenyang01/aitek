from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from system.llm import ensure_default, set_default_config, test_model_connection
from system.models import UserLLMConfig
from system.ollama import fetch_ollama_models
from system.serializers import LLMConfigTestSerializer, LLMConfigWriteSerializer, UserLLMConfigSerializer


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


def owned_config(user, pk):
    return UserLLMConfig.objects.filter(pk=pk, user=user).first()


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def llm_config_list_create(request):
    if request.method == 'GET':
        queryset = UserLLMConfig.objects.filter(user=request.user)
        model_type = (request.query_params.get('model_type') or '').strip()
        if model_type:
            queryset = queryset.filter(model_type=model_type)
        return ok(UserLLMConfigSerializer(queryset, many=True).data, msg='查询成功')

    serializer = LLMConfigWriteSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    data = serializer.validated_data
    model_type = data.get('model_type', UserLLMConfig.TYPE_CHAT)
    has_default = UserLLMConfig.objects.filter(
        user=request.user,
        model_type=model_type,
        is_default=True,
    ).exists()
    if not has_default:
        data['is_default'] = True
    config = UserLLMConfig.objects.create(user=request.user, **data)
    if config.is_default:
        set_default_config(config)
    return ok(UserLLMConfigSerializer(config).data, msg='模型已保存', http_status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def llm_config_detail(request, pk):
    config = owned_config(request.user, pk)
    if config is None:
        return fail('模型配置不存在', http_status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return ok(UserLLMConfigSerializer(config).data, msg='查询成功')

    if request.method == 'DELETE':
        user = config.user
        model_type = config.model_type
        config_id = config.id
        config.delete()
        ensure_default(user, model_type=model_type, exclude_id=config_id)
        return ok(None, msg='已删除')

    serializer = LLMConfigWriteSerializer(data=request.data, partial=True, instance=config)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    for field, value in serializer.validated_data.items():
        setattr(config, field, value)
    config.save()
    if config.is_default:
        set_default_config(config)
    else:
        ensure_default(request.user, model_type=config.model_type)
    return ok(UserLLMConfigSerializer(config).data, msg='已更新')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def llm_config_set_default(request, pk):
    config = owned_config(request.user, pk)
    if config is None:
        return fail('模型配置不存在', http_status=status.HTTP_404_NOT_FOUND)
    set_default_config(config)
    return ok(UserLLMConfigSerializer(config).data, msg='已设为默认模型')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def llm_config_test(request):
    config_id = request.data.get('id')
    if config_id:
        config = owned_config(request.user, config_id)
        if config is None:
            return fail('模型配置不存在', http_status=status.HTTP_404_NOT_FOUND)
        serializer = LLMConfigTestSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            for field, value in serializer.validated_data.items():
                if field == 'id':
                    continue
                setattr(config, field, value)
    else:
        serializer = LLMConfigTestSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(first_error_msg(serializer.errors))
        data = serializer.validated_data
        data.setdefault('model_type', UserLLMConfig.TYPE_CHAT)
        data.setdefault('source', UserLLMConfig.SOURCE_API)
        data.setdefault('provider', UserLLMConfig.PROVIDER_CUSTOM)
        config = UserLLMConfig(user=request.user, **data)

    try:
        result = test_model_connection(config)
    except Exception as exc:
        return fail(f'连接失败：{exc}', http_status=status.HTTP_502_BAD_GATEWAY)
    return ok(result, msg=result.get('message') or '连接成功')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ollama_models(request):
    base_url = (request.query_params.get('base_url') or '').strip()
    try:
        models = fetch_ollama_models(base_url or None)
    except Exception as exc:
        return fail(f'无法连接 Ollama：{exc}', http_status=status.HTTP_502_BAD_GATEWAY)
    return ok({'models': models}, msg='查询成功')
