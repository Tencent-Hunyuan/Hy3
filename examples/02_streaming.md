# 02 Streaming Chat Completion

This example shows how to call Hy3 with streaming enabled. Streaming returns the assistant response incrementally as chunks, which is useful for command-line demos and chat UIs.

Script: [02_streaming.py](02_streaming.py)

## Complete Request

Set `stream=True` in `client.chat.completions.create(...)`:

```python
stream = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content": "Write a short checklist for testing a REST API."}
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
    stream=True,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

## Complete Response Parsing

A streaming response is an iterator. Each item is a chunk that may contain a new text delta:

```text
chunk
└── choices[0]
    └── delta
        └── content = current new text fragment
```

The script prints each non-empty `delta.content` immediately:

```python
for chunk in stream:
    if not chunk.choices:
        continue

    delta = chunk.choices[0].delta
    if delta and delta.content:
        print(delta.content, end="", flush=True)
```

This is different from non-streaming parsing, where the final answer is read from `response.choices[0].message.content`.

## Run

```bash
python examples/02_streaming.py
```

## Example Output

```text
Assistant:1. Verify required endpoints and HTTP methods.
2. Test success and failure status codes.
3. Check authentication and authorization behavior.
4. Validate request and response schemas.
5. Add timeout and retry tests for transient failures.
```
