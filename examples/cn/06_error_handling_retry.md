# 06 错误处理与重试（Error Handling & Retry）

## 简介

本示例演示调用 Hy3（OpenAI 兼容 API）时对常见错误的处理与**指数退避重试**，覆盖三类典型场景：

1. **超时（`APITimeoutError`）**：用极短 `timeout` 强制触发，重试用尽后优雅失败。
2. **限流（`RateLimitError`，HTTP 429）**：展示如何识别 429 并按限流策略退避处理。
3. **网络错误（`APIConnectionError`）**：用错误 `base_url` 强制触发连接失败，重试后优雅处理。

重试逻辑使用 `tenacity` 库，对暂时性错误（超时/限流/网络错误）做指数退避重试，最多 5 次。每个场景都包裹在 `try/except` 中，**脚本可独立安全运行**——即使没有 Hy3 服务，场景一与场景三也会按预期触发错误。

---

## 前置条件

1. 安装依赖：
   ```bash
   pip install tenacity openai
   ```

2. 连接信息通过环境变量配置（默认值适用于本地部署）：
   ```bash
   set HY3_BASE_URL=http://127.0.0.1:8000/v1
   set HY3_API_KEY=EMPTY
   ```

3. 若要演示"正常调用"路径（场景二的非限流分支），需先启动 Hy3 服务（vLLM / SGLang）。场景一、三无需服务即可触发错误。

---

## 完整请求

> 完整可运行脚本位于 `../en/06_error_handling_retry.py`。

```python
"""Hy3 Example 06: Error handling & retry (timeout / 429 / network / 5xx).

Demonstrates:
  1. Timeout (APITimeoutError) with forced short timeout + bounded retry
  2. Rate limit (429 / RateLimitError) including Retry-After handling
  3. Network error (APIConnectionError) against an unreachable base_url
  4. Shared call_with_retry helper (exponential backoff, total wait cap)

Scenarios 1 and 3 work even without a live Hy3 service.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from openai import (  # noqa: E402
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from common import (  # noqa: E402
    call_with_retry,
    chat_completion,
    get_config,
    make_client,
    parse_retry_after,
)


def header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def scenario_timeout():
    header("Scenario 1: Timeout (APITimeoutError)")
    print("Note: timeout=0.001s almost always times out.")
    print("Expected: call_with_retry backs off, then raises APITimeoutError.\n")

    short_client = make_client(timeout=0.001)

    def call():
        return chat_completion(
            short_client,
            [{"role": "user", "content": "你好"}],
            reasoning="no_think",
        )

    try:
        # Keep demo snappy: few attempts, small delays
        call_with_retry(call, max_attempts=3, base_delay=0.2, max_delay=0.5, max_total_wait=2.0)
        print("[Result] Call succeeded (timeout not triggered).")
    except APITimeoutError as e:
        print("[Caught APITimeoutError] Timeout retries exhausted.")
        print(f"  Error type: {type(e).__name__}")
        print("  Suggestion: increase timeout, reduce context/max_tokens, or retry later.")
    except Exception as e:
        print(f"[Caught other exception] {type(e).__name__}: {e}")


def scenario_rate_limit():
    header("Scenario 2: Rate limit (RateLimitError, HTTP 429)")
    print("Note: shows identification + Retry-After aware backoff.")
    print("If the live server is not rate-limiting, the call succeeds normally.\n")

    client = make_client()

    def call():
        return chat_completion(
            client,
            [{"role": "user", "content": "你好"}],
            reasoning="no_think",
        )

    try:
        response = call_with_retry(call, max_attempts=3, base_delay=0.5, max_delay=2.0)
        print("[Result] Call succeeded; rate limit not triggered.")
        content = response.choices[0].message.content or ""
        print(f"  Returned content: {content[:50]} ...")
    except RateLimitError as e:
        retry_after = parse_retry_after(e)
        print("[Caught RateLimitError] Server returned 429.")
        print(f"  Error type: {type(e).__name__}")
        status = getattr(getattr(e, "response", None), "status_code", None)
        print(f"  HTTP status code: {status}")
        print(f"  Retry-After: {retry_after}")
        print("  Suggestion: lower concurrency; respect Retry-After; request quota if needed.")
    except APIStatusError as e:
        print("[Caught APIStatusError] Non-429 HTTP error.")
        print(f"  status_code: {getattr(e, 'status_code', 'unknown')}")
    except Exception as e:
        print(f"[Caught other exception] {type(e).__name__}: {e}")


def scenario_network_error():
    header("Scenario 3: Network error (APIConnectionError)")
    print("Note: uses unreachable base_url http://127.0.0.1:9/v1")
    print("Expected: retries then APIConnectionError.\n")

    bad_client = make_client(base_url="http://127.0.0.1:9/v1", api_key="EMPTY", timeout=2.0)

    def call():
        return chat_completion(
            bad_client,
            [{"role": "user", "content": "你好"}],
            reasoning="no_think",
        )

    try:
        call_with_retry(call, max_attempts=3, base_delay=0.2, max_delay=0.5, max_total_wait=2.0)
        print("[Result] Call succeeded (network error not triggered).")
    except APIConnectionError as e:
        print("[Caught APIConnectionError] Network connection failed; retries exhausted.")
        print(f"  Error type: {type(e).__name__}")
        cause = getattr(e, "__cause__", None) or e
        print(f"  Root cause: {cause}")
        print("  Suggestion: check base_url, service health, firewall/proxy.")
    except Exception as e:
        print(f"[Caught other exception] {type(e).__name__}: {e}")


def main():
    cfg = get_config()
    print("Hy3 Error Handling & Retry Example")
    print(f"Default target: {cfg['base_url']}  model={cfg['model']}")
    print("Scenarios 1 and 3 run without a live Hy3 service.")

    scenario_timeout()
    scenario_rate_limit()
    scenario_network_error()

    header("All scenarios demonstrated")
    print("Key takeaways:")
    print("  - APITimeoutError    -> increase timeout / reduce request size; retryable")
    print("  - RateLimitError(429)-> lower QPS, honor Retry-After, exponential backoff")
    print("  - APIConnectionError -> check base_url / service / network")
    print("  - 5xx APIStatusError -> retry with backoff; 4xx (except 429) usually not")
    print("  - Always cap max_attempts and max_total_wait so clients never hang forever")


if __name__ == "__main__":
    main()
```

