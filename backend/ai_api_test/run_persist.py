from django.utils import timezone

from .models import ApiTestRun, ApiTestRunLog, ApiTestRunStepResult


def persist_run_logs(user, case, data):
    if case is None:
        return
    run_id = str((data or {}).get('run_id') or '')
    rows = (data or {}).get('result_logs') or []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ApiTestRunLog.objects.create(
            user=user,
            case=case,
            run_id=run_id,
            event=str(row.get('event') or '')[:64],
            outcome=str(row.get('outcome') or 'running')[:16],
            test_name=str(row.get('test_name') or '')[:255],
            message=row.get('message') or '',
            traceback=row.get('traceback') or '',
            screenshot_path=str(row.get('screenshot_path') or '')[:1024],
            extra={'http': row.get('http') or {}},
        )


def persist_single_run(user, case, data):
    persist_run_logs(user, case, data or {})
    return None


def persist_suite_run(user, suite, data):
    passed = bool(data and data.get('passed'))
    total = int((data or {}).get('total') or 0)
    passed_count = int((data or {}).get('passed_count') or 0)
    failed_count = int((data or {}).get('failed_count') or 0)
    skipped_count = int((data or {}).get('skipped_count') or 0)
    run = ApiTestRun.objects.create(
        user=user,
        project=suite.project,
        suite=suite,
        name=suite.name,
        status='success' if passed else 'fail',
        total=total,
        passed=passed_count,
        failed=failed_count,
        skipped=skipped_count,
        summary=f'通过 {passed_count}/{total}' + (f'，跳过 {skipped_count}' if skipped_count else ''),
        service_run_id=str((data or {}).get('run_id') or ''),
        finished_at=timezone.now(),
    )
    for item in (data or {}).get('steps') or []:
        case_id = item.get('case_id')
        ApiTestRunStepResult.objects.create(
            run=run,
            case_id=case_id,
            step_index=item.get('step_index') or 1,
            case_name=item.get('case_name') or '',
            passed=bool(item.get('passed')),
            http=item.get('http') or {},
            extracts=item.get('extracts') or {},
            assertion_logs=item.get('assertion_logs') or [],
            result_logs=item.get('result_logs') or [],
            screenshots=item.get('screenshots') or [],
            unittest_output=item.get('unittest_output') or '',
            failures=item.get('failures') or [],
        )
        if case_id:
            from .models import ApiTestCase
            case = ApiTestCase.objects.filter(pk=case_id).first()
            if case:
                persist_run_logs(user, case, {**item, 'run_id': data.get('run_id')})
    data = data or {}
    data['report_id'] = run.id
    return run
