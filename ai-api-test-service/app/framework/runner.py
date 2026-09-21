import unittest
from io import StringIO
from pathlib import Path

from app.framework.loader import build_test_case
from app.framework.logger import get_logger
from app.framework.reporter import now_text, write_reports
from app.framework.result import ApiTextTestRunner


def run_api_test(spec, timeout, report_dir, run_id, log_dir=None, screenshot_dir=None):
    log, log_path, lines = get_logger(run_id, log_dir or report_dir)
    log(f'开始执行 {spec.get("case_name") or run_id}')
    test_cls = build_test_case(spec, timeout, log)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_cls)
    stream = StringIO()
    shot_dir = screenshot_dir or str(Path(report_dir) / 'screenshots')
    runner = ApiTextTestRunner(
        stream=stream,
        verbosity=2,
        screenshot_dir=shot_dir,
        run_id=run_id,
        test_cls=test_cls,
        log=log,
    )
    result = runner.run(suite)
    passed = result.wasSuccessful()
    failures = []
    for _test, traceback_text in list(result.failures) + list(result.errors):
        failures.append(traceback_text.splitlines()[-1] if traceback_text else '执行失败')
        log(traceback_text)
    log('执行结束：' + ('成功' if passed else '失败'))
    payload = {
        'run_id': run_id,
        'case_name': spec.get('case_name') or '',
        'passed': passed,
        'failures': failures,
        'http': test_cls.http_result or {},
        'assertion_logs': test_cls.assertion_logs,
        'logs': lines,
        'unittest_output': stream.getvalue(),
        'finished_at': now_text(),
        'log_path': log_path,
        'result_logs': getattr(result, 'records', []),
        'screenshots': getattr(result, 'screenshots', []),
    }
    html_path, json_path = write_reports(report_dir, run_id, payload)
    payload['report_html'] = html_path
    payload['report_json'] = json_path
    return payload


def run_api_suite(steps, timeout, report_dir, run_id, log_dir=None, screenshot_dir=None):
    import requests

    from app.framework.vars import apply_vars_to_spec, extract_variables

    log, log_path, lines = get_logger(run_id, log_dir or report_dir)
    log(f'开始套件执行，共 {len(steps or [])} 步')
    session = requests.Session()
    variables = {}
    step_results = []
    for index, step in enumerate(steps or [], 1):
        spec = apply_vars_to_spec(step.get('spec') or {}, variables)
        spec['_session'] = session
        log(f'第 {index} 步 {spec.get("case_name") or ""} 变量={variables}')
        payload = run_api_test(
            spec,
            timeout=timeout,
            report_dir=report_dir,
            run_id=f'{run_id}-{index}',
            log_dir=log_dir,
            screenshot_dir=screenshot_dir,
        )
        extracts = {}
        if payload.get('passed'):
            extracts = extract_variables((payload.get('http') or {}).get('response_text'), step.get('extractors'))
            variables.update({key: value for key, value in extracts.items()})
            log(f'第 {index} 步提取 {extracts}')
        item = {
            'step_index': index,
            'case_id': step.get('case_id'),
            'case_name': spec.get('case_name') or payload.get('case_name') or '',
            'passed': bool(payload.get('passed')),
            'extracts': extracts,
            'http': payload.get('http') or {},
            'assertion_logs': payload.get('assertion_logs') or [],
            'result_logs': payload.get('result_logs') or [],
            'screenshots': payload.get('screenshots') or [],
            'unittest_output': payload.get('unittest_output') or '',
            'failures': payload.get('failures') or [],
            'logs': payload.get('logs') or [],
        }
        step_results.append(item)
        if not item['passed']:
            log(f'第 {index} 步失败，中断后续步骤')
            break
    skipped = max(0, len(steps or []) - len(step_results))
    passed_count = sum(1 for item in step_results if item['passed'])
    failed_count = sum(1 for item in step_results if not item['passed'])
    all_passed = failed_count == 0 and skipped == 0 and passed_count == len(steps or [])
    return {
        'run_id': run_id,
        'passed': all_passed,
        'total': len(steps or []),
        'passed_count': passed_count,
        'failed_count': failed_count,
        'skipped_count': skipped,
        'variables': variables,
        'steps': step_results,
        'logs': lines,
        'finished_at': now_text(),
        'log_path': log_path,
    }