---

## 完整 response 解析

### 1. 错误类型说明

OpenAI Python SDK 对 Hy3（OpenAI 兼容 API）调用时可能抛出以下异常：

| 异常类型                | 触发场景                                   | 是否值得重试 |
|:------------------------|:-------------------------------------------|:------------|
| `APITimeoutError`       | 请求超时（超过设定的 `timeout`）            | 是          |
| `RateLimitError`        | 服务端返回 HTTP **429**（请求过频/超配额）  | 是          |
| `APIConnectionError`    | 网络层连接失败（DNS/拒绝连接/不可达等）      | 是          |
| `APIStatusError`        | 其他 HTTP 错误（400 请求错误、500 服务端错误等） | 视情况，一般不重试 |

> `APITimeoutError`、`RateLimitError`、`APIConnectionError` 属于**暂时性错误**，重试通常有意义；`APIStatusError`（如 400 参数错误）重试无意义，应直接排查请求。

### 2. tenacity 重试策略

本示例用 `tenacity` 的装饰器实现重试，关键配置：

```python
@retry(
    retry=retry_if_exception_type(
        (APITimeoutError, RateLimitError, APIConnectionError)
    ),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
```

- **`retry_if_exception_type`**：仅当抛出指定类型的异常时才重试。这里只对三种暂时性错误重试，`APIStatusError` 不会触发重试。
- **`wait_exponential`**：指数退避，避免在服务端压力未恢复时密集重试。
- **`stop_after_attempt(5)`**：最多尝试 5 次，防止无限重试。
- **`reraise=True`**：重试用尽后重新抛出原始异常，便于上层 `try/except` 按类型分别处理。

