# 01 基础对话（Basic chat）

这个示例先发送一条消息，再演示怎样维护
`system → user → assistant → user` 的多轮历史。完整代码见
[01_basic_chat.py](01_basic_chat.py)。

## 请求代码

单轮请求使用 Hosted API 顶层 `thinking` 字段：

```python
single = create_chat_completion(
    client,
    model=config.model,
    messages=[{"role": "user", "content": "用一句话解释什么是 API。"}],
    temperature=0.3,
    max_tokens=512,
    extra_body={"thinking": {"type": "disabled"}},
)
```

多轮请求先保存第一次返回的 assistant message，再追加下一条 user 消息：

```python
messages = [
    {"role": "system", "content": "你是一个简洁、准确的编程助手。"},
    {"role": "user", "content": "Python 列表推导式是什么？"},
]
first = create_chat_completion(client, messages=messages, **shared)
messages.append(assistant_message_dict(first.choices[0].message))
messages.append({"role": "user", "content": "给一个只保留偶数的例子。"})
second = create_chat_completion(client, messages=messages, **shared)
```

`response_summary` 解析 `model`、`finish_reason`、assistant 的 `content`、可选
`reasoning_content`/`tool_calls` 和 `usage`，同时省略 request ID 与 headers。

## 运行结果

```powershell
python examples/api/01_basic_chat.py
```

以下输出采集于 2026-07-17，使用 TokenHub 广州入口、`model=hy3`、
`temperature=0.3` 和 `max_tokens=512`。request ID 和 headers 已省略，模型文本再次
运行结果可能变化。

```text
=== Single turn ===
{
  "model": "hy3",
  "finish_reason": "stop",
  "message": {
    "role": "assistant",
    "reasoning_content": null,
    "content": "API（应用程序编程接口）是一套预先定义的规则和工具，让不同的软件系统能够相互通信、交换数据或调用功能。",
    "tool_calls": null
  },
  "usage": {"completion_tokens": 28, "prompt_tokens": 21, "total_tokens": 49}
}

=== Multi turn ===
{
  "model": "hy3",
  "finish_reason": "stop",
  "message": {
    "role": "assistant",
    "reasoning_content": null,
    "content": "下面是一个**只保留偶数**的列表推导式例子：\n\n```python\nnumbers = [1, 2, 3, 4, 5, 6, 7, 8]\nevens = [x for x in numbers if x % 2 == 0]\n\nprint(evens)\n# 输出: [2, 4, 6, 8]\n```\n\n解释：\n- `for x in numbers`：遍历原列表\n- `if x % 2 == 0`：只保留能被 2 整除的数（偶数）\n- `x`：把满足条件的元素放进新列表",
    "tool_calls": null
  },
  "usage": {"completion_tokens": 131, "prompt_tokens": 376, "total_tokens": 507}
}
```

脚本会对 429/502/503/504、连接失败和超时做有限重试，具体策略见示例 06。

## 容易踩坑

- 多轮历史需包含 assistant 消息，模型才能接续上一轮上下文。
- 启用思考或工具调用后，还要保留 assistant 消息中的 `reasoning_content` 和
  `tool_calls`。
