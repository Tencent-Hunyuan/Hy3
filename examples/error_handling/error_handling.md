# 错误处理与重试示例

## 功能说明

本示例演示 Hy3 API 的错误处理与重试机制，包括超时、限流、网络错误的重试与指数退避策略。

## 前置条件

1. 安装依赖：`pip install openai python-dotenv`
2. 创建 `.env` 文件，配置 API 密钥：
   ```
   API_KEY=your_api_key
   BASE_URL=https://tokenhub.tencentmaas.com/v1
   ```

## 错误类型

| 错误类型 | 说明 | 是否可重试 |
|:---|:---|:---|
| `APITimeoutError` | 请求超时 | 是 |
| `APIConnectionError` | 网络连接失败 | 是 |
| `RateLimitError` | 请求被限流 | 是 |
| `APIError` | 服务端错误 | 视情况 |
| `AuthenticationError` | 认证失败 | 否 |

## 重试策略

### 指数退避 + Jitter

```python
delay = min(delay * 2, max_delay)
jitter = random.uniform(0, delay * 0.1)
wait_time = delay + jitter
```

**参数说明**：

| 参数 | 默认值 | 说明 |
|:---|:---|:---|
| `max_retries` | 3 | 最大重试次数 |
| `base_delay` | 1.0s | 初始延迟 |
| `max_delay` | 10.0s | 最大延迟 |

### 限流重试

限流错误需要特殊处理，优先使用错误响应中的 `reset_after` 字段：

```python
reset_after = getattr(e, 'reset_after', 1)
wait_time = reset_after + random.uniform(0, 1)
```

## 装饰器实现

```python
def retry_with_backoff(func, max_retries=3, base_delay=1.0, max_delay=10.0):
    def wrapper(*args, **kwargs):
        retries = 0
        delay = base_delay
        while retries < max_retries:
            try:
                return func(*args, **kwargs)
            except (APITimeoutError, APIConnectionError) as e:
                retries += 1
                jitter = random.uniform(0, delay * 0.1)
                wait_time = delay + jitter
                time.sleep(wait_time)
                delay = min(delay * 2, max_delay)
            except RateLimitError as e:
                retries += 1
                reset_after = getattr(e, 'reset_after', 1)
                wait_time = reset_after + random.uniform(0, 1)
                time.sleep(wait_time)
            except APIError as e:
                raise
    return wrapper
```

## 请求方式

### Python SDK

```python
@retry_with_backoff
def chat_with_retry(messages):
    return client.chat.completions.create(
        model="hy3",
        messages=messages,
        timeout=5.0,
    )
```

### cURL

```bash
curl -X POST https://tokenhub.tencentmaas.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  --max-time 5 \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

## 测试场景

### 场景 1：超时处理

```python
slow_client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    timeout=1.0,  # 故意设置很短
)

try:
    response = slow_client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "请写一篇长文"}],
    )
except APITimeoutError as e:
    print("请求超时")
```

### 场景 2：限流处理

```python
@retry_with_backoff
def limited_request():
    return client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "测试"}],
    )

# 模拟高频请求
for i in range(5):
    response = limited_request()
```

### 场景 3：网络错误处理

```python
@retry_with_backoff
def chat_with_retry(messages):
    return client.chat.completions.create(
        model="hy3",
        messages=messages,
    )

# 如果网络中断，会自动重试
response = chat_with_retry([{"role": "user", "content": "你好"}])
```

## 最佳实践

1. **设置合理超时**：建议设置 5-10 秒超时
2. **指数退避**：避免重试风暴
3. **Jitter**：防止多个客户端同时重试
4. **限流感知**：使用 `reset_after` 字段
5. **最大重试次数**：设置合理上限（3-5 次）
6. **区分错误类型**：认证错误不应重试

## 常见问题

### Q: 重试会导致重复请求吗？

**回答**：是的。如果请求已经被服务端处理但响应丢失，重试可能导致重复操作。对于写操作，建议使用幂等设计。

### Q: 如何处理认证错误？

**回答**：认证错误（401）不应重试，应立即检查 API Key 是否正确。

### Q: 限流后应该等多久？

**回答**：优先使用错误响应中的 `reset_after` 字段。如果没有该字段，使用指数退避。

## 运行方式

```bash
export API_KEY=your_api_key
export BASE_URL=https://tokenhub.tencentmaas.com/v1
python error_handling.py
```

## 示例输出

```
=== Error Handling & Retry 示例 ===

【完整请求参数】
  model: hy3
  messages: [{'role': 'user', 'content': '你好'}]
  timeout: 5.0
  retry策略: max_retries=3, base_delay=1.0s, max_delay=10.0s

【错误处理流程】

【成功响应解析】
  id: chatcmpl-abc123
  model: hy3
  finish_reason: stop
  content: 你好！有什么我可以帮你的吗？


=== 超时处理测试 ===

【请求参数】
  timeout: 1.0s (故意设置很短以触发超时)

【超时】请求在1秒内未完成
  错误: APITimeoutError


=== 限流处理测试 ===

【模拟高频请求】
  请求 #1...
    成功: 15 字符
  请求 #2...
    成功: 12 字符
  请求 #3...
    限流错误: RateLimitError - 第 1/3 次重试，等待 2.50s
    成功: 18 字符
```