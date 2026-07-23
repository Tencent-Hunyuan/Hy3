\# 示例 6：错误处理与重试



\## 功能说明

演示如何优雅地处理 API 调用中可能出现的各种错误，包括超时、限流、网络错误等，并实现指数退避重试机制。



\## 适用场景

\- 生产环境中的稳定调用

\- 高并发场景下的容错

\- 网络不稳定的环境



\## 常见错误类型



| 错误类型 | 说明 | 是否可重试 |

|---------|------|-----------|

| `RateLimitError` | 请求频率超限 |  是（等待后重试） |

| `APITimeoutError` | 请求超时 | 是 |

| `APIConnectionError` | 网络连接失败 |  是 |

| `APIError` | 其他 API 错误 |  否（需排查） |

| `AuthenticationError` | API Key 无效 |  否（需修正） |



\## 完整请求（带重试装饰器）



```python

def call\_with\_retry(max\_retries=3):

&#x20;   def decorator(func):

&#x20;       def wrapper(\*args, \*\*kwargs):

&#x20;           for i in range(max\_retries):

&#x20;               try:

&#x20;                   return func(\*args, \*\*kwargs)

&#x20;               except Exception as e:

&#x20;                   print(f" 第 {i+1} 次尝试失败: {type(e).\_\_name\_\_}")

&#x20;                   if i == max\_retries - 1:

&#x20;                       raise  # 最后一次失败，向上抛出

&#x20;                   wait = 2 \*\* i  # 指数退避：1, 2, 4, 8...

&#x20;                   print(f"⏳ 等待 {wait} 秒后重试...")

&#x20;                   time.sleep(wait)

&#x20;           return None

&#x20;       return wrapper

&#x20;   return decorator



\# 使用示例

@call\_with\_retry(max\_retries=3)

def safe\_call():

&#x20;   return client.chat.completions.create(

&#x20;       model=MODEL,

&#x20;       messages=\[{"role": "user", "content": "你好"}],

&#x20;       max\_tokens=80,

&#x20;       extra\_body={"chat\_template\_kwargs": {"reasoning\_effort": "no\_think"}}

&#x20;   )



try:

&#x20;   response = safe\_call()

except Exception as e:

&#x20;   print(f" 最终失败: {e}")

```



\## 指数退避策略



| 重试次数 | 等待时间 | 累计等待 |

|---------|---------|---------|

| 第1次失败 | 1 秒 | 1 秒 |

| 第2次失败 | 2 秒 | 3 秒 |

| 第3次失败 | 4 秒 | 7 秒 |

| 第n次失败 | 2^(n-1) 秒 | - |



\## 响应解析



\### 成功响应

```python

\# 正常返回 ChatCompletion 对象

response = client.chat.completions.create(...)

print(response.choices\[0].message.content)

```



\### 错误响应

```python

try:

&#x20;   response = client.chat.completions.create(...)

except RateLimitError as e:

&#x20;   # HTTP 429 - 请求过多

&#x20;   print(f"限流: {e}")

except APITimeoutError as e:

&#x20;   # 超时

&#x20;   print(f"超时: {e}")

except APIError as e:

&#x20;   # 其他 API 错误

&#x20;   print(f"API 错误: {e}")

except Exception as e:

&#x20;   # 未知错误

&#x20;   print(f"未知错误: {e}")

```



\## 示例输出



```text

&#x20;正常调用（带重试保护）:

&#x20;成功! 回复: 你好！我是混元，是由腾讯开发的大模型...



&#x20;错误处理最佳实践:



1\. 使用 try-except 捕获异常

2\. 对限流/超时使用指数退避重试

3\. 设置合理的超时时间（如 30-60 秒）

4\. 记录错误日志便于调试

5\. 设置最大重试次数避免无限循环（如 3-5 次）

```



\## 最佳实践总结



\###  推荐做法

\- 对临时性错误（限流、超时）实施重试

\- 使用指数退避避免加重服务器负担

\- 设置最大重试次数（3-5次）

\- 记录详细的错误日志

\- 区分可重试和不可重试错误



\###  避免做法

\- 无限循环重试

\- 立即重试（无等待）

\- 忽略所有错误

\- 重试不可恢复的错误（如认证失败）

