import copy
import json


class RequestContext:
    def __init__(self, spec, log, response=None, test=None):
        self.spec = spec
        self.log = log
        self.response = response or {}
        self.test = test

    def _upsert(self, rows_key, key, value):
        rows = list(self.spec.get(rows_key) or [])
        found = False
        for item in rows:
            if isinstance(item, dict) and str(item.get('key') or '') == str(key):
                item['value'] = value
                item['enabled'] = True
                found = True
                break
        if not found:
            rows.append({'key': key, 'value': value, 'enabled': True, 'type': 'string'})
        self.spec[rows_key] = rows

    def set_header(self, key, value):
        self._upsert('headers', key, value)
        self.log(f'setUp set_header {key}')

    def set_query(self, key, value):
        self._upsert('query', key, value)
        self.log(f'setUp set_query {key}')

    def set_cookie(self, key, value):
        self._upsert('cookies', key, value)
        self.log(f'setUp set_cookie {key}')

    def set_body(self, value):
        if isinstance(value, (dict, list)):
            self.spec['body'] = json.dumps(value, ensure_ascii=False)
        else:
            self.spec['body'] = str(value)
        self.log('setUp set_body')

    def assert_in(self, fragment):
        text = (self.response or {}).get('response_text') or ''
        if self.test is not None:
            self.test.assertIn(str(fragment), text)
        elif str(fragment) not in text:
            raise AssertionError(f'后置断言失败：响应未包含 {fragment}')
        self.log(f'tearDown assert_in {fragment}')

    def assert_status(self, code):
        actual = str((self.response or {}).get('status_code') or '')
        if self.test is not None:
            self.test.assertEqual(actual, str(code))
        elif actual != str(code):
            raise AssertionError(f'后置断言失败：状态码 {actual} != {code}')
        self.log(f'tearDown assert_status {code}')


def run_script(script, spec, log, response=None, test=None, phase='setUp'):
    code = (script or '').strip()
    if not code:
        return spec
    working = copy.deepcopy(spec)
    api = RequestContext(working, log, response=response, test=test)
    env = {
        'api': api,
        'json': json,
        'True': True,
        'False': False,
        'None': None,
        'str': str,
        'int': int,
        'float': float,
        'len': len,
        'dict': dict,
        'list': list,
    }
    log(f'unittest {phase} 开始')
    exec(code, {'__builtins__': {}}, env)  # noqa: S102
    log(f'unittest {phase} 结束')
    return api.spec
