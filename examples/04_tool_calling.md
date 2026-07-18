# 04 · Tool Calling

## 说明

1. 单次请求中解析 `tool_calls`
2. 本地执行工具后，以 `role=tool` 回传结果，完成多轮工具循环

## 运行

```bash
python 04_tool_calling.py
```

## 请求

- `tools`：OpenAI function 格式
- `tool_choice`: `"auto"`
- 本地部署需启用 tool parser（见仓库 README）
- 云端网关若未透传 tools，可能仅返回文本

## 响应字段

```text
message.tool_calls[i].id
message.tool_calls[i].function.name
message.tool_calls[i].function.arguments
```

工具结果使用 `role: tool` 与 `tool_call_id` 写回 `messages`。

## 示例输出

环境：腾讯云 TokenHub。

```text
=== one-shot tool call ===
content: 
tool_calls: [ChatCompletionMessageFunctionToolCall(id='chatcmpl-tool-da6bbd5b878f4efa9026c66f04aec5db', function=Function(arguments='{"city": "北京"}', name='get_weather'), type='function')]

=== multi-turn tool loop ===
round1 content: 
round1 tool_calls: [ChatCompletionMessageFunctionToolCall(id='chatcmpl-tool-a4430a70de96d635', function=Function(arguments='{"city": "上海"}', name='get_weather'), type='function')]
tool result: {"city": "上海", "weather": "晴", "temp_c": 26}
round2 final: 上海今天天气晴朗，气温为26摄氏度，气候舒适宜人。
```
