<p align="left">
    <a href="../04_tool_calling.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

# 示例 04：工具调用

本示例同时演示单次工具调用响应，以及应用侧多轮工具执行循环。

> 相关文档：[示例索引](./README.md) | [API 快速开始](../../quickstart_CN.md)

## 服务端要求

启动服务时需要使用兼容 Hy3/Hunyuan 的工具解析器。对于 vLLM，请启用自动工具选择并设置 Hy3 parser。对于 SGLang，请使用它的 Hunyuan parser。

## 运行

```bash
python examples/zh-cn/04_tool_calling.py
```

## 完整请求

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "东京现在天气怎么样？请调用工具查询，并用摄氏度回答。"}],
    tools=TOOLS,
    tool_choice="auto",
    parallel_tool_calls=False,
    temperature=0.2,
    max_tokens=800,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

工具 schema 片段：

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {"type": "string"},
        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
      },
      "required": ["location", "unit"],
      "additionalProperties": false
    },
    "strict": true
  }
}
```

## 响应解析

```python
message = response.choices[0].message
for tc in message.tool_calls or []:
    name = tc.function.name
    args = json.loads(tc.function.arguments)
    result = TOOL_IMPLS[name](**args)
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "name": name,
        "content": json.dumps(result, ensure_ascii=False),
    })
```

然后用更新后的 `messages` 再次调用模型，让它生成最终答案。

## 示例输出

```text
=== 单次工具解析 ===
assistant 内容: None
工具调用:
- 名称: get_weather
  参数: {"location":"Tokyo","unit":"celsius"}

=== 多轮工具循环 ===
第 1 步: 模型请求 1 次工具调用
已执行 get_weather({'location': 'Tokyo', 'unit': 'celsius'}) -> {'location': 'Tokyo', 'unit': 'celsius', 'temperature': 21, 'condition': '多云间晴', 'source': '模拟天气服务'}
第 2 步: 模型请求 1 次工具调用
已执行 calculator({'expression': '17 * 23'}) -> {'expression': '17 * 23', 'result': 391}
最终答案: 东京当前示例天气为 21°C、多云间晴；17 * 23 = 391。
```

实际工具调用顺序可能不同。执行前务必校验工具参数。
