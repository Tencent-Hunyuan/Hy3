# 04 Tool calling

Complete a function tool call with Chat Completions.

```bash
uv run --env-file .env python examples/04_tool_calling.py
```

The script declares `get_weather`, parses `tool_calls`, executes a local demo function, and returns the result as a `role: "tool"` message with the matching `tool_call_id`. It repeats the loop until the model returns final text.

The weather function returns fixed demo data and does not call a real weather service.

## Output example

```text
深圳今天天气是**晴天**，当前气温为 **28°C**。整体比较温暖舒适，适合外出活动，不过紫外线可能较强，建议做好防晒措施~ ☀️
```

English translation: “The weather in Shenzhen is sunny today, with a current temperature of 28°C. It is warm and comfortable, but UV levels may be high.”
