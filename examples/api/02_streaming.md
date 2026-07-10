# 02 Streaming

[简体中文](02_streaming_CN.md) · [Index](README.md) · [Script](02_streaming.py)

## Purpose

Consume a streaming completion without assuming every chunk contains text. [`02_streaming.py`](02_streaming.py) prints content as it arrives while retaining reasoning, usage, finish reason, and fragmented tool calls in a final snapshot.

## Configuration

Configure a backend through `examples/api/.env`. The request uses backend-specific `no_think` mapping and asks the backend to include usage in the stream. Not every compatible server returns every optional field.

## Complete request

`build_request` returns the exact SDK arguments:

```python
{
    "model": config.model,
    "messages": [
        {
            "role": "user",
            "content": "Explain what an API is in two sentences.",
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512,
    "stream": True,
    "stream_options": {"include_usage": True},
    "extra_body": reasoning_extra_body(config, "no_think"),
}
```

## Response parsing

For each chunk, `StreamAccumulator.add_chunk` performs these steps:

1. Normalize and save a truthy `usage` object before inspecting choices. This supports a terminal usage-only chunk.
2. Return an empty update when `choices=[]`; empty-choice chunks are legal.
3. Read only the first choice, save a non-null finish reason, and extract content separately from reasoning.
4. Append non-empty content/reasoning fragments and extend structured reasoning details.
5. Reassemble tool-call `id`, `function.name`, and `function.arguments` by integer `index`. Fragments may arrive interleaved; the result sorts calls by index.

`consume_stream` prints only `update.content`. Reasoning never appears on the live `Content:` line. `result()` returns independent copies of nested usage, reasoning details, and tool calls.

## Run

From the repository root:

```bash
python examples/api/02_streaming.py
```

The command uses the configured API. The following values come from deterministic accumulator fixtures.

## Example output

**Deterministic offline example**

```text
content: Hello world
reasoning: plan carefully
finish_reason: tool_calls
usage.total_tokens: 12
tool_calls[0]: call_weather / get_weather / {"city":"Shenzhen"}
tool_calls[1]: call_time / get_time / {"timezone":"Asia/Hong_Kong"}
```

The fixture deliberately sends an initial empty chunk, interleaves call index 1 before index 0 in a later chunk, and finishes with a usage-only chunk.

## Limitations

- The output above is synthetic test data, not a live model response.
- `stream_options.include_usage` requests usage but cannot force an unsupported backend to provide it.
- The accumulator reads the first choice only.
- The script prints content live but waits until the stream ends to print reasoning, usage, and reconstructed tool calls.
- Network interruption before the terminal chunk may leave finish reason or usage unavailable.
