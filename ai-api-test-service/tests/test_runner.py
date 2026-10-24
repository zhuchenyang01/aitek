import unittest
from unittest.mock import patch

from app.framework.retry import retry
from app.framework.runner import run_api_test


class FakeResponse:
    def __init__(self, status_code=200, text='{"ok":true}'):
        self.url = 'https://example.com/login'
        self.status_code = status_code
        self.headers = {'Content-Type': 'application/json'}
        self.text = text
        self.elapsed = type('E', (), {'total_seconds': lambda self: 0.01})()


class RetryDecoratorTests(unittest.TestCase):
    def test_retries_then_passes(self):
        calls = {'n': 0}

        class Demo(unittest.TestCase):
            def setUp(self):
                calls.setdefault('setup', 0)
                calls['setup'] += 1

            def tearDown(self):
                calls.setdefault('teardown', 0)
                calls['teardown'] += 1

            @retry(times=3, delay=0)
            def test_flaky(self):
                calls['n'] += 1
                if calls['n'] < 2:
                    self.fail('transient')

        result = unittest.TextTestRunner(verbosity=0).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Demo)
        )
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(calls['n'], 2)
        self.assertGreaterEqual(calls['setup'], 2)


class RunnerTests(unittest.TestCase):
    @patch('app.framework.http_client.requests.request', return_value=FakeResponse())
    def test_pass(self, _mock):
        spec = {
            'case_name': '登录',
            'method': 'POST',
            'url': 'https://example.com/login',
            'body': '{"username":"a"}',
            'expected_status': '200',
            'expected_body': 'ok',
            'assertions': [],
            'retry_times': 1,
            'retry_delay': 0,
        }
        result = run_api_test(spec, timeout=5, report_dir='/tmp/api-test-reports', run_id='t1')
        self.assertTrue(result['passed'])
        self.assertEqual(result['http']['status_code'], 200)
        self.assertTrue(result['screenshots'])
        events = [row['event'] for row in result['result_logs']]
        self.assertIn('addSuccess', events)


class AssertionTests(unittest.TestCase):
    def test_eq_and_contains(self):
        from app.framework.assertions import check_assertion_item

        http = {
            'status_code': 200,
            'response_text': '{"code":0,"msg":"登录成功","data":{"token":"abc"}}',
            'response_headers': {'Content-Type': 'application/json'},
            'elapsed_ms': 12,
        }
        ok, _ = check_assertion_item(http, {'source': 'status', 'operator': 'eq', 'expected': '200'})
        self.assertTrue(ok)
        ok, _ = check_assertion_item(http, {'source': 'json', 'path': 'code', 'operator': 'eq', 'expected': '0'})
        self.assertTrue(ok)
        ok, _ = check_assertion_item(http, {'source': 'json', 'path': 'msg', 'operator': 'contains', 'expected': '成功'})
        self.assertTrue(ok)
        ok, _ = check_assertion_item(http, {'source': 'json', 'path': 'data.token', 'operator': 'exists'})
        self.assertTrue(ok)
        ok, _ = check_assertion_item(http, {'source': 'body', 'operator': 'contains', 'expected': 'token'})
        self.assertTrue(ok)
        ok, _ = check_assertion_item(http, {'source': 'json', 'path': 'code', 'operator': 'eq', 'expected': '1'})
        self.assertFalse(ok)
        ok, _ = check_assertion_item(http, {'name': 'status', 'expected': '200'})
        self.assertTrue(ok)
        ok, _ = check_assertion_item(http, {'name': 'code', 'expected': '0'})
        self.assertTrue(ok)


class VarsTests(unittest.TestCase):
    def test_apply_and_extract(self):
        from app.framework.vars import apply_vars, extract_variables

        self.assertEqual(apply_vars('Bearer ${token}', {'token': 'abc'}), 'Bearer abc')
        extracted = extract_variables('{"data":{"token":"xyz"}}', [{'name': 'token', 'path': 'data.token'}])
        self.assertEqual(extracted['token'], 'xyz')


class SuiteRunnerTests(unittest.TestCase):
    @patch('requests.Session.request', return_value=FakeResponse(text='{"data":{"token":"t1"}}'))
    def test_suite_extracts_variables(self, _mock):
        from app.framework.runner import run_api_suite

        steps = [
            {
                'case_id': 1,
                'extractors': [{'name': 'token', 'path': 'data.token'}],
                'spec': {
                    'case_name': '登录',
                    'method': 'POST',
                    'url': 'https://example.com/login',
                    'expected_status': '200',
                    'retry_times': 1,
                    'retry_delay': 0,
                },
            },
            {
                'case_id': 2,
                'extractors': [],
                'spec': {
                    'case_name': '查询',
                    'method': 'GET',
                    'url': 'https://example.com/me?token=${token}',
                    'expected_status': '200',
                    'retry_times': 1,
                    'retry_delay': 0,
                },
            },
        ]
        result = run_api_suite(steps, timeout=5, report_dir='/tmp/api-test-reports', run_id='s1')
        self.assertTrue(result['passed'])
        self.assertEqual(result['variables']['token'], 't1')
        self.assertEqual(result['passed_count'], 2)
