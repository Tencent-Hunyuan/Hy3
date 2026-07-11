# 01 Basic chat

[简体中文](01_basic_chat_CN.md) · [Index](README.md) · [Script](01_basic_chat.py)

## Purpose

Learn the smallest complete chat flow: build one request, normalize the response, append the assistant content to history, and send a second user turn. The script is [`01_basic_chat.py`](01_basic_chat.py).

## Configuration

Configure `examples/api/.env` as described in the [API index](README.md). The script uses `Hy3Config.from_env()`, creates one client, and applies backend-specific `no_think` mapping through `reasoning_extra_body`.

## Complete request

The first request contains every field passed to the SDK:

```python
{
    "model": config.model,
    "messages": [
        {"role": "user", "content": "Hello! Briefly introduce yourself."}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512,
    "extra_body": reasoning_extra_body(config, "no_think"),
}
```

After the first completion is summarized, the second request keeps the same model and sampling fields and sends this complete history:

```python
[
    {"role": "user", "content": "Hello! Briefly introduce yourself."},
    {"role": "assistant", "content": first["content"]},
    {
        "role": "user",
        "content": "What kinds of tasks can you help me with?",
    },
]
```

`build_request` copies every message dict, so preparing a request does not mutate the caller's message objects.

## Response parsing

`summarize_completion` reads only the first choice and returns:

- `model` and assistant `content`;
- normalized `reasoning` plus `reasoning_details`;
- `finish_reason`;
- a plain-dict `usage` value, or `None` when unavailable.

The second history entry intentionally stores assistant content only. For histories that must preserve structured reasoning or tool calls, use `assistant_message_to_dict` as demonstrated by the [tool-calling guide](04_tool_calling.md).

## Run

From the repository root:

```bash
python examples/api/01_basic_chat.py
```

This command uses the configured API. The observation below was captured from a live run; wording and token usage can vary between runs.

## Example output

**Verified live evidence summary (sanitized; not literal stdout)**

The script's actual CLI output also prints the request and response JSON with fixed English labels. This list is a reviewed summary, not a transcript:

- Backend: OpenRouter
- Model requested: `tencent/hy3:free`
- Model resolved: `tencent/hy3-20260706:free`
- Observed on: 2026-07-11
- Single-turn content: a brief self-introduction
- Single-turn reasoning: unavailable
- Single-turn `usage.total_tokens`: 71
- Multi-turn content: a list of task types the assistant can help with
- Multi-turn `usage.total_tokens`: 226

**Deterministic offline example**

```text
Single-turn response:
content: I am Hy3.
reasoning: brief plan
finish_reason: stop
usage.total_tokens: 5

Multi-turn response:
content: I can help with APIs.
reasoning: ""
finish_reason: stop
usage.total_tokens: 5
```

## Limitations

- The live content descriptions are safe summaries, not exact-output assertions. The deterministic text is fake test data; live wording and token usage vary.
- The example assumes the completion contains at least one choice. The shared normalizer raises when choices are missing.
- It does not stream, execute tools, or preserve reasoning fields in the second-turn assistant history.
- The script creates a client for a short-lived CLI and relies on process exit for cleanup.
