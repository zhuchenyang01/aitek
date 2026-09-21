import json
import os
import tempfile
from pathlib import Path

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from ai_testcase.ingest import extract_text_from_file
from functional_test.models import FunctionalProject
from system.llm import resolve_llm_client

from .importers import parse_api_document
from ai_testcase.generator import sse_bytes
from .llm_cases import generate_cases_stream, generate_cases_with_llm
from .llm_parser import extract_interfaces_with_llm
from .models import ApiInterface, ApiInterfaceData, ApiTestCase, ApiTestRunLog
from .run_persist import persist_single_run
from .service_client import ApiTestServiceError, run_api_case
from .user_errors import public_run_data
from utils.user_errors import user_facing_error
from .serializers import (
    ApiDocImportSerializer,
    ApiInterfaceDataSerializer,
    ApiInterfaceDetailSerializer,
    ApiInterfaceListSerializer,
    ApiInterfaceWriteSerializer,
    ApiTestCaseSerializer,
)


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


def owned_interface(user, pk):
    return ApiInterface.objects.filter(pk=pk, user=user).select_related('project', 'user').first()


ALLOWED_PAGE_SIZES = {10, 20, 50}


def parse_page_params(request, default_size=20):
    try:
        page = int(request.query_params.get('page') or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get('page_size') or default_size)
    except (TypeError, ValueError):
        page_size = default_size
    if page < 1:
        page = 1
    if page_size not in ALLOWED_PAGE_SIZES:
        page_size = default_size
    return page, page_size


def apply_write_fields(instance, data):
    mapping = (
        'name',
        'method',
        'url',
        'path',
        'host',
        'protocol',
        'version',
        'description',
        'headers',
        'query_params',
        'path_params',
        'body_mode',
        'body_raw',
        'body_form',
        'auth_type',
        'auth_config',
        'content_type',
        'timeout_ms',
        'request_example',
        'response_status',
        'response_headers',
        'response_body',
        'cookies',
        'setup_script',
        'teardown_script',
    )
    for key in mapping:
        if key in data and data[key] is not None:
            setattr(instance, key, data[key])
    if data.get('project_id'):
        instance.project_id = data['project_id']
    if not instance.path and instance.url:
        instance.path = instance.url
    if not instance.url and instance.path:
        instance.url = instance.path


def _parse_word_upload(user, uploaded, filename, version):
    llm = resolve_llm_client(user)
    if llm is None:
        raise ValueError('请先在模型配置中添加对话模型，再解析 Word 接口文档')
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            for chunk in uploaded.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        text = extract_text_from_file(tmp_path, filename)
        return extract_interfaces_with_llm(llm, text, filename=filename, version=version)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@api_view(['GET'])
def health(request):
    return Response({'msg': 'ok'})


