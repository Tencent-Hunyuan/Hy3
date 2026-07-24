# 08 Responses API tool calling

Complete a function tool call and return a `function_call_output` Item.

```bash
uv run --env-file .env python examples/08_responses_tool_calling.py
```

The script finds a `function_call` in `response.output`, parses its JSON-string `arguments`, executes the local demo function, and sends back a `function_call_output` whose `call_id` matches the original call. The final text is read from `response.output_text`.

## Output example

```text
深圳今天的天气是**晴天**，当前气温为 **28℃**。
```

English translation: “The weather in Shenzhen is sunny today, with a current temperature of 28°C.” The weather function returns fixed demo data.
