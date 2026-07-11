# Streaming Chat

This example demonstrates how to call the Hy3 OpenAI-compatible API with streaming enabled and how to parse response chunks incrementally.

It covers:

* enabling streaming with `stream=True`
* iterating over response chunks
* inspecting complete chunk objects
* parsing `delta.content`
* detecting the finish reason
* rebuilding the complete assistant response

## Prerequisites

Before running this example, make sure you have:

* Python 3.10 or later
* the `openai` Python package installed
* access to a Hy3 OpenAI-compatible endpoint

The example reads:

```text
HY3_BASE_URL
HY3_API_KEY
HY3_MODEL
```

If these variables are not set, it uses:

```text
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
```

## Run the example

From the repository root:

```bash
python examples/api/02_streaming.py
```

## Complete request

Streaming is enabled by setting:

```python
"stream": True
```

The complete request payload is:

```python
request_payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": (
                "Explain what an API is in about "
                "three short sentences."
            ),
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "stream": True,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think"
        }
    },
}

stream = client.chat.completions.create(
    **request_payload
)
```

Unlike a non-streaming request, the returned object is consumed incrementally.

## Chunk parsing

The example iterates over every received chunk:

```python
for chunk in stream:
    chunk_count += 1
```

Each complete chunk object is printed:

```python
print(chunk.model_dump_json(indent=2))
```

Some OpenAI-compatible endpoints may emit chunks without choices, so the example checks before accessing the first choice:

```python
if not chunk.choices:
    continue
```

The first choice contains a delta object:

```python
choice = chunk.choices[0]
delta = choice.delta
```

When text content is present, the new text fragment is appended to a list:

```python
if delta.content is not None:
    text_parts.append(delta.content)
```

The example also prints the parsed fragment:

```python
print(
    "Parsed delta.content: "
    f"{delta.content!r}"
)
```

Using `!r` makes spaces, line breaks, and other special characters easier to inspect.

## Finish reason

The final chunk may contain a finish reason:

```python
if choice.finish_reason is not None:
    finish_reason = choice.finish_reason
```

A normal completion commonly ends with:

```text
stop
```

## Rebuilding the complete response

Streaming responses arrive as separate text fragments.

For example:

```text
'An'
' API'
' is'
' a'
```

The example stores these fragments and joins them after the stream finishes:

```python
full_text = "".join(text_parts)
```

The reconstructed result is then printed:

```python
print(f"Full content: {full_text}")
```

## Example output

The exact number of chunks and generated text may vary between runs.

Example from a Hy3 API request:

```text
=== Final parsed result ===
Chunks received: 32
Finish reason: stop
Full content: An API (Application Programming Interface) is a set of rules that lets different software programs communicate with each other. It defines how requests are made and what data is returned, without exposing the internal code. APIs are commonly used to fetch information or trigger actions between apps and services.
```

## What this example demonstrates

This example shows that a streaming response is not a single complete message.

Instead, the client:

1. receives chunks incrementally
2. inspects each chunk
3. extracts `delta.content`
4. preserves every text fragment
5. detects the finish reason
6. reconstructs the full assistant response

Streaming is useful when applications want to display generated content before the complete response has finished.
