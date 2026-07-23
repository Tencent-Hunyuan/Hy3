# 02 — Streaming and incremental parsing

Streaming improves perceived latency by exposing deltas as the server generates
them. It also changes response handling: each event is partial and some terminal
chunks contain usage metadata but no choices.

## Run

```bash
python examples/api/02_streaming.py
```

## Complete request

```python
request = {
    "model": config.model,
    "messages": [
        {
            "role": "user",
            "content": "Write a four-line checklist for reviewing an API integration.",
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512,
    "stream": True,
    "extra_body": {
        "chat_template_kwargs": {"reasoning_effort": "low"}
    },
}
chunks = client.chat.completions.create(**request)
```

## Complete response parsing

The shared iterator normalizes SDK models and dictionary-shaped test fixtures,
skips empty `choices`, and keeps reasoning separate from final content:

```python
answer_parts = []
reasoning_parts = []

for chunk in chunks:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    reasoning_delta = getattr(delta, "reasoning_content", "") or ""
    answer_delta = delta.content or ""
    if reasoning_delta:
        reasoning_parts.append(reasoning_delta)
    if answer_delta:
        answer_parts.append(answer_delta)
        print(answer_delta, end="", flush=True)

answer = "".join(answer_parts)
reasoning = "".join(reasoning_parts)
```

Time to first answer token (TTFT) is measured when the first non-empty
`content` delta arrives, not when a role-only or reasoning-only chunk arrives.

## Example output

Illustrative format, not a live benchmark:

```text
Assistant: 1. Verify authentication and configuration.
2. Validate success and error response schemas.
3. Test timeouts, retries, and rate limits.
4. Remove secrets from logs and fixtures.
Time to first answer token: <seconds>s
Total stream time: <seconds>s
Answer characters: <count>
Reasoning characters: <count>
```

## Checks

- Do not assume every chunk has a choice or text.
- Flush each printed delta so the terminal visibly streams.
- Buffer the full answer if downstream code needs a complete string.
- Keep TTFT and total-time start points consistent across measurements.
