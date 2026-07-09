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
