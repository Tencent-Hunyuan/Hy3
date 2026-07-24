# 08 Responses API 工具调用

使用 Responses API 完成函数工具调用，并回传 `function_call_output`。

## 运行

```bash
uv run --env-file .env python examples/08_responses_tool_calling.py
```

## 请求和解析

第一次请求通过扁平结构的 `tools` 声明 `get_weather`。

脚本遍历 `response.output`，找到 `type: "function_call"` 后解析 `arguments` 并执行本地函数。

第二次请求将原工具调用和工具结果放入 `input`：

```json
{
  "type": "function_call_output",
  "call_id": "与 function_call.call_id 相同",
  "output": "工具结果 JSON 字符串"
}
```

最终从 `response.output_text` 读取模型回答。

## 输出示例

```text
深圳今天的天气是**晴天**，当前气温为 **28℃**。
```

天气函数返回的是固定演示数据，不会访问真实天气服务。
