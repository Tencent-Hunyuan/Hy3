# 04 Tool calling

[简体中文](04_tool_calling_CN.md) · [Index](README.md) · [Script](04_tool_calling.py)

## Purpose

Run a bounded tool loop with manual argument validation, structured errors, multiple calls returned in one assistant turn, and deterministic demo data. The implementation is [`04_tool_calling.py`](04_tool_calling.py); it executes returned calls sequentially.

## Configuration

Configure a backend in `examples/api/.env` and launch the server with compatible parsers. The repository's [vLLM command](../../README.md#vllm) uses `--tool-call-parser hy_v3`, `--reasoning-parser hy_v3`, and `--enable-auto-tool-choice`. The documented [SGLang command](../../README.md#sglang) uses the `hunyuan` tool and reasoning parsers.

The built-in tool supports only Beijing and Shenzhen. Its values are fixed demo data, not a weather service.

## Complete request

The first round starts with:

```python
messages = [
    {
        "role": "user",
        "content": "Use the weather tool for Shenzhen, then answer briefly.",
    }
]
```

Every round sends all of these fields:

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

## Response parsing

For each response, the loop:

1. Requires at least one choice and a message.
2. Treats missing tool calls as a final assistant response and normalizes content, reasoning, finish reason, and usage.
3. Rejects string, bytes, mapping, or non-iterable tool-call containers.
4. Normalizes every call and requires a non-empty string `id` plus a function object.
5. Appends exactly one assistant message for the round, preserving normalized tool calls and reasoning details.
6. Processes every returned call sequentially and appends one `role="tool"` message per result. A response may contain multiple calls in one assistant turn; each tool message uses the originating `tool_call_id`.

`execute_tool_call` rejects unknown tools before parsing arguments. Invalid JSON, non-object JSON, missing/non-string city values, and cities outside the demo table become structured tool results rather than arbitrary exceptions. After four rounds without a final answer, the loop raises `tool loop exceeded max_rounds=4`.

## Run

From the repository root:

```bash
python examples/api/04_tool_calling.py
```

This uses the configured API. The live section summarizes only the final CLI response; it does not reproduce intermediate calls. The following multi-call assistant turn remains deterministic unit-test data; the Python loop executes call 1 and then call 2.

## Example output

**Verified live evidence summary (sanitized; not literal stdout)**

The script's actual CLI output uses a fixed English label and prints the final result as JSON. This list is a reviewed summary, not a transcript:

- Backend: OpenRouter
- Model requested: `tencent/hy3:free`
- Model resolved: `tencent/hy3-20260706:free`
- Observed on: 2026-07-11
- Final assistant content: `Shenzhen is currently rainy with a temperature of 29°C.`
- `usage.total_tokens`: 306

The live CLI's final answer is consistent with the script's fixed `DEMO_WEATHER` data, not real current weather. The CLI does not print intermediate tool calls or tool results, so this live summary alone does not establish call IDs. The deterministic offline evidence below covers the omitted protocol behavior.

**Deterministic offline example**

```text
assistant messages appended for the round: 1
tool messages appended: 2
call_1 -> {"ok": true, "city": "Beijing", "condition": "sunny", "temperature_c": 24, "source": "demo data"}
call_2 -> {"ok": true, "city": "Shenzhen", "condition": "rainy", "temperature_c": 29, "source": "demo data"}
tool_call_id order: call_1, call_2
final assistant content: Done.
```

The multi-call fixture verifies assistant/tool history and `tool_call_id` propagation. A separate deterministic loop-limit fixture verifies the `max_rounds=4` bound.

## Limitations

- Weather values, including the live run's final wording, are consistent with `DEMO_WEATHER` and must not be treated as current conditions.
- Only `get_weather` is allowed; unknown names return `unknown_tool`.
- The loop does not use `eval`; arguments must be a JSON string decoding to an object.
- A tool error is sent back to the model as a tool result so the model can recover, but recovery is not guaranteed.
- `max_rounds=4` bounds repeated tool calls. Adjusting it changes the safety envelope.
- Production tools need authentication, authorization, timeouts, auditing, and domain-specific validation beyond this example.
