# 06 - Error Handling & Retry（错误处理与重试）

演示超时、限流、网络错误的重试与指数退避。

## 说明

生产环境中网络波动和限流难以避免。推荐策略：
- 设置合理的超时时间
- 对可重试错误（429、5xx、网络超时）实施指数退避重试
- 对不可重试错误（401、400）直接报错

## 运行方式

```bash
pip install openai python-dotenv
cp ../../.env.example ../../.env  # 编辑 .env 填入密钥
python error_handling_retry.py
```

## 代码

```python
import time
import random
import os
from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=30.0,
)

def chat_with_retry(messages, max_retries=3, base_delay=1.0):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
                temperature=0.9,
                timeout=15.0,  # 单次请求超时
            )
            return response

        except RateLimitError as e:
            print(f"限流 (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                print(f"等待 {delay:.1f}s 后重试...")
                time.sleep(delay)
            last_error = e

        except APITimeoutError as e:
            print(f"超时 (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"等待 {delay:.1f}s 后重试...")
                time.sleep(delay)
            last_error = e

        except APIError as e:
            if e.status_code and 500 <= e.status_code < 600:
                print(f"服务端错误 (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    print(f"等待 {delay:.1f}s 后重试...")
                    time.sleep(delay)
                last_error = e
            else:
                raise  # 4xx 等不可重试错误直接抛出

    raise last_error


# 使用示例
try:
    response = chat_with_retry([
        {"role": "user", "content": "你好！"}
    ])
    print(f"成功: {response.choices[0].message.content}")
except Exception as e:
    print(f"最终失败: {e}")
```

### 重试策略说明

| 错误类型 | 是否重试 | 策略 |
|---------|---------|------|
| `RateLimitError` (429) | 是 | 指数退避 + 随机抖动 |
| `APITimeoutError` (408) | 是 | 指数退避 |
| `APIError` 5xx | 是 | 指数退避 |
| `APIError` 4xx（非429） | 否 | 直接抛出 |
| `AuthenticationError` (401) | 否 | 直接抛出 |
| `BadRequestError` (400) | 否 | 直接抛出 |

---

完整源码：[error_handling_retry.py](./error_handling_retry.py)
