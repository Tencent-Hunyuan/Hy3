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
"""Hy3 Example 02: Streaming request + per-chunk parsing.

Demonstrates streaming mode via the OpenAI-compatible API, printing tokens
incrementally and assembling the full text at the end.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import (  # noqa: E402
    chat_completion,
    get_config,
    iter_stream_text,
    make_client,
)


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

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
    stream = chat_completion(client, messages, reasoning="no_think", stream=True)

    full_text_parts = []
    for content in iter_stream_text(stream):
        print(content, end="", flush=True)
        full_text_parts.append(content)

    print("\n\n=== Stream ended, assembling full text ===")
    full_text = "".join(full_text_parts)
    print(full_text)


if __name__ == "__main__":
    main()
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
> Verified live on **Tencent Cloud TokenHub** (`https://tokenhub.tencentmaas.com/v1`, `model=hy3`) on **2026-07-18**. Output is model-generated and may vary; secrets redacted.

```text
=== Streaming Output (per-chunk print) ===
秋天的银杏宛若披上金裳的舞者，在微凉的风里洒落一地温柔的时光。

=== Stream ended ===
TTFT ≈ 0.005 s · total ≈ 0.453 s
```
