# 01 基础对话

[English](01_basic_chat.md) · [索引](README_CN.md) · [脚本](01_basic_chat.py)

## 用途

学习最小而完整的对话流程：构造第一次请求、规范化响应、把 assistant content 加入历史，再发送第二个用户问题。对应脚本是 [`01_basic_chat.py`](01_basic_chat.py)。

## 配置

按照 [API 索引](README_CN.md)配置 `examples/api/.env`。脚本使用 `Hy3Config.from_env()`，只创建一个 client，并通过 `reasoning_extra_body` 应用当前后端的 `no_think` 映射。

## 完整请求

第一次请求传给 SDK 的全部字段如下：

```python
{
    "model": config.model,
    "messages": [
        {"role": "user", "content": "Hello! Briefly introduce yourself."}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512,
    "extra_body": reasoning_extra_body(config, "no_think"),
}
```

第一次 completion 规范化后，第二次请求保持相同 model 和采样字段，并发送以下完整历史：

```python
[
    {"role": "user", "content": "Hello! Briefly introduce yourself."},
    {"role": "assistant", "content": first["content"]},
    {
        "role": "user",
        "content": "What kinds of tasks can you help me with?",
    },
]
```

`build_request` 会复制每个 message dict，因此构造请求不会修改调用方传入的消息对象。

## 响应解析

`summarize_completion` 只读取第一个 choice，并返回：

- `model` 与 assistant `content`；
- 规范化后的 `reasoning` 和 `reasoning_details`；
- `finish_reason`；
- 普通 dict 形式的 `usage`，缺失时为 `None`。

第二轮历史有意只保存 assistant content。如果历史还必须保留结构化 reasoning 或工具调用，请使用[工具调用指南](04_tool_calling_CN.md)中的 `assistant_message_to_dict`。

## 运行

从仓库根目录运行：

```bash
python examples/api/01_basic_chat.py
```

该命令会使用已配置的 API。下方内容来自确定性单元测试 fixture，不是实时模型调用。

## 示例输出

**确定性离线示例**

```text
Single-turn response:
content: I am Hy3.
reasoning: brief plan
finish_reason: stop
usage.total_tokens: 5

Multi-turn response:
content: I can help with APIs.
reasoning: ""
finish_reason: stop
usage.total_tokens: 5
```

## 限制与注意事项

- 上述确定性文本是测试数据；实时措辞与 token usage 会变化。
- 示例假设 completion 至少有一个 choice；缺少 choices 时共享 normalizer 会抛出异常。
- 示例不处理流式输出、工具执行，也不会把 reasoning 字段加入第二轮 assistant 历史。
- 该短命 CLI 创建 client 后依赖进程退出释放资源。
