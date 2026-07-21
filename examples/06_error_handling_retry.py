"""示例 06：错误处理与重试（超时 / 限流 / 网络错误）

错误是否可重试:
- 可重试：429(限流) / 502 / 503 / 504 / 连接失败 / 超时
- 不可重试：400(请求格式) / 401(认证) / 403(权限) / 402(余额)

运行:
    python 06_error_handling_retry.py
"""

import os
import random
import time

from openai import OpenAI
from openai import APITimeoutError, APIConnectionError
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=int(os.environ.get("HY3_TIMEOUT_SECONDS", "60")),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")
REASONING = {"chat_template_kwargs": {"reasoning_effort": "no_think"}}


# ── 重试参数───
MAX_ATTEMPTS = 4        # 最多尝试次数
BASE_DELAY = 0.5        # 初始退避秒数
MAX_DELAY = 8.0         # 单次退避上限
MAX_TOTAL_WAIT = 20.0   # 总等待预算（超此值直接放弃）


def is_retryable(err: Exception) -> bool:
    """判断错误是否可重试。"""
    status = getattr(err, "status_code", None)
    if status is not None:
        return status in (429, 502, 503, 504)
    return isinstance(err, (APITimeoutError, APIConnectionError, ConnectionError, TimeoutError))


def parse_retry_after(err: Exception) -> float | None:
    """从响应头读取 Retry-After（优先于退避公式）。"""
    resp = getattr(err, "response", None)
    if resp is None:
        return None
    raw = (resp.headers or {}).get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def backoff(attempt: int) -> float:
    """指数退避 + equal jitter: min(MAX, BASE*2^(n-1)) * (0.5~1.0)"""
    exp = min(MAX_DELAY, BASE_DELAY * (2 ** (attempt - 1)))
    return exp * (0.5 + 0.5 * random.random())


def call_with_retry(fn):
    """带重试的执行器。fn 是无参可调用对象（如 lambda: client.chat...）。"""
    total_wait = 0.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except Exception as err:
            if not is_retryable(err) or attempt >= MAX_ATTEMPTS:
                raise
            ra = parse_retry_after(err)
            delay = ra if ra is not None else backoff(attempt)
            if total_wait + delay > MAX_TOTAL_WAIT:
                raise RuntimeError("重试等待预算已耗尽") from err
            print(f"  第 {attempt} 次重试, 等待 {delay:.1f}s ("
                  f"HTTP {getattr(err, 'status_code', None) or err.__class__.__name__})")
            time.sleep(delay)
            total_wait += delay
    raise AssertionError("不可达")


def main() -> None:
    print("=== 带重试的请求 ===")
    try:
        response = call_with_retry(
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": "说「你好」两个字。"}],
                max_tokens=32,
                extra_body=REASONING,
            )
        )
        print("回答:", response.choices[0].message.content)
    except Exception as err:
        status = getattr(err, "status_code", None)
        status_str = f" (HTTP {status})" if status else ""
        print(f"请求失败: {err.__class__.__name__}{status_str}")


if __name__ == "__main__":
    main()
