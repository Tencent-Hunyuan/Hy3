# Error Handling & Retry — 错误处理与指数退避重试

演示 Hy3 API 调用中的错误分类、可重试性判断和指数退避重试策略。生产环境中网络波动、服务限流、临时故障是常态，健壮的重试机制是 API 客户端的必备能力。

## 运行

```bash
cd issue1
python examples/retry.py
```

可选配置：

```bash
export HY3_TIMEOUT="90"             # 请求超时秒数
export HY3_RETRY_MAX_ATTEMPTS="5"   # 最大重试次数（含首次）
```

## 错误分类策略

### 不可重试（直接失败）

这些错误重试也无法解决，应立即向上层报告：

| 错误类型 | 含义 | 处理方式 |
|:---|:---|:---|
| `BadRequestError` | 请求格式错误 | 修正请求参数 |
| `AuthenticationError` | API Key 无效 (401) | 检查 Key 配置 |
| `PermissionDeniedError` | 权限不足 (403) | 检查套餐权限 |
| `NotFoundError` | 模型不存在 (404) | 检查 model 名称 |

### 可重试（指数退避）

这些错误是临时的，重试可能成功：

| 错误类型 / 状态码 | 含义 | 典型原因 |
|:---|:---|:---|
| `APIConnectionError` | 网络连接失败 | DNS、TCP 层问题 |
| `APITimeoutError` | 请求超时 | 服务端负载高、网络延迟 |
| `RateLimitError` | 被限流 (429) | 短时间请求过多 |
| `408` | 请求超时 | 服务端处理超时 |
| `409` | 冲突 | 并发操作冲突 |
| `425` | 太早 | 服务未就绪 |
| `500, 502, 503, 504` | 服务端错误 | 临时故障 |

## 退避算法

```
sleep = min(8.0s, 0.5s × 2^(attempt-1)) + random(0, 0.25s)
```

各次重试的等待时间示例：

| attempt | 基础等待 | 最大抖动 | 实际范围 |
|:---|:---|:---|:---|
| 1 (首次失败) | 0.5s | 0.25s | 0.50s – 0.75s |
| 2 | 1.0s | 0.25s | 1.00s – 1.25s |
| 3 | 2.0s | 0.25s | 2.00s – 2.25s |
| 4 | 4.0s | 0.25s | 4.00s – 4.25s |
| 5 | 8.0s (cap) | 0.25s | 8.00s – 8.25s |

> **为什么需要 jitter？** 多个客户端同时重试时，如果退避时间完全相同，会在同一时刻同时冲击服务端（thundering herd）。随机抖动将请求分散到不同时间点。

## 重试核心实现

```python
def call_with_retry(fn, max_attempts=5):
    """带指数退避重试的 API 调用包装器。"""
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc) or attempt == max_attempts:
                raise  # 不可重试或已达上限，直接抛出

            wait = min(8.0, 0.5 * (2 ** (attempt - 1))) + random.uniform(0, 0.25)
            time.sleep(wait)
```

### 集成到 OpenAI Client

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key="your_key",
    timeout=30.0,          # 单次请求超时
    max_retries=2,         # SDK 内置重试（适用于网络层错误）
)

# SDK 内置重试 + 自定义业务重试 = 双重保护
response = call_with_retry(
    lambda: client.chat.completions.create(...),
    max_attempts=3
)
```

## 示例输出

以下为实际调用 TokenHub `hy3-preview` 的输出：

```
============================================================
【Hy3 API 错误处理与重试】
模型: hy3-preview
超时设置: 90.0s
最大重试: 5 次
============================================================

──────────────────────────────────
【错误分类参考表】
──────────────────────────────────
错误类型                          可重试       说明
────────────────────────────────────────────────────────────
BadRequestError                 ❌ 不可重试   请求格式错误，修改后重试
AuthenticationError             ❌ 不可重试   API Key 无效，检查配置
PermissionDeniedError           ❌ 不可重试   权限不足，检查套餐
NotFoundError                   ❌ 不可重试   模型名错误
APIConnectionError              ✅ 可重试     网络断开，可重试
APITimeoutError                 ✅ 可重试     请求超时，可重试
RateLimitError                  ✅ 可重试     被限流，可重试

──────────────────────────────────
【正常请求（带重试保护）】
──────────────────────────────────
  ✅ attempt=1/5 → 成功

──────────────────────────────────
【响应内容】
──────────────────────────────────
id: chatcmpl-xxxxxxxx
model: hy3-preview
finish_reason: stop
content:
安全重试 Hy3 API 请求的 5 条最佳实践：

1. **幂等性设计** — 使用幂等键确保重复请求不会产生副作用，尤其写操作必须保证多次执行结果一致。

2. **只重试临时错误** — 仅对网络超时、429（限流）和 5xx 服务端错误重试，对 4xx 客户端错误直接失败并记录日志。

3. **指数退避 + 随机抖动** — 采用指数增长等待时间并加入随机因子，避免多个客户端同时重试造成惊群效应。

4. **设置上限与超时** — 限制最大重试次数（建议 3-5 次）和总超时时间，防止无限等待耗尽资源。

5. **遵守 Retry-After 头** — 当服务端返回 429 或 503 时，优先使用响应中的 Retry-After 头指定的等待时间。

Token: prompt=36, completion=229, total=265
```

## 关键要点

1. **SDK 内置 + 自定义双层保护**：OpenAI SDK 的 `max_retries` 处理网络层，自定义 `call_with_retry` 处理业务层
2. **永不重试 4xx**：参数错误重试多少次也没用
3. **抖动不可或缺**：无抖动的指数退避在分布式系统中会制造同步冲击
4. **上限保护**：总重试次数和总耗时都要有上限，防止雪崩
5. **遵守 Retry-After**：服务端明确告诉你等多久，就按它说的做
