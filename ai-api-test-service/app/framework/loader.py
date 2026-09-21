import copy
import unittest

from app.framework.assertions import check_assertion_item, check_body_contains, check_status
from app.framework.http_client import send_request
from app.framework.retry import retry
from app.framework.scripts import run_script


def build_test_case(spec, timeout, log):
    retry_times = spec.get('retry_times')
    retry_delay = spec.get('retry_delay')
    if retry_times is None:
        retry_times = 3
    if retry_delay is None:
        retry_delay = 1

    class ApiHttpTest(unittest.TestCase):
        http_result = None
        assertion_logs = []
        runtime_spec = None

        def setUp(self):
            ApiHttpTest.runtime_spec = copy.deepcopy(spec)
            script = ApiHttpTest.runtime_spec.get('setup_script') or ''
            if script.strip():
                ApiHttpTest.runtime_spec = run_script(
                    script,
                    ApiHttpTest.runtime_spec,
                    log,
                    phase='setUp',
                )

        def tearDown(self):
            script = (spec.get('teardown_script') or '').strip()
            if not script:
                return
            run_script(
                script,
                ApiHttpTest.runtime_spec or spec,
                log,
                response=ApiHttpTest.http_result,
                test=self,
                phase='tearDown',
            )

        @retry(times=retry_times, delay=retry_delay, log=log)
        def test_api(self):
            current = ApiHttpTest.runtime_spec or spec
            log(f"请求 {current.get('method')} {current.get('url') or current.get('path')}")
            result = send_request(current, timeout)
            ApiHttpTest.http_result = result
            log(f"响应状态码 {result['status_code']} 耗时 {result['elapsed_ms']}ms")
            log(f"响应体 {result['response_text'][:2000]}")

            ok, message = check_status(result['status_code'], current.get('expected_status'))
            ApiHttpTest.assertion_logs.append(message)
            log(message)
            self.assertTrue(ok, message)

            ok, message = check_body_contains(result['response_text'], current.get('expected_body'))
            ApiHttpTest.assertion_logs.append(message)
            log(message)
            self.assertTrue(ok, message)

            for item in current.get('assertions') or []:
                ok, message = check_assertion_item(result['response_text'], item)
                ApiHttpTest.assertion_logs.append(message)
                log(message)
                self.assertTrue(ok, message)

    ApiHttpTest.__name__ = 'ApiHttpTest'
    return ApiHttpTest
