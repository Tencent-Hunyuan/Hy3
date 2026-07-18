# 06 · Error Handling & Retry(超时 / 限流 / 网络错误)

生产环境必须处理三类错误:**业务错误(4xx,不重试)**、**限流(429,退避重试)**、**网络/超时(退避重试)**。可运行脚本:`06_error_handling_retry.py`。

---

## 1. 真实错误响应(非法 model,HTTP 400)

```bash
curl -X POST '.../chat/completions' -H 'Authorization: Bearer $HY3_API_KEY' \
  -d '{"model":"not-a-real-model","messages":[{"role":"user","content":"hi"}]}'
```

```json
{
  "error": {
    "type": "gateway_error",
    "code": "400004",
    "message": "The model or service ID not-a-real-model does not exist...",
    "message_zh": "请求中的模型或服务 ID not-a-real-model 不存在,请检查服务 ID 是否正确。",
    "request_id": "aced97d2-4fc6-401f-b363-95ed89b6f20c"
  }
}
```

`400004` 是**业务错误**(参数/服务问题),重试无意义,应直接修请求。

---

## 2. 分类重试策略

```python
import time
from openai import OpenAI, APITimeoutError, RateLimitError, APIConnectionError, APIStatusError

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30.0, max_retries=0)

def chat_with_retry(messages, max_attempts=4, backoff_base=0.5):
    for attempt in range(1, max_attempts + 1):
        try:
            return client.chat.completions.create(model="hy3", messages=messages)
        except (APITimeoutError, APIConnectionError) as e:
            print(f"[尝试 {attempt}] 网络/超时: {type(e).__name__}")     # 可重试
        except RateLimitError as e:
            print(f"[尝试 {attempt}] 限流 429: {type(e).__name__}")      # 可重试
        except APIStatusError as e:
            print(f"[业务错误 {e.status_code}, 不重试]")                # 4xx 直接抛
            raise
        if attempt < max_attempts:
            time.sleep(backoff_base * (2 ** (attempt - 1)))             # 指数退避: 0.5,1,2,4...
    raise RuntimeError("重试耗尽")
```

**核心原则**:
- **可重试**:超时、连接错误、`429` 限流、`5xx` 服务端错误 → 指数退避后重试。
- **不可重试**:`400`(参数错)、`401`(鉴权)、`404` 等 4xx → 修代码,重试浪费配额。

---

## 3. 指数退避(Exponential Backoff)

```python
wait = backoff_base * (2 ** (attempt - 1))   # 0.5s → 1s → 2s → 4s ...
time.sleep(wait)
```

配合**抖动(jitter)**可进一步避免多个客户端同时重试撞车:`wait = wait * (0.5 + random())`。

---

## 4. 错误码速查

| HTTP | code | 含义 | 处理 |
|------|------|------|------|
| 400 | `400004` | model/服务 ID 不存在 | 核对 `model=hy3`,开通服务 |
| 401 | — | Key 失效/缺失 | 重新生成 Key |
| 429 | — | 触发限流 | 退避重试 / 提配额 |
| 5xx | — | 网关抖动 | 退避重试 |

> 排查时把响应里的 `request_id` 一并提交给 tokenhub,便于定位。
