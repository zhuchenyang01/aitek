import unittest

from app.framework.screenshot import capture_screenshot


class ApiTestResult(unittest.TextTestResult):
    """记录成功 / 失败 / 跳过，并在各结局自动截图。"""

    def __init__(self, stream, descriptions, verbosity, screenshot_dir='', run_id='', test_cls=None, log=None):
        super().__init__(stream, descriptions, verbosity)
        self.screenshot_dir = screenshot_dir
        self.run_id = run_id
        self.test_cls = test_cls
        self.log = log or (lambda _msg: None)
        self.records = []
        self.screenshots = []

    def _http(self):
        if self.test_cls is None:
            return {}
        return getattr(self.test_cls, 'http_result', None) or {}

    def _case_name(self, test):
        return getattr(test, '_testMethodName', '') or str(test)

    def _append(self, event, outcome, test, message='', traceback_text='', screenshot=''):
        record = {
            'event': event,
            'outcome': outcome,
            'test_name': str(test),
            'message': message or '',
            'traceback': traceback_text or '',
            'screenshot_path': screenshot or '',
            'http': self._http(),
        }
        self.records.append(record)
        self.log(f'TestResult.{event} {outcome} {record["test_name"]}')
        return record

    def _shot(self, outcome, test, message=''):
        path = capture_screenshot(
            self.screenshot_dir,
            self.run_id,
            outcome,
            self._case_name(test),
            http=self._http(),
            message=message,
        )
        self.screenshots.append(path)
        self.log(f'截图 {outcome}: {path}')
        return path

    def startTest(self, test):
        super().startTest(test)
        self._append('startTest', 'running', test)

    def stopTest(self, test):
        super().stopTest(test)
        self._append('stopTest', 'stopped', test)

    def addSuccess(self, test):
        super().addSuccess(test)
        shot = self._shot('success', test, 'passed')
        self._append('addSuccess', 'success', test, message='passed', screenshot=shot)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        detail = self._exc_info_to_string(err, test)
        shot = self._shot('failure', test, detail.splitlines()[-1] if detail else 'failed')
        self._append('addFailure', 'failure', test, message='failed', traceback_text=detail, screenshot=shot)

    def addError(self, test, err):
        super().addError(test, err)
        detail = self._exc_info_to_string(err, test)
        shot = self._shot('error', test, detail.splitlines()[-1] if detail else 'error')
        self._append('addError', 'error', test, message='error', traceback_text=detail, screenshot=shot)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        shot = self._shot('skip', test, reason or 'skipped')
        self._append('addSkip', 'skip', test, message=reason or 'skipped', screenshot=shot)


class ApiTextTestRunner(unittest.TextTestRunner):
    resultclass = ApiTestResult

    def __init__(self, *args, screenshot_dir='', run_id='', test_cls=None, log=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.screenshot_dir = screenshot_dir
        self.run_id = run_id
        self.test_cls = test_cls
        self._log = log

    def _makeResult(self):
        return ApiTestResult(
            self.stream,
            self.descriptions,
            self.verbosity,
            screenshot_dir=self.screenshot_dir,
            run_id=self.run_id,
            test_cls=self.test_cls,
            log=self._log,
        )
