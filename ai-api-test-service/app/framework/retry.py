import time
from functools import wraps

try:
    from requests.exceptions import RequestException
except ImportError:  # pragma: no cover
    RequestException = OSError

RETRY_EXCEPTIONS = (AssertionError, RequestException)


def retry(times=3, delay=1.0, exceptions=RETRY_EXCEPTIONS, log=None):
    """用例级重试：装饰 unittest 的 test_* 方法。

    失败后先 tearDown 再 setUp，保证前置/后置与请求同次数执行。
    不装饰 setUp/tearDown 本身，也不放在 HTTP 客户端里（避免非幂等请求被静默重放）。
    """
    attempts = max(1, int(times or 1))
    wait = max(0.0, float(delay or 0))

    def deco(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            last = None
            for index in range(1, attempts + 1):
                try:
                    if index > 1:
                        try:
                            self.tearDown()
                        except Exception as exc:
                            if log:
                                log(f'重试前 tearDown 异常：{exc}')
                        self.setUp()
                    return fn(self, *args, **kwargs)
                except exceptions as exc:
                    last = exc
                    if log:
                        log(f'第 {index}/{attempts} 次执行失败：{exc}')
                    if index >= attempts:
                        raise
                    if wait:
                        time.sleep(wait)
            raise last

        return wrapper

    return deco
