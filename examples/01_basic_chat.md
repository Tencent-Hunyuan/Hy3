<p align="left">
    <a href="./zh-cn/01_basic_chat.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>

# Example 01: Basic chat

This example demonstrates single-turn and multi-turn chat with the Hy3 OpenAI-compatible API.

> Related: [Examples Index](./README.md) | [API Quickstart](../quickstart.md)

## Run

```bash
export HY3_BASE_URL="${HY3_BASE_URL:-http://127.0.0.1:8000/v1}"
export HY3_API_KEY="${HY3_API_KEY:-EMPTY}"
export HY3_MODEL="${HY3_MODEL:-hy3}"
python examples/01_basic_chat.py
```

## Full request: single-turn

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

Equivalent HTTP body:

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

## Response parsing

```python
message = response.choices[0].message
print(message.content)
print(response.choices[0].finish_reason)
print(response.usage)
```

## Sample output

```text
=== single-turn ===
assistant: Hy3 适合代码生成、工具调用、长上下文问答等开发者场景。它可以作为 OpenAI-compatible API 接入现有应用。
finish_reason: stop
usage: CompletionUsage(completion_tokens=..., prompt_tokens=..., total_tokens=...)
```

Actual wording and token counts may vary with sampling parameters and server configuration.
