# 04 工具调用

[English](04_tool_calling.md) · [索引](README_CN.md) · [脚本](04_tool_calling.py)

## 用途

运行带手工参数校验、结构化错误、同一 assistant 回合多个调用和确定性演示数据的有界工具循环。实现位于 [`04_tool_calling.py`](04_tool_calling.py)，返回的调用会被顺序执行。

## 配置

在 `examples/api/.env` 中配置后端，并用兼容 parser 启动服务。仓库的 [vLLM 命令](../../README_CN.md#vllm)使用 `--tool-call-parser hy_v3`、`--reasoning-parser hy_v3` 和 `--enable-auto-tool-choice`。文档中的 [SGLang 命令](../../README_CN.md#sglang)使用 `hunyuan` tool/reasoning parser。

内置工具只支持北京和深圳，数值是固定演示数据，不是天气服务。

## 完整请求

第一轮从以下消息开始：

```python
messages = [
    {
        "role": "user",
        "content": "Use the weather tool for Shenzhen, then answer briefly.",
    }
]
```

每一轮发送以下全部字段：

```python
client.chat.completions.create(
    model=config.model,
    messages=messages,
    tools=[
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Return deterministic demo weather data for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "City name: Beijing or Shenzhen.",
                        }
                    },
                    "required": ["city"],
                    "additionalProperties": False,
                },
            },
        }
    ],
    tool_choice="auto",
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
    extra_body=reasoning_extra_body(config, "no_think"),
)
```

## 响应解析

每个响应按以下流程处理：

1. 要求至少一个 choice 和一条 message。
2. 缺少 tool calls 时，把它视为最终 assistant 响应，并规范化 content、reasoning、finish reason 和 usage。
3. 拒绝 string、bytes、mapping 或不可迭代的 tool-call 容器。
4. 规范化每个调用，并要求非空字符串 `id` 和 function 对象。
5. 每轮只追加一条 assistant message，同时保留规范化后的 tool calls 和 reasoning details。
6. 顺序处理所有返回的调用，每个结果追加一条 `role="tool"` 消息。同一 assistant 回合可以包含多个调用，每条 tool message 的 `tool_call_id` 都与来源调用一致。

`execute_tool_call` 会在解析参数前拒绝未知工具。无效 JSON、非对象 JSON、缺失/非字符串 city，以及演示数据表之外的城市都会变成结构化 tool result，而不是直接抛出未结构化异常。四轮后仍没有最终回答时，循环抛出 `tool loop exceeded max_rounds=4`。

## 运行

从仓库根目录运行：

```bash
python examples/api/04_tool_calling.py
```

该命令使用已配置 API。以下同一 assistant 回合多调用序列来自确定性单元测试数据；Python 循环会先执行 call 1，再执行 call 2。

## 示例输出

**确定性离线示例**

```text
assistant messages appended for the round: 1
tool messages appended: 2
call_1 -> {"ok": true, "city": "Beijing", "condition": "sunny", "temperature_c": 24, "source": "demo data"}
call_2 -> {"ok": true, "city": "Shenzhen", "condition": "rainy", "temperature_c": 29, "source": "demo data"}
tool_call_id order: call_1, call_2
final assistant content: Done.
```

## 限制与注意事项

- 天气值是演示数据，不能当作当前天气展示；确定性输出中的 `source` 字段固定为 `demo data`。
- 只允许 `get_weather`；未知名称返回 `unknown_tool`。
- 循环不使用 `eval`；参数必须是能够解码为对象的 JSON 字符串。
- 工具错误会作为 tool result 返回给模型，让模型有机会恢复，但不保证一定恢复。
- `max_rounds=4` 限制重复工具调用；调整该值会改变安全边界。
- 生产工具还需要认证、授权、超时、审计和领域校验。
