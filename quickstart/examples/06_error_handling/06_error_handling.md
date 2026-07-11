# Example 6: Error Handling & Retry（错误处理与重试）

## 1.目标

展示生产环境的健壮性处理，包括超时处理、限流重试、网络错误处理和指数退避策略。

## 2.错误类型

| 错误码 | 错误类型 | 处理策略 |
|--------|----------|----------|
| 401 | Unauthorized | 检查 API Key，不重试 |
| 403 | Forbidden | 检查权限，不重试 |
| 429 | Too Many Requests | 指数退避重试 |
| 500 | Internal Server Error | 有限次数重试 |
| 502 | Bad Gateway | 有限次数重试 |
| 503 | Service Unavailable | 指数退避重试 |
| 504 | Gateway Timeout | 重试 |
| 网络错误 | Connection Reset, Timeout | 有限次数重试 |

## 3.超时处理

### 3.1请求示例

#### Python

```python
from openai import OpenAI, APIConnectionError, APITimeoutError
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
    timeout=30,
)

messages = [
    {"role": "user", "content": "请写一篇关于人工智能的长文，不少于500字。"},
]

print("=== 超时处理示例 ===")
try:
    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        max_tokens=2000,
    )
    print("成功!")
    print("回答长度:", len(response.choices[0].message.content), "字符")
except APITimeoutError:
    print("错误: 请求超时")
except APIConnectionError:
    print("错误: 网络连接失败")
except Exception as e:
    print(f"错误: {e}")
```

### 3.2示例输出

```
=== 超时处理示例 ===
成功!
回答长度: 850 字符
```

## 4指数退避重试

### 4.1请求示例

#### Python

```python
from openai import OpenAI, RateLimitError, APIError
from dotenv import load_dotenv
import os
import time
import math

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

messages = [
    {"role": "user", "content": "你好"},
]

def chat_with_retry(max_retries=5, initial_delay=1):
    for attempt in range(max_retries):
        try:
            print(f"尝试 {attempt + 1}/{max_retries}")
            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
            )
            return response.choices[0].message.content
        
        except RateLimitError:
            delay = initial_delay * (2 ** attempt) + math.random()
            print(f"限流! 等待 {delay:.2f} 秒后重试...")
            time.sleep(delay)
        
        except APIError as e:
            if e.status_code in [500, 502, 503, 504]:
                delay = initial_delay * (2 ** attempt) + math.random()
                print(f"服务端错误 ({e.status_code})! 等待 {delay:.2f} 秒后重试...")
                time.sleep(delay)
            else:
                raise
        
        except Exception as e:
            print(f"未知错误: {e}")
            raise
    
    raise Exception("超过最大重试次数")

print("=== 指数退避重试示例 ===")
try:
    result = chat_with_retry()
    print("成功!")
    print("回答:", result)
except Exception as e:
    print(f"最终失败: {e}")
```

### 4.2响应解析

指数退避策略按以下公式计算等待时间：

```
delay = initial_delay * (2^attempt) + random_jitter
```

| 重试次数 | 等待时间（初始延迟=1秒） |
|----------|------------------------|
| 1 | ~1 秒 |
| 2 | ~2 秒 |
| 3 | ~4 秒 |
| 4 | ~8 秒 |
| 5 | ~16 秒 |

### 4.3示例输出

```
=== 指数退避重试示例 ===
尝试 1/5
限流! 等待 1.23 秒后重试...
尝试 2/5
限流! 等待 2.56 秒后重试...
尝试 3/5
成功!
回答: 你好！我是混元，是由腾讯开发的大模型。
```

## 5完整错误处理封装

### 5.1请求示例

#### Python

```python
from openai import OpenAI, RateLimitError, APIError, APIConnectionError, APITimeoutError, BadRequestError
from dotenv import load_dotenv
import os
import time
import math
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
    timeout=30,
)

def safe_chat_completion(messages, model="hy3", max_retries=5, initial_delay=1, **kwargs):
    for attempt in range(max_retries):
        try:
            logger.info(f"第 {attempt + 1} 次尝试")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            logger.info(f"请求成功，Token 消耗: {response.usage.total_tokens}")
            return response
        
        except BadRequestError as e:
            logger.error(f"请求参数错误: {e}")
            raise
        
        except RateLimitError as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt) + math.random()
                logger.warning(f"限流 (第 {attempt + 1} 次)，等待 {delay:.2f} 秒")
                time.sleep(delay)
            else:
                logger.error("超过最大重试次数，限流错误")
                raise
        
        except APIConnectionError as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt) + math.random()
                logger.warning(f"网络连接错误 (第 {attempt + 1} 次)，等待 {delay:.2f} 秒")
                time.sleep(delay)
            else:
                logger.error("超过最大重试次数，网络连接错误")
                raise
        
        except APITimeoutError as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt) + math.random()
                logger.warning(f"请求超时 (第 {attempt + 1} 次)，等待 {delay:.2f} 秒")
                time.sleep(delay)
            else:
                logger.error("超过最大重试次数，请求超时")
                raise
        
        except APIError as e:
            if e.status_code in [500, 502, 503, 504]:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt) + math.random()
                    logger.warning(f"服务端错误 {e.status_code} (第 {attempt + 1} 次)，等待 {delay:.2f} 秒")
                    time.sleep(delay)
                else:
                    logger.error(f"超过最大重试次数，服务端错误 {e.status_code}")
                    raise
            else:
                logger.error(f"API 错误 {e.status_code}: {e}")
                raise
        
        except Exception as e:
            logger.error(f"未知错误: {e}")
            raise
    
    raise Exception("超过最大重试次数")

print("=== 完整错误处理示例 ===")
messages = [
    {"role": "user", "content": "请介绍一下腾讯混元大模型。"},
]

try:
    response = safe_chat_completion(messages)
    print("成功!")
    print("回答:", response.choices[0].message.content[:100], "...")
except Exception as e:
    print(f"失败: {e}")
```

### 5.2示例输出

```
=== 完整错误处理示例 ===
INFO:__main__:第 1 次尝试
INFO:__main__:请求成功，Token 消耗: 85
成功!
回答: 腾讯混元大模型是由腾讯研发的大语言模型，具备强大的中文创作能力、复杂语...
```

## 6错误处理最佳实践

1. **区分可重试和不可重试错误**：
   - 可重试：429（限流）、500/502/503/504（服务端错误）、网络错误、超时
   - 不可重试：401（权限）、403（禁止）、400（参数错误）

2. **指数退避策略**：避免在短时间内重复请求，给服务端恢复时间

3. **添加随机抖动**：防止多个客户端同时重试造成新的限流

4. **设置最大重试次数**：避免无限重试导致资源耗尽

5. **记录详细日志**：便于问题排查和监控

6. **设置合理超时**：根据请求类型和预期响应时间设置

## 7关键点

1. **超时配置**：在 OpenAI 客户端初始化时设置 `timeout`
2. **指数退避**：`delay = initial_delay * (2^attempt) + random_jitter`
3. **错误分类**：区分可重试和不可重试错误
4. **日志记录**：记录每次尝试和错误信息
5. **最大重试**：设置合理的最大重试次数

测试代码请参考06_error_handling.ipynb/06_error_handling.py