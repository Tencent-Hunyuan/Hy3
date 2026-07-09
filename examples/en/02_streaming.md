# 02 Streaming Output Example

## Introduction

This example demonstrates how to call Hy3 in **streaming mode** via the OpenAI-compatible API.

A streaming call immediately returns an iterator when you pass `stream=True` to `client.chat.completions.create(...)`. The model pushes a `chunk` for every token (or small text segment) it generates, so the client can receive and print output **incrementally**, achieving a typewriter-style real-time display and significantly reducing the perceived time to first character.

Suitable scenarios: chat assistants, interactive Q&A, real-time content generation — any experience that benefits from displaying output as it is produced.

---

## Complete Request

> Before running, deploy the Hy3 service via vLLM / SGLang (listens on `127.0.0.1:8000` by default).
> Connection info can be overridden via the environment variables `HY3_BASE_URL` and `HY3_API_KEY`.

```python
"""
Hy3 Streaming Output Example (examples/02_streaming.py)

Demonstrates how to call Hy3 in streaming mode via the OpenAI-compatible API,
receiving incremental output token by token and finally assembling the full text.

Before running, deploy the Hy3 service via vLLM / SGLang (listens on 127.0.0.1:8000 by default).
Connection info can be overridden via environment variables:
    HY3_BASE_URL  service address (default http://127.0.0.1:8000/v1)
    HY3_API_KEY   API key (any value works for local deployment, default EMPTY)
"""

import os

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

# A prompt that elicits a multi-sentence answer
messages = [
    {
        "role": "user",
        "content": (
            "请用中文写一段关于「秋天的银杏林」的短文，"
            "包含颜色、声音和心情的描写，至少三句话。"
        ),
    },
]

print("=== Streaming Output (per-chunk print) ===")
stream = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    stream=True,
)

full_text_parts = []
for chunk in stream:
    # Each chunk in the stream is a ChatCompletionChunk
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    content = delta.content
    if content:  # skip None / empty string
        # Print incremental content in real time (no newline, typewriter effect)
        print(content, end="", flush=True)
        full_text_parts.append(content)

print("\n\n=== Stream ended, assembling full text ===")
full_text = "".join(full_text_parts)
print(full_text)
```

---

## Complete Response Parsing

When `stream=True`, `client.chat.completions.create(...)` no longer returns a single `ChatCompletion` object; instead it returns an **iterable** stream that yields a `ChatCompletionChunk` on each iteration.

### 1. Structure of a single chunk

Each `chunk` (`ChatCompletionChunk`) has roughly the following structure:

```python
ChatCompletionChunk(
    id="chatcmpl-xxx",
    choices=[
        Choice(
            index=0,
            delta=ChoiceDelta(
                role="assistant",   # usually only the first chunk carries role
                content="秋",        # incremental content of this chunk; may be None / ""
            ),
            finish_reason=None,      # only the last chunk is "stop"
        )
    ],
    usage=None,                      # by default usage is None in streaming
)
```

Key field notes:

- `chunk.choices`: usually has only one element (`index=0`). In some cases (e.g. when the server pushes usage) `choices` may be empty, so guard with `if not chunk.choices: continue` while iterating.
- `chunk.choices[0].delta`: the **incremental** delta of this chunk relative to the previous one.
  - `delta.content`: the incremental text. May be `None` or the empty string `""` before the model emits any token; check for emptiness before using it.
  - `delta.role`: the role info, usually present only in the **first** chunk (value `"assistant"`).
- `chunk.choices[0].finish_reason`: the stop reason. Middle chunks are all `None`; the **last** chunk is `"stop"` (normal end) or another stop marker.

### 2. How to accumulate the full text

Because each chunk only carries a delta, you need to concatenate them yourself:

```python
full_text_parts = []
for chunk in stream:
    if not chunk.choices:
        continue
    content = chunk.choices[0].delta.content
    if content:                          # skip None / ""
        print(content, end="", flush=True)  # real-time display
        full_text_parts.append(content)     # collect
full_text = "".join(full_text_parts)        # final assembly
```

- `list.append + "".join` is more efficient than repeated string `+=`.
- `print(content, end="", flush=True)` ensures the increment is flushed to the terminal immediately, producing the typewriter effect.

### 3. About usage

By default, `chunk.usage` in a streaming response is `None` (OpenAI-compatible services usually do not return usage stats within the stream). If you need token usage, pass the following in the request:

```python
stream_options={"include_usage": True}
```

When enabled, the server generally returns the total usage in the **last chunk** (the one with empty `choices` and a populated `usage`).

---

## Sample Output

> The following is **sample output** (representative text, not a real run result) to illustrate the print layout of a streaming call.

```
=== Streaming Output (per-chunk print) ===
秋天的银杏林是一幅金色的画卷。阳光透过层层叠叠的叶片洒落下来，把地面铺成一条柔软的金黄小径。微风拂过，叶子簌簌作响，像是在低声诉说季节的秘密。我站在林中，呼吸着微凉的空气，心底升起一种安静而满足的喜悦。

=== Stream ended, assembling full text ===
秋天的银杏林是一幅金色的画卷。阳光透过层层叠叠的叶片洒落下来，把地面铺成一条柔软的金黄小径。微风拂过，叶子簌簌作响，像是在低声诉说季节的秘密。我站在林中，呼吸着微凉的空气，心底升起一种安静而满足的喜悦。
```

At runtime, the first paragraph is printed incrementally to the terminal — character by character / word by word (typewriter effect) — and after the stream ends the assembled full text is printed once more.