### 3. 指数退避公式

`wait_exponential(multiplier=1, min=1, max=10)` 的等待时间计算：

```
wait = min(max, multiplier * 2^(attempt - 1))
```

各次重试的等待时间（`multiplier=1, min=1, max=10`）：

| 第几次尝试 | 等待时间 |
|:----------:|:--------:|
| 1（首次）  | 0（立即） |
| 2          | 1s        |
| 3          | 2s        |
| 4          | 4s        |
| 5          | 8s        |
| 6+         | 10s（被 max 截断） |

本示例最多 5 次尝试，实际等待序列约为：立即 → 1s → 2s → 4s → 8s。

### 4. 各错误的识别与处理建议

- **超时（`APITimeoutError`）**
  - 识别：捕获 `APITimeoutError`。
  - 处理：适当增大 `timeout`；若因上下文过长导致生成慢，可减小请求/上下文规模；重试可恢复偶发性超时。

- **限流（`RateLimitError`，HTTP 429）**
  - 识别：捕获 `RateLimitError`，其底层 HTTP 状态码为 429。
  - 处理：降低并发数与请求频率；指数退避后重试；必要时联系运维提升配额（QPS/TPM）。

- **网络错误（`APIConnectionError`）**
  - 识别：捕获 `APIConnectionError`，根因可通过 `e.__cause__` 查看（如连接拒绝）。
  - 处理：检查 `base_url` 是否正确、Hy3 服务是否已启动、网络/防火墙是否放通对应端口。

- **其他 HTTP 错误（`APIStatusError`）**
  - 识别：捕获 `APIStatusError`，通过 `e.status_code` 获取状态码。
  - 处理：4xx 检查请求参数（如模型名、消息格式），5xx 检查服务端日志与状态。

---

## 示例输出

> 以下为示例性输出（非真实运行结果），用于展示各场景的打印格式与错误信息。实际错误根因文本会因环境而异。

```text
Hy3 错误处理与重试示例
本脚本可独立运行；即使没有 Hy3 服务，场景一/三也会按预期触发错误。

======================================================================
场景一：超时（APITimeoutError）
======================================================================
说明：设置极短的 timeout=0.001s，几乎必然超时。
预期：tenacity 触发指数退避重试，重试用尽后抛出 APITimeoutError，被 try/except 捕获。

[捕获 APITimeoutError] 超时重试已用尽。
  错误类型: APITimeoutError
  处理建议: 适当增大 timeout，或减小请求/上下文规模后重试。

======================================================================
场景二：限流（RateLimitError，HTTP 429）
======================================================================
说明：模拟服务端返回 429 时如何识别并退避处理。
预期：RateLimitError 被 retry 捕获并指数退避重试；这里手动构造一次以展示识别逻辑。

[捕获 RateLimitError] 服务端返回 429，触发限流。
  错误类型: RateLimitError
  HTTP 状态码: 429
  处理建议: 降低并发/请求频率，指数退避后重试；必要时联系运维提升配额。

======================================================================
场景三：网络错误（APIConnectionError）
======================================================================
说明：使用一个无法连通的 base_url，强制触发连接错误。
预期：tenacity 指数退避重试用尽后抛出 APIConnectionError，被 try/except 捕获。

[捕获 APIConnectionError] 网络连接失败，重试已用尽。
  错误类型: APIConnectionError
  根因: Connection error.
  处理建议: 检查 base_url 是否正确、Hy3 服务是否启动、网络/防火墙是否放通。

======================================================================
全部场景演示完成
======================================================================
要点回顾：
  - APITimeoutError   → 增大 timeout 或减小请求规模，可重试
  - RateLimitError(429)→ 降低并发/频率，指数退避后重试
  - APIConnectionError→ 检查 base_url / 服务状态 / 网络
  - APIStatusError    → 按 HTTP 状态码分别处理（4xx 查请求，5xx 查服务）
```
