# 04 Tool Calling：一次调用与多轮工具循环

源码：[`04_tool_calling.py`](04_tool_calling.py)

示例使用内置的确定性天气数据，不调用第三方天气服务。

## 运行

只解析并执行一轮工具调用：

```bash
python 04_tool_calling.py --single
```

运行完整工具闭环：

```bash
python 04_tool_calling.py
```

## 完整请求

```python
response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    tools=TOOLS,
    tool_choice="required",  # 第一轮保证演示工具调用，后续轮次改为 auto
    parallel_tool_calls=True,
    temperature=0.2,
    max_tokens=1024,
    extra_body={"thinking": {"type": "disabled"}},
)
```

`TOOLS` 中的函数参数使用 JSON Schema，并设置 `additionalProperties: false`。

## 完整响应解析与回填

当 `finish_reason=tool_calls` 时：

1. 遍历 `message.tool_calls`，而不是只处理第一个；
2. 从白名单查找函数，解析并验证 `function.arguments`；
3. 执行本地函数；
4. 把完整 assistant 消息加入 `messages`；
5. 为每个结果追加带相同 `tool_call_id` 的 `tool` 消息；
6. 再次调用模型，直到得到最终文本或达到 5 轮上限。

```python
messages.append(assistant_message_dict(message))
messages.append(
    {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps(result, ensure_ascii=False),
    }
)
```

`assistant_message_dict` 会保留 `content`、`tool_calls` 和可能存在的 `reasoning_content`，因此也能作为“保留式思考 + 工具调用”的历史序列化基础。

## 示例输出

```text
round 1: finish_reason=tool_calls, usage={...}
tool request: get_weather {"city":"北京"}
tool result: {"city":"北京","temperature_c":28,"condition":"晴","humidity":42}
tool request: get_weather {"city":"上海"}
tool result: {"city":"上海","temperature_c":31,"condition":"多云","humidity":67}
round 2: finish_reason=stop, usage={...}
assistant: 上海 31°C，北京 28°C，因此上海更暖和。
```

生产代码还应为工具增加权限控制、超时、审计和更严格的业务参数校验。
