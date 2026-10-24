from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from system.llm import resolve_llm_client
from utils.user_errors import user_facing_error

from .generate_cases import generate_agent_cases
from .models import AgentProject, AgentProjectProfile, AgentTestCase, AgentTestRun
from .runner import build_dialogue_turns, run_agent_case
from .serializers import (
    AgentProjectProfileUpdateSerializer,
    AgentProjectSerializer,
    AgentProjectWriteSerializer,
    AgentTestCaseSerializer,
    AgentTestRunDetailSerializer,
    AgentTestRunListSerializer,
    format_local_datetime,
)
from .understand import generate_understanding


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
    return AgentProject.objects.filter(pk=pk, user=user).select_related('profile').first()


def save_profile_failure(project, message):
    profile, _ = AgentProjectProfile.objects.get_or_create(project=project)
    profile.error_message = (message or '')[:512]
    profile.save(update_fields=['error_message', 'updated_at'])
    project.understand_status = AgentProject.STATUS_FAILED
    project.save(update_fields=['understand_status', 'updated_at'])
    return profile


@api_view(['GET', 'POST'])
def project_list_create(request):
    if request.method == 'GET':
        queryset = (
            AgentProject.objects.filter(user=request.user)
            .select_related('profile')
            .annotate(case_count=Count('test_cases'))
            .order_by('-id')
        )
        return ok(AgentProjectSerializer(queryset, many=True).data, msg='查询成功')

    serializer = AgentProjectWriteSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))
    project = AgentProject.objects.create(
        user=request.user,
        name=serializer.validated_data['name'],
        path=serializer.validated_data['path'],
        agent_url=serializer.validated_data.get('agent_url') or 'http://127.0.0.1:3001',
        buried_point_url=serializer.validated_data.get('buried_point_url') or 'http://127.0.0.1:5000',
        understand_status=AgentProject.STATUS_PENDING,
    )
    project = owned_project(request.user, project.pk)
    return ok(AgentProjectSerializer(project).data, msg='项目创建成功', http_status=status.HTTP_201_CREATED)


@api_view(['GET'])
def project_detail(request, pk):
    project = owned_project(request.user, pk)
    if project is None:
        return fail('项目不存在', http_status=status.HTTP_404_NOT_FOUND)
    return ok(AgentProjectSerializer(project).data, msg='查询成功')


@api_view(['POST'])
def project_understand(request, pk):
    project = owned_project(request.user, pk)
    if project is None:
        return fail('项目不存在', http_status=status.HTTP_404_NOT_FOUND)
    if project.understand_status == AgentProject.STATUS_RUNNING:
        return fail('项目正在理解中，请稍后再试')

    try:
        llm = resolve_llm_client(request.user, request.data.get('llm_config_id') if isinstance(request.data, dict) else None)
    except LookupError as exc:
        return fail(str(exc))
    if llm is None:
        return fail('请先在「模型配置」中添加对话模型')

    project.understand_status = AgentProject.STATUS_RUNNING
    project.save(update_fields=['understand_status', 'updated_at'])

    try:
        content = generate_understanding(llm, name=project.name, path=project.path)
    except Exception as exc:
        message = user_facing_error(exc, '生成项目理解失败')
        save_profile_failure(project, message)
        return fail(message)

    with transaction.atomic():
        profile, created = AgentProjectProfile.objects.select_for_update().get_or_create(project=project)
        profile.content = content
        profile.source = AgentProjectProfile.SOURCE_LLM
        profile.llm_model = getattr(llm, 'model', '') or ''
        if isinstance(request.data, dict) and request.data.get('llm_config_id') not in (None, ''):
            try:
                profile.llm_config_id = int(request.data.get('llm_config_id'))
            except (TypeError, ValueError):
                profile.llm_config_id = None
        profile.error_message = ''
        if not created:
            profile.content_version = (profile.content_version or 1) + 1
        profile.save()
        project.understand_status = AgentProject.STATUS_DONE
        project.save(update_fields=['understand_status', 'updated_at'])

    project = owned_project(request.user, project.pk)
    return ok(AgentProjectSerializer(project).data, msg='项目理解已生成')


