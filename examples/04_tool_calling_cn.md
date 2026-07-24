# 04 工具调用

使用 Chat Completions API 完成函数工具调用，并将本地函数结果回传给模型。

## 运行

```bash
uv run --env-file .env python examples/04_tool_calling.py
```

## 请求和解析

第一次请求通过 `tools` 声明 `get_weather`。

如果响应中的 `message.tool_calls` 不为空，脚本解析 `tool_call.function.arguments`，执行本地演示函数，再以 `role: "tool"` 和对应的 `tool_call_id` 回传结果。

脚本会循环处理工具调用，直到模型返回最终文本。

## 输出示例

```text
深圳今天天气是**晴天**，当前气温为 **28°C**。整体比较温暖舒适，适合外出活动，不过紫外线可能较强，建议做好防晒措施~ ☀️
```

天气函数返回的是固定演示数据，不会访问真实天气服务。
