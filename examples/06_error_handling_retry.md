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

```python
"""
Hy3 错误处理与重试（Error Handling & Retry）示例
================================================

演示对 Hy3（OpenAI 兼容 API）调用时的常见错误处理与指数退避重试，覆盖三种场景：
  1. 超时（APITimeoutError）：用极短 timeout 强制触发，重试后仍失败则优雅处理。
  2. 限流（RateLimitError，HTTP 429）：展示如何捕获并按 429 进行退避处理。
  3. 网络错误（APIConnectionError）：用错误 base_url 强制触发，重试后优雅失败。

重试逻辑使用 tenacity 库，对 APITimeoutError / RateLimitError / APIConnectionError
做指数退避重试（最多 5 次）。每个场景都包在 try/except 中，脚本可安全独立运行
（即便没有 Hy3 服务，错误场景也会按预期触发）。

依赖：pip install tenacity openai

连接信息通过环境变量配置（带默认值）：
  HY3_BASE_URL  默认 http://127.0.0.1:8000/v1
  HY3_API_KEY   默认 EMPTY
"""

import os

from openai import (
    OpenAI,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    APIStatusError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

MODEL = "hy3"

# 通过环境变量初始化客户端（带默认值），方便切换部署地址
client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)


# ---------------------------------------------------------------------------
# 1. 定义带指数退避重试的调用封装
# ---------------------------------------------------------------------------
# 重试策略：
#   - 仅对 APITimeoutError / RateLimitError / APIConnectionError 重试
#     （这些通常是暂时性错误，重试有意义）
#   - wait_exponential：指数退避，等待时间 = min(max, multiplier * 2^(attempt-1))
#                       此处 multiplier=1, min=1, max=10
#                       即 1s, 2s, 4s, 8s, 10s(被 max 截断) ...
#   - stop_after_attempt(5)：最多重试 5 次
#   - APIStatusError（其他 HTTP 错误，如 400/500）不重试，直接抛出
@retry(
    retry=retry_if_exception_type(
        (APITimeoutError, RateLimitError, APIConnectionError)
    ),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
def chat_with_retry(messages, **kwargs):
    """带指数退避重试的 chat completion 调用。"""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        **kwargs,
    )


def header(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# ---------------------------------------------------------------------------
# 2. 场景一：超时（APITimeoutError）
# ---------------------------------------------------------------------------
def scenario_timeout():
    header("场景一：超时（APITimeoutError）")
    print("说明：设置极短的 timeout=0.001s，几乎必然超时。")
    print("预期：tenacity 触发指数退避重试，重试用尽后抛出 APITimeoutError，被 try/except 捕获。\n")

    # 用一个独立的 client 强制极短超时（不影响全局 client）
    short_timeout_client = OpenAI(
        base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
        api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
        timeout=0.001,
    )

    @retry(
        retry=retry_if_exception_type(
            (APITimeoutError, RateLimitError, APIConnectionError)
        ),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def call():
        return short_timeout_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.9,
            top_p=1.0,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        )

    try:
        call()
        print("[结果] 调用成功（未触发超时）。")
    except APITimeoutError as e:
        print(f"[捕获 APITimeoutError] 超时重试已用尽。")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  处理建议: 适当增大 timeout，或减小请求/上下文规模后重试。")
    except Exception as e:
        print(f"[捕获其他异常] {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# 3. 场景二：限流（RateLimitError，HTTP 429）
# ---------------------------------------------------------------------------
def scenario_rate_limit():
    header("场景二：限流（RateLimitError，HTTP 429）")
    print("说明：模拟服务端返回 429 时如何识别并退避处理。")
    print("预期：RateLimitError 被 retry 捕获并指数退避重试；这里手动构造一次以展示识别逻辑。\n")

    # 真实 429 由服务端返回时，OpenAI SDK 会自动抛出 RateLimitError。
    # 这里用 try/except 演示如何识别与处理该异常类型。
    try:
        # 尝试一次正常调用；若服务端真的限流，会抛 RateLimitError
        # （此处主要为展示捕获与处理逻辑）
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.9,
            top_p=1.0,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        )
        print("[结果] 调用成功，未触发限流。")
        print(f"  返回内容: {response.choices[0].message.content[:50]} ...")
    except RateLimitError as e:
        print(f"[捕获 RateLimitError] 服务端返回 429，触发限流。")
        print(f"  错误类型: {type(e).__name__}")
        # HTTP 429 是限流的典型状态码
        status = getattr(getattr(e, "response", None), "status_code", None)
        print(f"  HTTP 状态码: {status}")
        print(f"  处理建议: 降低并发/请求频率，指数退避后重试；必要时联系运维提升配额。")
    except APIStatusError as e:
        # 其他 HTTP 错误（非 429）走这里
        print(f"[捕获 APIStatusError] 非 429 的 HTTP 错误。")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  HTTP 状态码: {getattr(e, 'status_code', 'unknown')}")
        print(f"  处理建议: 根据状态码排查（4xx 检查请求，5xx 检查服务端）。")
    except Exception as e:
        print(f"[捕获其他异常] {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# 4. 场景三：网络错误（APIConnectionError）
# ---------------------------------------------------------------------------
def scenario_network_error():
    header("场景三：网络错误（APIConnectionError）")
    print("说明：使用一个无法连通的 base_url，强制触发连接错误。")
    print("预期：tenacity 指数退避重试用尽后抛出 APIConnectionError，被 try/except 捕获。\n")

    # 用一个必定无法连通的地址构造客户端
    bad_client = OpenAI(
        base_url="http://127.0.0.1:9/v1",  # 几乎不会有服务监听 9 端口
        api_key="EMPTY",
    )

    @retry(
        retry=retry_if_exception_type(
            (APITimeoutError, RateLimitError, APIConnectionError)
        ),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def call():
        return bad_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.9,
            top_p=1.0,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        )

    try:
        call()
        print("[结果] 调用成功（未触发网络错误）。")
    except APIConnectionError as e:
        print(f"[捕获 APIConnectionError] 网络连接失败，重试已用尽。")
        print(f"  错误类型: {type(e).__name__}")
        cause = getattr(e, "__cause__", None) or e
        print(f"  根因: {cause}")
        print(f"  处理建议: 检查 base_url 是否正确、Hy3 服务是否启动、网络/防火墙是否放通。")
    except Exception as e:
        print(f"[捕获其他异常] {type(e).__name__}: {e}")


def main():
    print("Hy3 错误处理与重试示例")
    print("本脚本可独立运行；即使没有 Hy3 服务，场景一/三也会按预期触发错误。")

    scenario_timeout()
    scenario_rate_limit()
    scenario_network_error()

    header("全部场景演示完成")
    print("要点回顾：")
    print("  - APITimeoutError   → 增大 timeout 或减小请求规模，可重试")
    print("  - RateLimitError(429)→ 降低并发/频率，指数退避后重试")
    print("  - APIConnectionError→ 检查 base_url / 服务状态 / 网络")
    print("  - APIStatusError    → 按 HTTP 状态码分别处理（4xx 查请求，5xx 查服务）")


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
