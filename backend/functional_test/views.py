from pathlib import Path
from utils.user_errors import user_facing_error

from django.db.models import Count, Prefetch
from django.db.models.functions import Substr
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from ai_testcase.generator import sse_bytes
from system.llm import (
    resolve_embedding_client,
    resolve_llm_client,
    resolve_rerank_client,
    resolve_vision_client,
)

from .ai_service_client import (
    AIServiceError,
    ingest_document as ai_ingest_document,
    iter_generate_stream,
    serialize_embedding_client,
    serialize_llm_client,
    serialize_rerank_client,
    serialize_vision_client,
)
from .kb_sync import (
    extract_requirement_text,
    get_or_create_default_testcase_kb,
    get_or_create_project_requirement_kb,
    requirement_document_already_ingested,
)
from .models import FunctionalProject, FunctionalTestCase, RequirementDocument, TestCaseGeneration
from .serializers import (
    CreateFunctionalProjectSerializer,
    CreateRequirementDocumentSerializer,
    FunctionalProjectSerializer,
    FunctionalTestCaseListSerializer,
    FunctionalTestCaseSerializer,
    GenerateRequirementSerializer,
    format_local_datetime,
    RequirementDocumentSerializer,
    UpdateFunctionalProjectSerializer,
    UpdateRequirementDocumentSerializer,
)
from .testcase_excel import attachment_content_disposition, build_testcase_workbook, testcase_export_filename
from .testcase_store import persist_generation_result


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


def owned_project(user, pk):
    return FunctionalProject.objects.filter(pk=pk, user=user).first()


def project_queryset(user, with_requirements=False):
    queryset = FunctionalProject.objects.filter(user=user).select_related('user').annotate(
        requirement_count=Count('requirements', distinct=True),
    )
    if with_requirements:
        queryset = queryset.prefetch_related(
            Prefetch(
                'requirements',
                queryset=RequirementDocument.objects.select_related('user').order_by('-id'),
            )
        )
    return queryset


def testcase_queryset(user):
    return FunctionalTestCase.objects.filter(user=user).select_related(
        'project',
        'requirement',
        'user',
    )


def apply_testcase_filters(queryset, request):
    project_id = request.query_params.get('project_id')
    requirement_id = request.query_params.get('requirement_id')
    generation_id = request.query_params.get('generation_id')
    if project_id:
        queryset = queryset.filter(project_id=project_id)
    if requirement_id:
        queryset = queryset.filter(requirement_id=requirement_id)
    if generation_id:
        queryset = queryset.filter(generation_id=generation_id)
    return queryset


LIST_PREVIEW_LEN = 241


def testcase_list_page(queryset, start, page_size):
    return queryset.select_related('project', 'requirement', 'user').defer(
        'precondition',
        'steps',
        'expected_result',
    ).annotate(
        _precondition_preview=Substr('precondition', 1, LIST_PREVIEW_LEN),
        _steps_preview=Substr('steps', 1, LIST_PREVIEW_LEN),
        _expected_preview=Substr('expected_result', 1, LIST_PREVIEW_LEN),
    )[start : start + page_size]


def delete_owned_testcases(user, ids):
    qs = FunctionalTestCase.objects.filter(user=user, pk__in=ids)
    count = qs.count()
    qs.delete()
    return count


def _serialize_testcase_rows(queryset):
    rows = []
    for item in queryset:
        data = FunctionalTestCaseSerializer(item).data
        data['created_at'] = format_local_datetime(item.created_at)
        rows.append(data)
    return rows


def _save_generation_or_fail(
    *,
    user,
    project,
    document,
    query,
    answer,
    thinking,
    references,
    llm_config_id,
    status=TestCaseGeneration.STATUS_COMPLETED,
    feature_points=None,
    test_directions=None,
):
    generation, case_count = persist_generation_result(
        user=user,
        project=project,
        requirement=document,
        query=query,
        answer=answer,
        thinking=thinking,
        references=references,
        feature_points=feature_points,
        test_directions=test_directions,
        llm_config_id=llm_config_id,
        status=status,
    )
    return generation, case_count


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