@api_view(['PUT'])
def project_profile_update(request, pk):
    project = owned_project(request.user, pk)
    if project is None:
        return fail('项目不存在', http_status=status.HTTP_404_NOT_FOUND)

    serializer = AgentProjectProfileUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return fail(first_error_msg(serializer.errors))

    with transaction.atomic():
        profile, _ = AgentProjectProfile.objects.select_for_update().get_or_create(project=project)
        profile.content = serializer.validated_data['content']
        profile.source = AgentProjectProfile.SOURCE_MANUAL
        profile.error_message = ''
        profile.content_version = (profile.content_version or 1) + 1
        profile.save()
        project.understand_status = AgentProject.STATUS_DONE
        project.save(update_fields=['understand_status', 'updated_at'])

    project = owned_project(request.user, project.pk)
    return ok(AgentProjectSerializer(project).data, msg='项目理解已保存')


@api_view(['POST'])
def project_generate_cases(request, pk):
    project = owned_project(request.user, pk)
    if project is None:
        return fail('项目不存在', http_status=status.HTTP_404_NOT_FOUND)
    if project.understand_status != AgentProject.STATUS_DONE:
        return fail('请先完成「理解项目」，再生成测试用例')
    try:
        profile_content = project.profile.content
    except AgentProjectProfile.DoesNotExist:
        profile_content = ''
    if not (profile_content or '').strip():
        return fail('项目理解文案为空，请先理解或编辑项目理解')

    try:
        llm = resolve_llm_client(request.user, request.data.get('llm_config_id') if isinstance(request.data, dict) else None)
    except LookupError as exc:
        return fail(str(exc))
    if llm is None:
        return fail('请先在「模型配置」中添加对话模型')

    try:
        generated = generate_agent_cases(
            llm,
            name=project.name,
            path=project.path,
            profile=profile_content,
        )
    except Exception as exc:
        return fail(user_facing_error(exc, '生成测试用例失败'))

    rows = [
        AgentTestCase(
            user=request.user,
            project=project,
            task_name=item['task_name'],
            session_id=item['session_id'],
            tool_chain=item['tool_chain'],
            knowledge_base=item['knowledge_base'],
            expected_result=item['expected_result'],
            verify_status=AgentTestCase.VERIFY_PENDING,
            score=None,
            level=item['level'],
            test_reason=item['test_reason'],
            dimensions=item['dimensions'],
            user_input=item['user_input'],
            source_type='llm',
        )
        for item in generated
    ]
    AgentTestCase.objects.bulk_create(rows)
    created = list(
        AgentTestCase.objects.filter(user=request.user, project=project).order_by('-id')[: len(rows)]
    )
    created.reverse()
    return ok(
        {
            'project_id': project.id,
            'count': len(created),
            'items': AgentTestCaseSerializer(created, many=True).data,
        },
        msg=f'已生成 {len(created)} 条测试用例',
        http_status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
def case_list(request):
    queryset = AgentTestCase.objects.filter(user=request.user).select_related('project').order_by('-id')
    project_id = request.query_params.get('project_id')
    if project_id:
        queryset = queryset.filter(project_id=project_id)
    keyword = (request.query_params.get('keyword') or '').strip()
    if keyword:
        queryset = queryset.filter(task_name__icontains=keyword)
    try:
        page = max(1, int(request.query_params.get('page') or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get('page_size') or 20)
    except (TypeError, ValueError):
        page_size = 20
    if page_size not in {10, 20, 50}:
        page_size = 20
    total = queryset.count()
    start = (page - 1) * page_size
    items = queryset[start : start + page_size]
    return ok(
        {
            'items': AgentTestCaseSerializer(items, many=True).data,
            'total': total,
            'page': page,
            'page_size': page_size,
        },
        msg='查询成功',
    )


@api_view(['POST'])
def case_run(request, pk):
    """真实执行：JSON-RPC 调用 Agent + 埋点 /logs|/traces|/summary 校验工具链。"""
    item = AgentTestCase.objects.filter(pk=pk, user=request.user).select_related('project').first()
    if item is None:
        return fail('用例不存在', http_status=status.HTTP_404_NOT_FOUND)
    project = item.project
    agent_url = (project.agent_url or '').strip() or 'http://127.0.0.1:3001'
    buried_url = (project.buried_point_url or '').strip() or 'http://127.0.0.1:5000'

    try:
        result = run_agent_case(
            user_input=item.user_input or item.task_name,
            tool_chain=item.tool_chain or '',
            expected_result=item.expected_result or '',
            agent_url=agent_url,
            buried_point_url=buried_url,
            timeout=120,
        )
    except Exception as exc:  # noqa: BLE001
        return fail(user_facing_error(exc, fallback='用例执行失败'))

    now = timezone.now()
    item.verify_status = result['verify_status']
    item.score = result['score']
    item.last_run_at = now
    item.last_run_result = result['last_run_result']
    item.last_run_detail = result['detail']
    item.save(
        update_fields=[
            'verify_status',
            'score',
            'last_run_at',
            'last_run_result',
            'last_run_detail',
            'updated_at',
        ]
    )
    run = AgentTestRun.objects.create(
        user=request.user,
        project=project,
        case=item,
        request_id=result['request_id'],
        verify_status=result['verify_status'],
        score=result['score'],
        elapsed_ms=result['elapsed_ms'],
        summary=result['summary'],
        detail=result['detail'],
    )
    data = AgentTestCaseSerializer(item, context={'include_detail': True}).data
    data['run_id'] = run.id
    msg = '执行通过' if result['verify_status'] == AgentTestCase.VERIFY_PASSED else '执行完成（未通过）'
    return ok(data, msg=msg)


@api_view(['GET'])
def case_last_run_detail(request, pk):
    """获取用例最近一次完整执行详情（点击展开用）。"""
    item = AgentTestCase.objects.filter(pk=pk, user=request.user).first()
    if item is None:
        return fail('用例不存在', http_status=status.HTTP_404_NOT_FOUND)
    detail = item.last_run_detail or {}
    actual_answer = ''
    if isinstance(detail, dict):
        actual_answer = detail.get('actual_answer') or ''
        if not actual_answer:
            chat = detail.get('chat_result') or {}
            if isinstance(chat, dict):
                actual_answer = chat.get('response') or chat.get('answer') or ''
    return ok(
        {
            'case_id': item.id,
            'task_name': item.task_name,
            'user_input': item.user_input,
            'dialogue_turns': build_dialogue_turns(item.user_input or '', detail),
            'verify_status': item.verify_status,
            'verify_status_label': item.get_verify_status_display(),
            'score': item.score,
            'last_run_at': format_local_datetime(item.last_run_at),
            'last_run_result': item.last_run_result,
            'last_run_output': actual_answer,
            'last_run_detail': detail,
        },
        msg='查询成功',
    )


@api_view(['GET'])
def report_list(request):
    """执行报告列表（不含完整 detail，点击后再拉详情）。"""
    queryset = (
        AgentTestRun.objects.filter(user=request.user)
        .select_related('project', 'case')
        .order_by('-id')
    )
    project_id = request.query_params.get('project_id')
    if project_id:
        try:
            queryset = queryset.filter(project_id=int(project_id))
        except (TypeError, ValueError):
            pass
    try:
        page = max(1, int(request.query_params.get('page') or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(100, max(1, int(request.query_params.get('page_size') or 20)))
    except (TypeError, ValueError):
        page_size = 20
    total = queryset.count()
    start = (page - 1) * page_size
    items = queryset[start : start + page_size]
    return ok(
        {
            'items': AgentTestRunListSerializer(items, many=True).data,
            'total': total,
            'page': page,
            'page_size': page_size,
        },
        msg='查询成功',
    )


@api_view(['GET'])
def report_detail(request, pk):
    """单次执行完整详情（含埋点 flow / logs / traces / summary）。"""
    run = (
        AgentTestRun.objects.filter(pk=pk, user=request.user)
        .select_related('project', 'case')
        .first()
    )
    if run is None:
        return fail('报告不存在', http_status=status.HTTP_404_NOT_FOUND)
    return ok(AgentTestRunDetailSerializer(run).data, msg='查询成功')
