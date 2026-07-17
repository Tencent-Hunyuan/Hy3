# 01 — Basic chat

目标：展示一次非流式单轮调用，以及显式维护 `system → user → assistant → user`
历史的多轮调用。完整代码见 [01_basic_chat.py](01_basic_chat.py)。

## 完整请求

单轮请求使用 Hosted API 顶层 `thinking` 字段：

```python
single = create_chat_completion(
    client,
    model=config.model,
    messages=[{"role": "user", "content": "用一句话介绍 Hy3。"}],
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

## 运行与真实输出

```powershell
python examples/api/01_basic_chat.py
```

2026-07-17 在 TokenHub 广州入口以 `model=hy3`、`temperature=0.3`、
`max_tokens=512` 实测通过。下面是脚本核心公开字段的脱敏实测摘录；request ID 和 headers
未进入输出，模型文本再次运行时可能变化。

```text
=== Single turn ===
{
  "model": "hy3",
  "finish_reason": "stop",
  "message": {
    "role": "assistant",
    "reasoning_content": null,
    "content": "Hy3（混元大模型第三代）是腾讯研发的新一代大语言模型，具备更强的多模态理解与生成能力，支持复杂推理、代码编写及长文本处理等任务。",
    "tool_calls": null
  },
  "usage": {"completion_tokens": 39, "prompt_tokens": 21, "total_tokens": 60}
}

=== Multi turn ===
{
  "model": "hy3",
  "finish_reason": "stop",
  "message": {
    "role": "assistant",
    "reasoning_content": null,
    "content": "```python\nevens = [x for x in range(10) if x % 2 == 0]\n# 结果：[0, 2, 4, 6, 8]\n```\n\n说明：  \n- `range(10)` 生成 `0~9`  \n- `if x % 2 == 0` 只保留偶数  \n- 最终得到只包含偶数的列表",
    "tool_calls": null
  },
  "usage": {"completion_tokens": 86, "prompt_tokens": 256, "total_tokens": 342}
}
```

脚本通过公共 `create_chat_completion` 对 429/502/503/504、连接失败和超时做有限
重试；上面的业务请求与解析逻辑不因此改变。

常见错误：多轮历史遗漏 assistant 消息会丢失上下文；若后续启用思考或工具调用，
还必须保留 assistant 消息中的 `reasoning_content` 和 `tool_calls`。