@api_view(['GET'])
def testcase_list(request):
    queryset = apply_testcase_filters(
        FunctionalTestCase.objects.filter(user=request.user),
        request,
    ).order_by('-created_at', 'sort_order', 'id')
    total = queryset.count()
    page, page_size = parse_page_params(request)
    start = (page - 1) * page_size
    items = testcase_list_page(queryset, start, page_size)
    return ok(
        {
            'items': FunctionalTestCaseListSerializer(items, many=True).data,
            'total': total,
            'page': page,
            'page_size': page_size,
        },
        msg='查询成功',
    )


@api_view(['GET', 'DELETE'])
def testcase_detail(request, pk):
    item = testcase_queryset(request.user).filter(pk=pk).first()
    if item is None:
        return fail('用例不存在', http_status=status.HTTP_404_NOT_FOUND)
    if request.method == 'DELETE':
        item_id = item.id
        item.delete()
        return ok({'id': item_id, 'deleted': 1}, msg='删除成功')
    return ok(FunctionalTestCaseSerializer(item).data, msg='查询成功')


@api_view(['POST'])
def testcase_batch_delete(request):
    raw_ids = request.data.get('ids') if isinstance(request.data, dict) else None
    ids = []
    for item in raw_ids or []:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    ids = list(dict.fromkeys(ids))
    if not ids:
        return fail('请选择要删除的用例')
    deleted = delete_owned_testcases(request.user, ids)
    if deleted <= 0:
        return fail('没有可删除的测试用例')
    return ok({'deleted': deleted}, msg=f'已删除 {deleted} 条用例')


@api_view(['GET'])
def testcase_export(request):
    queryset = apply_testcase_filters(testcase_queryset(request.user), request).order_by(
        '-created_at',
        'sort_order',
        'id',
    )
    if not queryset.exists():
        return fail('没有可导出的测试用例')

    filename = testcase_export_filename(queryset)
    content = build_testcase_workbook(_serialize_testcase_rows(queryset))
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = attachment_content_disposition(filename)
    return response


