"""通用耗时装饰器。"""
from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def timed(step_name: str | None = None) -> Callable[[F], F]:
    """统计函数耗时并打印。用法: @timed("step1")"""

    def decorator(func: F) -> F:
        name = step_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            print(f"[TIMING] >>> 开始: {name}")
            try:
                return func(*args, **kwargs)
            finally:
                cost = time.perf_counter() - start
                print(f"[TIMING] <<< 结束: {name} | 耗时 {cost:.3f}s")

        return wrapper  # type: ignore[return-value]

    return decorator


if __name__ == "__main__":
    @timed("demo_sleep")
    def _demo() -> None:
        time.sleep(0.05)

    _demo()
