<p align="left">
    <a href="../06_error_handling_retry.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

# 示例 06：错误处理与重试

本示例演示如何针对超时、限流、网络错误和可重试的服务端错误，显式使用带抖动的指数退避重试。

> 相关文档：[示例索引](./README.md) | [API 快速开始](../../quickstart_CN.md)

## 运行

```bash
python examples/zh-cn/06_error_handling_retry.py
```

## 完整请求

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "请用三点说明 API 请求重试为什么需要退避和抖动。"}],
    temperature=0.3,
    max_tokens=512,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

## 响应解析

```python
print(response.choices[0].message.content)
print(response.usage)
```

## 重试策略

重试：

- `RateLimitError` / HTTP `429`
- `APITimeoutError`
- `APIConnectionError`
- HTTP `500`, `502`, `503`, `504`

不要盲目重试：

- HTTP `400`：请求格式、参数或 chat-template 问题
- HTTP `401` / `403`：认证问题
- HTTP `404`：端点或模型名错误
- 可能产生副作用的重复工具执行错误

## 示例输出

```text
第 1 次尝试: 被限流
0.91 秒后重试...
第 2 次尝试: 网络/超时错误: APITimeoutError
1.73 秒后重试...
1. 退避可以避免大量请求在服务繁忙时继续冲击服务端。
2. 抖动可以防止多个客户端同时重试造成“惊群”。
3. 对可恢复错误重试、对参数错误快速失败，可以提升稳定性并减少无效请求。
用量: CompletionUsage(...)
```