@api_view(['GET', 'POST'])
def project_list_create(request):
    if request.method == 'GET':
        queryset = project_queryset(request.user, with_requirements=True)
        return ok(FunctionalProjectSerializer(queryset, many=True).data, msg='查询成功')

    serializer = CreateFunctionalProjectSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    project = FunctionalProject.objects.create(
        user=request.user,
        name=serializer.validated_data['name'].strip(),
        description=(serializer.validated_data.get('description') or '').strip(),
    )
    project = project_queryset(request.user, with_requirements=True).filter(pk=project.pk).first()
    return ok(FunctionalProjectSerializer(project).data, msg='项目创建成功', http_status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT'])
def project_detail(request, pk):
    project = project_queryset(request.user, with_requirements=True).filter(pk=pk).first()
    if project is None:
        return fail('项目不存在', http_status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return ok(FunctionalProjectSerializer(project).data, msg='查询成功')

    serializer = UpdateFunctionalProjectSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    project.name = serializer.validated_data['name'].strip()
    project.description = (serializer.validated_data.get('description') or '').strip()
    project.save(update_fields=['name', 'description', 'updated_at'])
    project = project_queryset(request.user, with_requirements=True).filter(pk=project.pk).first()
    return ok(FunctionalProjectSerializer(project).data, msg='项目修改成功')


@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def project_requirements(request, pk):
    project = owned_project(request.user, pk)
    if project is None:
        return fail('项目不存在', http_status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        queryset = RequirementDocument.objects.filter(project=project).order_by('-id')
        return ok(RequirementDocumentSerializer(queryset, many=True).data, msg='查询成功')

    serializer = CreateRequirementDocumentSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))

    uploaded = serializer.validated_data['file']
    filename = (getattr(uploaded, 'name', None) or 'document').strip()
    title = (serializer.validated_data.get('title') or '').strip() or Path(filename).stem
    document = RequirementDocument.objects.create(
        project=project,
        user=request.user,
        title=title,
        source_filename=filename,
        file=uploaded,
    )
    return ok(RequirementDocumentSerializer(document).data, msg='需求上传成功', http_status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
def project_requirement_detail(request, pk, doc_id):
    project = owned_project(request.user, pk)
    if project is None:
        return fail('项目不存在', http_status=status.HTTP_404_NOT_FOUND)

    document = RequirementDocument.objects.filter(pk=doc_id, project=project).first()
    if document is None:
        return fail('需求文档不存在', http_status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = UpdateRequirementDocumentSerializer(data=request.data)
        if not serializer.is_valid():
            return fail(first_error_msg(serializer.errors))
        document.title = serializer.validated_data['title']
        document.save(update_fields=['title'])
        return ok(RequirementDocumentSerializer(document).data, msg='修改成功')

    if document.file:
        document.file.delete(save=False)
    document.delete()
    return ok(msg='删除成功')


@api_view(['POST'])
def requirement_generate(request, pk, doc_id):
    project = owned_project(request.user, pk)
    if project is None:
        return fail('项目不存在', http_status=status.HTTP_404_NOT_FOUND)

    document = RequirementDocument.objects.filter(pk=doc_id, project=project, user=request.user).first()
    if document is None:
        return fail('需求文档不存在', http_status=status.HTTP_404_NOT_FOUND)

    serializer = GenerateRequirementSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))

    try:
        requirement_kb = get_or_create_project_requirement_kb(request.user, project)
        testcase_kb = get_or_create_default_testcase_kb(request.user)
        if not requirement_document_already_ingested(document, requirement_kb):
            title = (document.title or '').strip() or document.source_filename
            content_text = extract_requirement_text(document)
            embedder = resolve_embedding_client(request.user)
            ai_ingest_document(
                request.user.id,
                requirement_kb.id,
                title=title,
                content_text=content_text,
                source_filename=document.source_filename,
                embedding_config=serialize_embedding_client(embedder),
            )
    except ValueError as exc:
        return fail(user_facing_error(exc, '需求文档入库失败'))
    except AIServiceError as exc:
        return fail(exc.message, http_status=exc.status_code if exc.status_code in (400, 502, 503) else 502)
    except Exception:
        return fail('需求文档入库失败')
    title = (document.title or document.source_filename or '需求文档').strip()
    query = serializer.validated_data.get('query') or f'请根据《{title}》生成完整功能测试用例，覆盖主流程与异常场景。'

    try:
        llm = resolve_llm_client(request.user, serializer.validated_data.get('llm_config_id'))
    except LookupError:
        return fail('模型配置不存在', http_status=status.HTTP_404_NOT_FOUND)

    embedder = resolve_embedding_client(request.user)
    reranker = resolve_rerank_client(request.user)
    vision = resolve_vision_client(request.user)
    llm_config = serialize_llm_client(llm)
    embedding_config = serialize_embedding_client(embedder)
    rerank_config = serialize_rerank_client(reranker)
    vision_config = serialize_vision_client(vision)
    file_path = None
    if document.file:
        try:
            file_path = document.file.path
        except Exception:
            file_path = None

    if serializer.validated_data.get('stream'):
        llm_config_id = serializer.validated_data.get('llm_config_id')

        def event_stream():
            answer_parts = []
            thinking = ''
            references = []
            feature_points = []
            test_directions = []
            failed = False
            error_sent = False

            def emit_error(message):
                nonlocal failed, error_sent
                failed = True
                if error_sent:
                    return
                error_sent = True
                yield sse_bytes({
                    'response_type': 'error',
                    'content': message,
                    'done': True,
                })

            yield sse_bytes({
                'response_type': 'pipeline',
                'step': 'prepare',
                'step_label': '准备',
                'status': 'running',
                'content': '需求入库完成，正在启动 AI 流水线…',
                'done': False,
            })
            try:
                for event in iter_generate_stream(
                    request.user.id,
                    query,
                    requirement_kb.id,
                    testcase_kb.id,
                    llm_config=llm_config,
                    embedding_config=embedding_config,
                    rerank_config=rerank_config,
                    vision_config=vision_config,
                    file_path=file_path,
                    pipeline=True,
                ):
                    kind = event.get('response_type')
                    if kind == 'thinking':
                        thinking = event.get('content') or thinking
                    elif kind == 'references':
                        references = event.get('knowledge_references') or []
                    elif kind == 'answer':
                        answer_parts.append(event.get('content') or '')
                    elif kind == 'feature_points':
                        feature_points = event.get('items') or []
                    elif kind == 'test_directions':
                        test_directions = event.get('items') or []
                    elif kind == 'error':
                        failed = True
                        error_sent = True
                    elif kind == 'pipeline' and event.get('status') == 'error':
                        failed = True
                    yield sse_bytes(event)
            except AIServiceError as exc:
                for item in emit_error(exc.message):
                    yield item
            except Exception as exc:
                for item in emit_error(f'生成服务异常：{exc}'):
                    yield item
            else:
                if not error_sent and not answer_parts:
                    for item in emit_error('生成流程已结束，但未收到用例内容，请检查 AI 服务配置后重试'):
                        yield item
            finally:
                answer = ''.join(answer_parts).strip()
                if answer:
                    generation, case_count = _save_generation_or_fail(
                        user=request.user,
                        project=project,
                        document=document,
                        query=query,
                        answer=answer,
                        thinking=thinking,
                        references=references,
                        feature_points=feature_points,
                        test_directions=test_directions,
                        llm_config_id=llm_config_id,
                        status=TestCaseGeneration.STATUS_FAILED if failed else TestCaseGeneration.STATUS_COMPLETED,
                    )
                    yield sse_bytes({
                        'response_type': 'saved',
                        'content': '',
                        'done': True,
                        'generation_id': generation.id,
                        'case_count': case_count,
                        'project_id': project.id,
                        'requirement_id': document.id,
                        'failed': failed,
                    })
                elif failed and not error_sent:
                    for item in emit_error('生成失败，未保存任何用例'):
                        yield item

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    answer_parts = []
    thinking = ''
    references = []
    feature_points = []
    test_directions = []
    failed = False
    try:
        for event in iter_generate_stream(
            request.user.id,
            query,
            requirement_kb.id,
            testcase_kb.id,
            llm_config=llm_config,
            embedding_config=embedding_config,
            rerank_config=rerank_config,
            vision_config=vision_config,
            file_path=file_path,
            pipeline=True,
        ):
            kind = event.get('response_type')
            if kind == 'thinking':
                thinking = event.get('content') or thinking
            elif kind == 'references':
                references = event.get('knowledge_references') or []
            elif kind == 'answer':
                answer_parts.append(event.get('content') or '')
            elif kind == 'feature_points':
                feature_points = event.get('items') or []
            elif kind == 'test_directions':
                test_directions = event.get('items') or []
            elif kind == 'error':
                failed = True
                return fail(event.get('content') or '生成失败', http_status=502)
    except AIServiceError as exc:
        return fail(exc.message, http_status=exc.status_code if exc.status_code in (400, 502, 503) else 502)

    answer = ''.join(answer_parts).strip()
    generation, case_count = _save_generation_or_fail(
        user=request.user,
        project=project,
        document=document,
        query=query,
        answer=answer,
        thinking=thinking,
        references=references,
        feature_points=feature_points,
        test_directions=test_directions,
        llm_config_id=serializer.validated_data.get('llm_config_id'),
        status=TestCaseGeneration.STATUS_FAILED if failed else TestCaseGeneration.STATUS_COMPLETED,
    )

    result = {
        'message_id': '',
        'answer': answer,
        'thinking': thinking,
        'references': references,
        'query': query,
        'requirement_id': document.id,
        'project_id': project.id,
        'requirement_kb_id': requirement_kb.id,
        'testcase_kb_id': testcase_kb.id,
        'generation_id': generation.id,
        'case_count': case_count,
    }
    return ok(result, msg='生成成功')
