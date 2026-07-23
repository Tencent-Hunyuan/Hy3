# Example 06: Error Handling & Retry

健壮的错误处理与重试策略：覆盖超时、限流、网络错误等场景，实现指数退避重试。

---

## 环境准备

```bash
pip install openai
```

---

## 常见错误类型速查

| 异常类 | HTTP 状态码 | 场景 | 是否可重试 |
|:---|:---|:---|:---|
| `openai.AuthenticationError` | 401 | API Key 无效 | ❌ |
| `openai.RateLimitError` | 429 | 超出速率限制 | ✅ |
| `openai.APITimeoutError` | — | 请求超时 | ✅ |
| `openai.APIConnectionError` | — | 网络不可达 | ✅ |
| `openai.InternalServerError` | 500 | 服务端错误 | ✅ |
| `openai.BadRequestError` | 400 | 参数错误 | ❌ |
| `openai.PermissionDeniedError` | 403 | 权限不足 | ❌ |

---

## 基础版：简单 try/except

### 完整代码

```python
import os
from openai import OpenAI, (
    APIError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
)

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
    timeout=60.0,   # 单次请求超时（秒）
    max_retries=0,  # 关闭 SDK 内置重试，改用自定义策略
)

try:
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "你好"}],
        temperature=0.9,
        max_tokens=128,
    )
    print(response.choices[0].message.content)

except AuthenticationError as e:
    # 401 — API Key 无效，不重试
    print(f"[FATAL] 认证失败，请检查 API Key: {e}")

except BadRequestError as e:
    # 400 — 参数错误，不重试
    print(f"[FATAL] 请求参数错误: {e}")

except RateLimitError as e:
    # 429 — 限流，需要等待后重试
    print(f"[RETRY] 触发限流: {e}")

except APITimeoutError as e:
    # 超时，可重试
    print(f"[RETRY] 请求超时: {e}")

except APIConnectionError as e:
    # 网络问题，可重试
    print(f"[RETRY] 网络连接错误: {e}")

except InternalServerError as e:
    # 500 — 服务端错误，可重试
    print(f"[RETRY] 服务端内部错误: {e}")

except APIError as e:
    # 其他 API 错误
    print(f"[ERROR] 未知 API 错误: {e}")

except Exception as e:
    # 其他未预期的错误
    print(f"[ERROR] 未知错误: {type(e).__name__}: {e}")
```

---

## 进阶版：指数退避重试

### 完整代码

```python
import os
import time
import random
from openai import OpenAI, (
    APIStatusError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
    timeout=60.0,
    max_retries=0,  # 使用自定义重试
)

# ============================================================
# 重试配置
# ============================================================
MAX_RETRIES = 5              # 最大重试次数
BASE_DELAY = 1.0             # 基础等待秒数
MAX_DELAY = 60.0             # 最大等待秒数
JITTER = True                # 是否加入随机抖动
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def should_retry(error: Exception) -> bool:
    """判断是否应该重试"""
    if isinstance(error, APIConnectionError):
        return True
    if isinstance(error, APITimeoutError):
        return True
    if isinstance(error, RateLimitError):
        return True
    if isinstance(error, InternalServerError):
        return True
    if isinstance(error, APIStatusError):
        return error.status_code in RETRYABLE_STATUSES
    return False


def calc_delay(attempt: int) -> float:
    """计算指数退避等待时间，含随机抖动"""
    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
    if JITTER:
        delay *= 0.5 + random.random()  # [0.5 * delay, 1.5 * delay]
    return delay


def chat_with_retry(messages, **kwargs):
    """带重试的 chat completion 调用"""
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
                **kwargs,
            )
            return response  # 成功

        except Exception as e:
            last_error = e

            if not should_retry(e):
                print(f"  ❌ 不可重试的错误，立即放弃: {type(e).__name__}")
                raise

            if attempt >= MAX_RETRIES:
                print(f"  ❌ 已达最大重试次数 ({MAX_RETRIES})，放弃")
                raise

            delay = calc_delay(attempt)
            print(
                f"  ⚠️  [{type(e).__name__}] "
                f"第 {attempt + 1}/{MAX_RETRIES} 次重试，"
                f"等待 {delay:.1f}s..."
            )
            time.sleep(delay)

    raise last_error


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    messages = [{"role": "user", "content": "用三句话介绍人工智能"}]

    try:
        response = chat_with_retry(
            messages,
            temperature=0.9,
            max_tokens=256,
        )
        content = response.choices[0].message.content
        print(f"\n✅ 成功获取回复:\n{content}")
        print(f"   tokens: {response.usage.total_tokens}")

    except Exception as e:
        print(f"\n💥 最终失败: {type(e).__name__}: {e}")
```

