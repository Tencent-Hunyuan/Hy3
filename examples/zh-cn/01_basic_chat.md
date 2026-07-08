<p align="left">
    <a href="../01_basic_chat.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

# 示例 01：基础聊天

本示例演示如何通过兼容 OpenAI 的 Hy3 API 进行单轮和多轮聊天。

> 相关文档：[示例索引](./README.md) | [API 快速开始](../../quickstart_CN.md)

## 运行

```bash
export HY3_BASE_URL="${HY3_BASE_URL:-http://127.0.0.1:8000/v1}"
export HY3_API_KEY="${HY3_API_KEY:-EMPTY}"
export HY3_MODEL="${HY3_MODEL:-hy3}"
python examples/zh-cn/01_basic_chat.py
```

## 完整请求：单轮

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "请用三句话介绍 Hy3 适合什么开发场景。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=300,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

等价的 HTTP 请求体：

```json
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "请用三句话介绍 Hy3 适合什么开发场景。"}
  ],
  "temperature": 0.9,
  "top_p": 1.0,
  "max_tokens": 300,
  "chat_template_kwargs": {"reasoning_effort": "no_think"}
}
```

## 响应解析

```python
message = response.choices[0].message
print(message.content)
print(response.choices[0].finish_reason)
print(response.usage)
```

## 示例输出

```text
=== 单轮 ===
assistant: Hy3 适合代码生成、工具调用、长上下文问答等开发者场景。它可以作为兼容 OpenAI 的 API 接入现有应用。
结束原因: stop
用量: CompletionUsage(completion_tokens=..., prompt_tokens=..., total_tokens=...)
```

实际措辞和 token 数量会随采样参数和服务配置变化。
