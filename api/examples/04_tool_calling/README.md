# Tool calling：多轮工具循环

启动服务时必须启用工具解析。vLLM 需要 `--enable-auto-tool-choice --tool-call-parser hy_v3`，SGLang 使用 `--tool-call-parser hunyuan`。

```bash
python api/examples/04_tool_calling/tool_calling.py
```
完整请求、响应解析和工具实现见 [`tool_calling.py`](tool_calling.py)。第一次请求携带 JSON Schema：

```python
response = client.chat.completions.create(
    model=model,
    messages=messages,
    tools=TOOLS,
    tool_choice="auto",
)
```

脚本解析每个 `message.tool_calls`，按函数名白名单分发，使用 `json.loads` 解析参数，再以相同 `tool_call_id` 追加 `role=tool` 的结果。随后将完整消息历史再次提交，直到模型返回普通文本；最多允许 5 轮，避免异常模型行为造成无限循环。生产代码还应对工具执行设置权限、超时和输出大小限制。

```text
=== Model round 1 ===
id: chatcmpl-d41
model: hy3
role: assistant
content: None
tool_call: id=call_7, name=get_weather, arguments={"city":"深圳"}
finish_reason: tool_calls
usage: prompt=86, completion=18, total=104
tool result (call_7): {"city": "深圳", "temperature_c": 26, "condition": "晴"}
=== Model round 2 ===
id: chatcmpl-d42
model: hy3
role: assistant
content: 深圳当前约 26°C、晴，建议穿短袖并注意防晒。
finish_reason: stop
usage: prompt=132, completion=28, total=160
```