@api_view(['GET', 'POST'])
def interface_list_create(request):
    if request.method == 'GET':
        queryset = ApiInterface.objects.filter(user=request.user).select_related('project')
        project_id = request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        keyword = (request.query_params.get('keyword') or '').strip()
        if keyword:
            queryset = queryset.filter(Q(name__icontains=keyword) | Q(url__icontains=keyword) | Q(path__icontains=keyword))
        if str(request.query_params.get('for_select') or '').strip() in ('1', 'true', 'True'):
            items = queryset[:500]
            return ok(
                [
                    {
                        'id': item.id,
                        'name': item.name,
                        'method': item.method,
                        'url': item.url,
                        'path': item.path,
                    }
                    for item in items
                ]
            )
        total = queryset.count()
        page, page_size = parse_page_params(request)
        start = (page - 1) * page_size
        items = queryset[start : start + page_size]
        return ok(
            {
                'items': ApiInterfaceListSerializer(items, many=True).data,
                'total': total,
                'page': page,
                'page_size': page_size,
            }
        )

    serializer = ApiInterfaceWriteSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    data = serializer.validated_data
    project = FunctionalProject.objects.filter(pk=data['project_id'], user=request.user).first()
    item = ApiInterface(user=request.user, project=project, source_type='manual')
    apply_write_fields(item, data)
    item.save()
    return ok(ApiInterfaceDetailSerializer(item).data, msg='接口创建成功', http_status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def interface_detail(request, pk):
    item = owned_interface(request.user, pk)
    if item is None:
        return fail('接口不存在', http_status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return ok(ApiInterfaceDetailSerializer(item).data)
    if request.method == 'DELETE':
        item.delete()
        return ok(msg='接口已删除')

    serializer = ApiInterfaceWriteSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    apply_write_fields(item, serializer.validated_data)
    item.save()
    return ok(ApiInterfaceDetailSerializer(item).data, msg='接口已保存')


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def interface_import(request):
    serializer = ApiDocImportSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    uploaded = serializer.validated_data['file']
    version = (serializer.validated_data.get('version') or '').strip()
    project = FunctionalProject.objects.filter(
        pk=serializer.validated_data['project_id'],
        user=request.user,
    ).first()
    filename = getattr(uploaded, 'name', '') or 'api.json'
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == '.docx':
            parsed = _parse_word_upload(request.user, uploaded, filename, version)
        else:
            raw = uploaded.read().decode('utf-8')
            parsed = parse_api_document(raw, filename=filename)
    except UnicodeDecodeError:
        return fail('JSON 文件编码必须是 UTF-8')
    except LookupError:
        return fail('对话模型配置不存在')
    except ValueError as exc:
        return fail(user_facing_error(exc, '解析接口文档失败'))
    except Exception:
        return fail('解析接口文档失败')
    if not parsed:
        return fail('文档中没有解析到接口')

    created = []
    for payload in parsed:
        if version:
            payload['version'] = version
        item = ApiInterface(user=request.user, project=project)
        apply_write_fields(item, payload)
        item.source_type = payload.get('source_type') or 'openapi'
        item.source_filename = filename[:255]
        item.save()
        created.append(item)

    return ok(
        {
            'count': len(created),
            'items': ApiInterfaceListSerializer(created, many=True).data,
        },
        msg=f'已导入 {len(created)} 个接口',
        http_status=status.HTTP_201_CREATED,
    )


@api_view(['GET', 'POST'])
def dataset_list_create(request):
    if request.method == 'GET':
        queryset = ApiInterfaceData.objects.filter(user=request.user).select_related('interface')
        interface_id = request.query_params.get('interface_id')
        if interface_id:
            queryset = queryset.filter(interface_id=interface_id)
        keyword = (request.query_params.get('keyword') or '').strip()
        if keyword:
            queryset = queryset.filter(Q(description__icontains=keyword))
        total = queryset.count()
        page, page_size = parse_page_params(request)
        start = (page - 1) * page_size
        items = queryset[start : start + page_size]
        return ok(
            {
                'items': ApiInterfaceDataSerializer(items, many=True).data,
                'total': total,
                'page': page,
                'page_size': page_size,
            }
        )

    serializer = ApiInterfaceDataSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    data = serializer.validated_data
    item = ApiInterfaceData.objects.create(
        user=request.user,
        interface_id=data['interface_id'],
        description=data['description'],
        payload=data['payload'],
    )
    return ok(ApiInterfaceDataSerializer(item).data, msg='数据保存成功', http_status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def dataset_detail(request, pk):
    item = ApiInterfaceData.objects.filter(pk=pk, user=request.user).first()
    if item is None:
        return fail('测试数据不存在', http_status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return ok(ApiInterfaceDataSerializer(item).data)
    if request.method == 'DELETE':
        item.delete()
        return ok(msg='已删除')
    serializer = ApiInterfaceDataSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    data = serializer.validated_data
    item.interface_id = data['interface_id']
    item.description = data['description']
    item.payload = data['payload']
    item.save()
    return ok(ApiInterfaceDataSerializer(item).data, msg='数据已更新')


@api_view(['POST'])
def interface_generate_cases(request, pk):
    item = owned_interface(request.user, pk)
    if item is None:
        return fail('接口不存在', http_status=status.HTTP_404_NOT_FOUND)
    try:
        llm = resolve_llm_client(request.user)
    except LookupError:
        return fail('对话模型配置不存在')
    if llm is None:
        return fail('请先在模型配置中添加对话模型')
    datasets = list(ApiInterfaceData.objects.filter(user=request.user, interface=item)[:20])
    try:
        generated = generate_cases_with_llm(llm, item, datasets)
    except ValueError as exc:
        return fail(str(exc))
    except Exception:
        return fail('生成测试用例失败')
    created = []
    for payload in generated:
        created.append(
            ApiTestCase.objects.create(
                user=request.user,
                interface=item,
                source_type='llm',
                **payload,
            )
        )
    return ok(
        {
            'count': len(created),
            'items': ApiTestCaseSerializer(created, many=True).data,
        },
        msg=f'已生成 {len(created)} 条测试用例',
        http_status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
def interface_generate_cases_stream(request, pk):
    item = owned_interface(request.user, pk)
    if item is None:
        return fail('接口不存在', http_status=status.HTTP_404_NOT_FOUND)
    try:
        llm = resolve_llm_client(request.user)
    except LookupError:
        return fail('对话模型配置不存在')
    if llm is None:
        return fail('请先在模型配置中添加对话模型')
    datasets = list(ApiInterfaceData.objects.filter(user=request.user, interface=item)[:20])

    def event_stream():
        try:
            for event in generate_cases_stream(llm, item, datasets):
                if event.get('response_type') == 'cases':
                    created = []
                    for payload in event.get('cases') or []:
                        created.append(
                            ApiTestCase.objects.create(
                                user=request.user,
                                interface=item,
                                source_type='llm',
                                **payload,
                            )
                        )
                    yield sse_bytes(
                        {
                            'response_type': 'saved',
                            'content': f'已生成 {len(created)} 条测试用例',
                            'count': len(created),
                            'items': [{'id': row.id, 'name': row.name, 'case_type': row.case_type} for row in created],
                            'done': True,
                        }
                    )
                    return
                yield sse_bytes(event)
        except ValueError as extra:
            yield sse_bytes({'response_type': 'error', 'content': user_facing_error(extra, '生成测试用例失败'), 'done': True})
        except Exception:
            yield sse_bytes({'response_type': 'error', 'content': '生成测试用例失败', 'done': True})

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['GET', 'POST'])
def case_list_create(request):
    if request.method == 'GET':
        queryset = ApiTestCase.objects.filter(user=request.user).select_related('interface')
        interface_id = request.query_params.get('interface_id')
        if interface_id:
            queryset = queryset.filter(interface_id=interface_id)
        keyword = (request.query_params.get('keyword') or '').strip()
        if keyword:
            queryset = queryset.filter(Q(name__icontains=keyword) | Q(description__icontains=keyword))
        total = queryset.count()
        page, page_size = parse_page_params(request)
        start = (page - 1) * page_size
        items = queryset[start : start + page_size]
        return ok(
            {
                'items': ApiTestCaseSerializer(items, many=True).data,
                'total': total,
                'page': page,
                'page_size': page_size,
            }
        )

    serializer = ApiTestCaseSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    data = serializer.validated_data
    item = ApiTestCase.objects.create(
        user=request.user,
        interface_id=data['interface_id'],
        name=data['name'],
        priority=data.get('priority') or 'P2',
        case_type=data.get('case_type') or '',
        description=data.get('description') or '',
        preconditions=data.get('preconditions') or '',
        request_headers=data.get('request_headers') or [],
        request_query=data.get('request_query') or [],
        request_body=data.get('request_body') or '',
        expected_status=data.get('expected_status') or '200',
        expected_body=data.get('expected_body') or '',
        assertions=data.get('assertions') or [],
        source_type='manual',
    )
    return ok(ApiTestCaseSerializer(item).data, msg='用例创建成功', http_status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def case_detail(request, pk):
    item = ApiTestCase.objects.filter(pk=pk, user=request.user).select_related('interface').first()
    if item is None:
        return fail('用例不存在', http_status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return ok(ApiTestCaseSerializer(item).data)
    if request.method == 'DELETE':
        item.delete()
        return ok(msg='已删除')
    serializer = ApiTestCaseSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    data = serializer.validated_data
    item.interface_id = data['interface_id']
    item.name = data['name']
    item.priority = data.get('priority') or item.priority
    if 'case_type' in data:
        item.case_type = data.get('case_type') or ''
    if 'description' in data:
        item.description = data.get('description') or ''
    if 'preconditions' in data:
        item.preconditions = data.get('preconditions') or ''
    if 'request_headers' in data:
        item.request_headers = data.get('request_headers') or []
    if 'request_query' in data:
        item.request_query = data.get('request_query') or []
    if 'request_body' in data:
        item.request_body = data.get('request_body') or ''
    if 'expected_status' in data:
        item.expected_status = data.get('expected_status') or ''
    if 'expected_body' in data:
        item.expected_body = data.get('expected_body') or ''
    if 'assertions' in data:
        item.assertions = data.get('assertions') or []
    item.save()
    return ok(ApiTestCaseSerializer(item).data, msg='用例已更新')


def _kv_rows(rows):
    return rows if isinstance(rows, list) else []


def build_run_payload(case):
    interface = case.interface
    dataset = (
        ApiInterfaceData.objects.filter(user=case.user, interface=interface)
        .order_by('-id')
        .first()
    )
    body = (case.request_body or '').strip()
    if not body and dataset is not None:
        body = json.dumps(dataset.payload, ensure_ascii=False) if not isinstance(dataset.payload, str) else dataset.payload
    return {
        'case_id': case.id,
        'case_name': case.name,
        'method': interface.method,
        'url': interface.url or interface.path,
        'path': interface.path,
        'headers': _kv_rows(interface.headers),
        'query': _kv_rows(interface.query_params),
        'request_headers': _kv_rows(case.request_headers),
        'request_query': _kv_rows(case.request_query),
        'body': body,
        'auth_type': interface.auth_type,
        'auth_config': interface.auth_config or {},
        'timeout': max(1, (interface.timeout_ms or 30000) / 1000),
        'expected_status': case.expected_status,
        'expected_body': case.expected_body,
        'assertions': case.assertions or [],
        'cookies': _kv_rows(interface.cookies),
        'setup_script': interface.setup_script or '',
        'teardown_script': interface.teardown_script or '',
        'path_params': _kv_rows(interface.path_params),
        'retry_times': 3,
        'retry_delay': 1,
        'dataset_id': dataset.id if dataset else None,
    }


@api_view(['POST'])
def case_run(request, pk):
    item = ApiTestCase.objects.filter(pk=pk, user=request.user).select_related('interface').first()
    if item is None:
        return fail('用例不存在', http_status=status.HTTP_404_NOT_FOUND)
    payload = build_run_payload(item)
    if not payload.get('url'):
        return fail('接口缺少请求地址')
    try:
        result = run_api_case(request.user.id, payload, timeout=60)
    except ApiTestServiceError as exc:
        return fail(exc.message, http_status=status.HTTP_502_BAD_GATEWAY)
    data = result.get('data') if isinstance(result, dict) else result
    passed = bool(data and data.get('passed'))
    persist_single_run(request.user, item, data or {})
    msg = result.get('msg') if isinstance(result, dict) else ('接口测试执行成功' if passed else '接口测试执行失败')
    return ok(public_run_data(data or {}), msg=msg)


@api_view(['GET'])
def case_run_logs(request, pk):
    item = ApiTestCase.objects.filter(pk=pk, user=request.user).first()
    if item is None:
        return fail('用例不存在', http_status=status.HTTP_404_NOT_FOUND)
    queryset = item.run_logs.filter(user=request.user)
    run_id = (request.query_params.get('run_id') or '').strip()
    if run_id:
        queryset = queryset.filter(run_id=run_id)
    rows = [
        {
            'id': log.id,
            'run_id': log.run_id,
            'event': log.event,
            'outcome': log.outcome,
            'test_name': '',
            'message': '' if log.message in ('failed', 'error', 'passed') else log.message,
            'screenshot_path': '',
            'extra': log.extra,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        for log in queryset.order_by('id')[:500]
    ]
    return ok({'items': rows, 'total': len(rows)})
