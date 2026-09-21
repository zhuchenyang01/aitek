from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view

from functional_test.models import FunctionalProject
from functional_test.serializers import format_local_datetime

from .models import ApiTestCase, ApiTestRun, ApiTestSuite, ApiTestSuiteStep
from .user_errors import public_run_data, public_run_step
from .run_persist import persist_suite_run
from .service_client import ApiTestServiceError, run_api_suite
from .views import build_run_payload, fail, ok, parse_page_params


def _suite_payload(suite):
    steps = []
    for step in suite.steps.select_related('case').all():
        steps.append(
            {
                'id': step.id,
                'order': step.order,
                'case_id': step.case_id,
                'case_name': step.case.name if step.case_id else '',
                'extractors': step.extractors or [],
            }
        )
    return {
        'id': suite.id,
        'project_id': suite.project_id,
        'project_name': suite.project.name if suite.project_id else '',
        'name': suite.name,
        'description': suite.description,
        'steps': steps,
        'created_at': format_local_datetime(suite.created_at),
        'updated_at': format_local_datetime(suite.updated_at),
    }


def _replace_steps(suite, user, steps):
    suite.steps.all().delete()
    for index, item in enumerate(steps or [], 1):
        if not isinstance(item, dict):
            continue
        case_id = item.get('case_id')
        case = ApiTestCase.objects.filter(pk=case_id, user=user).first()
        if case is None:
            continue
        ApiTestSuiteStep.objects.create(
            suite=suite,
            case=case,
            order=int(item.get('order') or index),
            extractors=item.get('extractors') or [],
        )


@api_view(['GET', 'POST'])
def suite_list_create(request):
    if request.method == 'GET':
        queryset = ApiTestSuite.objects.filter(user=request.user).select_related('project')
        project_id = request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        keyword = (request.query_params.get('keyword') or '').strip()
        if keyword:
            queryset = queryset.filter(Q(name__icontains=keyword))
        total = queryset.count()
        page, page_size = parse_page_params(request)
        start = (page - 1) * page_size
        items = [_suite_payload(item) for item in queryset[start : start + page_size]]
        return ok({'items': items, 'total': total, 'page': page, 'page_size': page_size})

    name = (request.data.get('name') or '').strip()
    project_id = request.data.get('project_id')
    if not name:
        return fail('请填写套件名称')
    project = FunctionalProject.objects.filter(pk=project_id, user=request.user).first()
    if project is None:
        return fail('项目不存在')
    suite = ApiTestSuite.objects.create(
        user=request.user,
        project=project,
        name=name,
        description=request.data.get('description') or '',
    )
    _replace_steps(suite, request.user, request.data.get('steps') or [])
    return ok(_suite_payload(suite), msg='套件已创建', http_status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def suite_detail(request, pk):
    suite = ApiTestSuite.objects.filter(pk=pk, user=request.user).select_related('project').first()
    if suite is None:
        return fail('套件不存在', http_status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return ok(_suite_payload(suite))
    if request.method == 'DELETE':
        suite.delete()
        return ok(msg='已删除')
    name = (request.data.get('name') or '').strip()
    if name:
        suite.name = name
    suite.description = request.data.get('description') or ''
    project_id = request.data.get('project_id')
    if project_id:
        project = FunctionalProject.objects.filter(pk=project_id, user=request.user).first()
        if project is None:
            return fail('项目不存在')
        suite.project = project
    suite.save()
    if 'steps' in request.data:
        _replace_steps(suite, request.user, request.data.get('steps') or [])
    return ok(_suite_payload(suite), msg='套件已更新')


@api_view(['POST'])
def suite_run(request, pk):
    suite = ApiTestSuite.objects.filter(pk=pk, user=request.user).select_related('project').first()
    if suite is None:
        return fail('套件不存在', http_status=status.HTTP_404_NOT_FOUND)
    steps = list(suite.steps.select_related('case', 'case__interface').all())
    if not steps:
        return fail('套件没有步骤')
    payload_steps = []
    for step in steps:
        spec = build_run_payload(step.case)
        if not spec.get('url'):
            return fail(f'步骤「{step.case.name}」缺少请求地址')
        payload_steps.append(
            {
                'case_id': step.case_id,
                'extractors': step.extractors or [],
                'spec': spec,
            }
        )
    try:
        result = run_api_suite(request.user.id, {'steps': payload_steps}, timeout=180)
    except ApiTestServiceError as exc:
        return fail(exc.message, http_status=status.HTTP_502_BAD_GATEWAY)
    data = result.get('data') if isinstance(result, dict) else result
    persist_suite_run(request.user, suite, data or {})
    msg = result.get('msg') if isinstance(result, dict) else ('套件执行成功' if (data or {}).get('passed') else '套件执行失败')
    return ok(public_run_data(data or {}), msg=msg)


def _run_payload(run, with_steps=False):
    payload = {
        'id': run.id,
        'name': run.name,
        'status': run.status,
        'total': run.total,
        'passed': run.passed,
        'failed': run.failed,
        'skipped': run.skipped,
        'pass_rate': run.pass_rate,
        'summary': run.summary,
        'suite_id': run.suite_id,
        'case_id': run.case_id,
        'project_id': run.project_id,
        'service_run_id': run.service_run_id,
        'started_at': format_local_datetime(run.started_at),
        'finished_at': format_local_datetime(run.finished_at) if run.finished_at else '',
    }
    if with_steps:
        payload['steps'] = [
            public_run_step(
                {
                    'id': item.id,
                    'step_index': item.step_index,
                    'case_id': item.case_id,
                    'case_name': item.case_name,
                    'passed': item.passed,
                    'http': item.http,
                    'extracts': item.extracts,
                    'assertion_logs': item.assertion_logs,
                    'result_logs': item.result_logs,
                    'screenshots': [],
                    'failures': item.failures,
                }
            )
            for item in run.step_results.all()
        ]
    return payload


@api_view(['GET'])
def run_list(request):
    queryset = ApiTestRun.objects.filter(user=request.user, suite_id__isnull=False)
    keyword = (request.query_params.get('keyword') or '').strip()
    if keyword:
        queryset = queryset.filter(Q(name__icontains=keyword))
    total = queryset.count()
    page, page_size = parse_page_params(request)
    start = (page - 1) * page_size
    items = [_run_payload(item) for item in queryset[start : start + page_size]]
    return ok({'items': items, 'total': total, 'page': page, 'page_size': page_size})


@api_view(['GET'])
def run_detail(request, pk):
    run = ApiTestRun.objects.filter(pk=pk, user=request.user, suite_id__isnull=False).first()
    if run is None:
        return fail('报告不存在', http_status=status.HTTP_404_NOT_FOUND)
    return ok(_run_payload(run, with_steps=True))
