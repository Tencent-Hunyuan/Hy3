### `error_handling`

#### **说明**

处理请求中的超时、限流、网络错误，实现自动重试与退避机制。

```
# 错误处理与重试示例：超时、限流、网络错误

本示例演示如何处理 Hy3 API 请求中的常见错误（超时、限流、网络问题），并实现自动重试与退避机制。

## 关键点
1. 使用 `try-except` 捕获 `OpenAIError`、`TimeoutError`、`ConnectionError`。
2. 定义指数退避重试函数。
3. 通过 `requests` 适配器配置最大重试次数和退避策略。

## 示例输出（模拟错误并重试）
- 限流错误（429）：触发重试，延迟后成功。
- 超时错误（Timeout）：重试后恢复。
- 网络错误（ConnectionError）：连接恢复后完成请求。
```

**代码块 (**`**error_handling.py)**`

```python
import time
from openai import OpenAI, OpenAIError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# 定义重试函数
def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        retry_count = 3
        backoff_base = 2
        for attempt in range(retry_count + 1):
            try:
                return func(*args, **kwargs)
            except (OpenAIError, TimeoutError, ConnectionError) as e:
                if attempt == retry_count:
                    raise e
                print(f"错误：{e}. 重试 {attempt + 1} 次...")
                time.sleep(backoff_base ** attempt)
    return wrapper

# 创建客户端并配置重试策略
client = OpenAI(api_key="YOUR_API_KEY", base_url="https://tokenhub.tencentmaas.com/v1")
client.http_client.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=2)))

# 模拟错误请求
@retry_with_backoff
def send_request(prompt):
    return client.chat.completions.create(
        model="hunyuan-turbo",
        messages=[{"role": "user", "content": prompt}],
    )

# 发送请求并捕获错误
try:
    response = send_request("解释量子纠缠")
except Exception as e:
    print(f"请求失败：{e}")
else:
    print(f"返回结果：{response.choices[0].message.content}")
```

**示例输出**

```
请求触发限流，错误信息：Rate limit exceeded. Retrying in 5 seconds...
重试成功，返回结果：量子纠缠是量子力学中的现象...
```