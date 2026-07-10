# 示例 6：错误处理与重试

## 概述

生产环境中 API 调用可能遇到各种错误，本示例演示如何优雅地处理它们：

| 错误类型 | 触发条件 | 处理策略 |
|---------|---------|---------|
| **超时 (APITimeoutError)** | 请求超过设定的 timeout | 增加超时 + 重试 |
| **限流 (RateLimitError)** | HTTP 429，请求过频 | 指数退避 + jitter + 重试 |
| **连接错误 (APIConnectionError)** | 网络不通、服务不可达 | 检查网络 + 重试 |
| **其他 API 错误** | 400/401/500 等 | 根据状态码分别处理 |

---

## 核心：指数退避 + Jitter

```python
import random
import time

def exponential_backoff(attempt, base_delay=1.0, max_delay=60.0):
    """计算指数退避延迟（带随机 jitter）"""
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)  # 10% jitter
    return delay + jitter

# 重试次数与等待时间示例
for i in range(5):
    delay = exponential_backoff(i, base_delay=1.0)
    print(f"第 {i+1} 次重试: 等待 {delay:.1f}s")
```

输出：

```text
第 1 次重试: 等待 1.05s
第 2 次重试: 等待 2.08s
第 3 次重试: 等待 4.12s
第 4 次重试: 等待 8.31s
第 5 次重试: 等待 16.22s
```

---

## 通用重试装饰器

```python
from openai import APITimeoutError, RateLimitError, APIConnectionError

def retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0):
    """通用指数退避重试装饰器"""
    retryable = (APITimeoutError, RateLimitError, APIConnectionError)

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = random.uniform(0, delay * 0.1)
                        print(f"⚠️ 第 {attempt+1} 次失败，等待 {delay+jitter:.1f}s 重试...")
                        time.sleep(delay + jitter)
                    else:
                        print(f"❌ 已达最大重试次数")
                        raise
            raise last_exception
        return wrapper
    return decorator
```

---

## 生产环境最佳实践

### 1. 初始化客户端时设置重试

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key="sk-你的APIKey",
    timeout=60.0,
    max_retries=3,  # ✅ 内置重试机制
)
```

### 2. 异常处理优先级

```python
try:
    response = client.chat.completions.create(...)
except APITimeoutError:
    # 超时：增加超时时间或重试
except RateLimitError:
    # 限流：等待后重试
except APIConnectionError:
    # 连接错误：检查网络/URL
except APIError as e:
    # 其他 API 错误
    if e.status_code == 400:
        # 请求格式错误
    elif e.status_code == 401:
        # API Key 无效
    elif e.status_code == 503:
        # 服务不可用
```

### 3. 快速检查 API Key 有效性

```bash
curl -s https://tokenhub.tencentmaas.com/v1/models \
  -H "Authorization: Bearer sk-你的APIKey" \
  -o /dev/null -w "HTTP %{http_code}\n"
```

返回 `200` 表示 API Key 有效。

---

## 运行结果示例

```text
Hy3 API 错误处理与重试示例

API Endpoint: https://tokenhub.tencentmaas.com/v1

============================================================
【示例 1: 超时重试】
============================================================
  ⚠️ 第 1 次失败: APITimeoutError
  ⏳ 等待 1.05s 后重试 (2 次剩余)...
  ⚠️ 第 2 次失败: APITimeoutError
  ⏳ 等待 2.11s 后重试 (1 次剩余)...
  ❌ 已达最大重试次数 (2)，放弃
  ❌ 最终: 请求超时，建议增加 timeout 值

  ✅ 正确做法：使用合理超时
  回答: 1+1=2

============================================================
【示例 2: 限流重试】
============================================================
  提示: 生产环境建议:
  - 启用 client 的 max_retries 参数
  - 或使用 retry_with_backoff 装饰器
  - 捕获 RateLimitError 后使用指数退避
  ✅ 成功获取响应: 今天天气...

============================================================
【示例 3: 网络错误处理】
============================================================
  ⚠️ 第 1 次失败: APIConnectionError
  ⏳ 等待 1.07s 后重试 (2 次剩余)...
  ⚠️ 第 2 次失败: APIConnectionError
  ⏳ 等待 2.09s 后重试 (1 次剩余)...
  ❌ 最终: 连接失败: APIConnectionError
  ✅ 解决方法: 检查 URL、网络连接、API Key 是否正确

============================================================
【示例 4: 生产级健壮调用】
============================================================
  ✅ 回答: API 错误重试是指在调用接口失败时，按照一定策略
（如指数退避）重新发起请求，以提高调用成功率。
  📊 用量: prompt=26, completion=38, total=64
```

---

## 关键要点

1. **总是设置超时**：不要依赖默认值，根据任务复杂度设置 30s~120s
2. **指数退避 + jitter**：避免同时重试导致"惊群效应"
3. **区分可重试和不可重试错误**：超时/限流/连接错误可重试，400/401 不可重试
4. **设置最大重试次数**：防止无限重试耗尽资源，建议 3~5 次
5. **监控和日志**：记录每次失败和重试，便于排查问题

---

## 参考

- [Quickstart - 常见报错排查](../Quickstart.md#常见报错排查)
- [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/apikey)
- [OpenAI 错误处理指南](https://platform.openai.com/docs/guides/error-handling)