---

## 生产级封装：RetryHandler 类

### 完整代码

```python
import os
import time
import random
import logging
from openai import OpenAI, (
    APIStatusError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
    AuthenticationError,
    BadRequestError,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class RetryHandler:
    """生产级重试处理器"""

    RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def should_retry(self, error: Exception) -> bool:
        if isinstance(error, (APIConnectionError, APITimeoutError,
                               RateLimitError, InternalServerError)):
            return True
        if isinstance(error, APIStatusError):
            return error.status_code in self.RETRYABLE_STATUSES
        return False

    def calc_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random()
        return delay

    def call(self, fn, *args, **kwargs):
        """包装任意函数，自动重试"""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except (AuthenticationError, BadRequestError) as e:
                logger.error(f"不可重试: {type(e).__name__}: {e}")
                raise
            except Exception as e:
                last_error = e
                if not self.should_retry(e):
                    logger.error(f"不可重试: {type(e).__name__}: {e}")
                    raise
                if attempt >= self.max_retries:
                    logger.error(f"已达最大重试 {self.max_retries} 次")
                    raise
                delay = self.calc_delay(attempt)
                logger.warning(
                    f"[{type(e).__name__}] 重试 {attempt + 1}/{self.max_retries}，"
                    f"等待 {delay:.1f}s"
                )
                time.sleep(delay)
        raise last_error


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    client = OpenAI(
        api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
        base_url="https://tokenhub.tencentmaas.com/v1",
        timeout=30.0,
        max_retries=0,
    )

    retry = RetryHandler(max_retries=3, base_delay=1.0)

    def do_chat(content: str):
        return client.chat.completions.create(
            model="hy3",
            messages=[{"role": "user", "content": content}],
            temperature=0.9,
            max_tokens=128,
        )

    # 执行调用
    response = retry.call(do_chat, "你好，介绍一下AI")
    print(response.choices[0].message.content)
```

### 示例输出（模拟限流场景）

```
2026-07-22 10:23:01 [WARNING] [RateLimitError] 重试 1/3，等待 1.2s
2026-07-22 10:23:03 [WARNING] [RateLimitError] 重试 2/3，等待 2.7s
2026-07-22 10:23:06 [INFO] 请求成功

✅ 成功获取回复:
人工智能（AI）是计算机科学的一个分支，旨在创建能模拟人类智能行为的系统...
   tokens: 89
```

---

## 关键要点

| 要点 | 说明 |
|:---|:---|
| **不可重试的错误** | 401（认证）、400（参数）、403（权限）— 重试不会改变结果 |
| **可重试的错误** | 429（限流）、500/502/503/504（服务端）、超时、网络断开 |
| **指数退避** | `delay = min(base_delay * 2^attempt, max_delay)` |
| **随机抖动** | 避免"惊群效应"—多个客户端同时重试导致二次限流 |
| **设置 max_retries=0** | 关闭 SDK 内置重试，用自定义逻辑精确控制行为 |
| **timeout 设置** | `OpenAI(timeout=60.0)` — 避免请求无限挂起 |
| **记录日志** | 记录每次重试的原因和等待时间，便于排查问题 |
