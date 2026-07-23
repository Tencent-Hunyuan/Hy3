# Example 2: Streaming

Stream responses token-by-token for real-time display, similar to ChatGPT's typing effect.

## What You'll Learn

- Enable streaming with `stream=True`
- Iterate over SSE chunks
- Distinguish `delta.content` from `delta.reasoning_content`
- Handle the `[DONE]` signal and final usage stats

---

## Streaming Request

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)

stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "Write a haiku about programming."},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    stream=True,  # ← Enable streaming
)
```

### Chunk-by-Chunk Parsing

```python
for chunk in stream:
    if not chunk.choices:
        continue

    delta = chunk.choices[0].delta

    # Regular content
    if delta.content:
        print(delta.content, end="", flush=True)

    # Finish reason (signals end of stream)
    if chunk.choices[0].finish_reason:
        print(f"\n\n[Finished: {chunk.choices[0].finish_reason}]")

    # Usage stats (sent in the final chunk)
    if hasattr(chunk, "usage") and chunk.usage:
        print(f"[Tokens: {chunk.usage.total_tokens}]")
```

### Raw Chunk Structure

Each chunk is a JSON object sent as an SSE event:

```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"hy3","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"hy3","choices":[{"index":0,"delta":{"content":"Bugs"},"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"hy3","choices":[{"index":0,"delta":{"content":" hide"},"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"hy3","choices":[{"index":0,"delta":{"content":" in"},"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"hy3","choices":[{"index":0,"delta":{"content":" light"},"finish_reason":null}]}

...

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"hy3","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":14,"completion_tokens":18,"total_tokens":32}}

data: [DONE]
```

### Sample Output

```
Bugs hide in the code,
Compile errors light the screen—
Debugger drinks coffee.

[Finished: stop]
[Tokens: 32]
```

---

## Streaming with Reasoning Content

When `reasoning_effort="high"` is enabled, the stream includes both thinking tokens and final output:

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "What is 15 * 37?"}],
    stream=True,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)

thinking = []
answer = []

for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta

    # Thinking tokens (model's internal reasoning)
    if getattr(delta, "reasoning_content", None):
        thinking.append(delta.reasoning_content)
        print(f"\x1b[90m{delta.reasoning_content}\x1b[0m", end="", flush=True)

    # Final answer tokens
    if delta.content:
        answer.append(delta.content)
        print(delta.content, end="", flush=True)

print(f"\n\nThinking tokens: {len(''.join(thinking).split())}")
print(f"Answer tokens:   {len(''.join(answer).split())}")
```

### Sample Output (Reasoning Mode)

```
Let me break this down:
15 * 37 = 15 * (40 - 3) = 15*40 - 15*3 = 600 - 45 = 555
So 15 * 37 = 555.

Thinking tokens: 32
Answer tokens: 11
```

> 💡 **Tip**: In UI applications, show `reasoning_content` in a collapsed "thinking" panel and `content` as the main output.

---

## Collecting Full Response from Stream

If you need the complete text (e.g., for logging or downstream processing):

```python
def stream_and_collect(client, messages, **kwargs):
    """Stream the response and return the full text + usage stats."""
    stream = client.chat.completions.create(
        model="hy3",
        messages=messages,
        stream=True,
        **kwargs,
    )

    content_parts = []
    reasoning_parts = []
    finish_reason = None
    usage = None

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        if getattr(delta, "reasoning_content", None):
            reasoning_parts.append(delta.reasoning_content)

        if delta.content:
            content_parts.append(delta.content)
            print(delta.content, end="", flush=True)

        if chunk.choices[0].finish_reason:
            finish_reason = chunk.choices[0].finish_reason

        if hasattr(chunk, "usage") and chunk.usage:
            usage = chunk.usage

    return {
        "content": "".join(content_parts),
        "reasoning": "".join(reasoning_parts),
        "finish_reason": finish_reason,
        "usage": usage,
    }
```

---

## Key Takeaways

1. **Set `stream=True`** in `client.chat.completions.create()`.
2. **Iterate over chunks** — each chunk contains a `delta` with partial content.
3. **The first chunk** carries `delta.role: "assistant"` with no content.
4. **The last meaningful chunk** contains `finish_reason` and `usage`.
5. **`[DONE]`** signals the stream end; the OpenAI SDK handles this automatically.
6. **Reasoning content** arrives in `delta.reasoning_content` before `delta.content`.

---

## Run the Script

```bash
pip install openai
python 02-streaming.py
```
