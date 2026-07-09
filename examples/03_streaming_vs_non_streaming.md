# 03 Streaming vs Non-Streaming

This example compares non-streaming and streaming chat completions. Non-streaming waits until the full answer is ready. Streaming can expose the first token earlier while generation continues.

Script: [03_streaming_vs_non_streaming.py](03_streaming_vs_non_streaming.py)

## Complete Request

Both requests use the same prompt:

```python
messages = [{"role": "user", "content": "Explain API retries in about 120 words."}]
```

Non-streaming request:

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    max_tokens=256,
)
```

Streaming request:

```python
stream = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    max_tokens=256,
    stream=True,
)
```

## Complete Response Parsing

The non-streaming response contains the final answer at:

```python
non_stream_text = response.choices[0].message.content
```

The streaming response is parsed chunk by chunk. The first non-empty `delta.content` marks first-token latency:

```python
for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    if delta and delta.content:
        if first_token_time is None:
            first_token_time = time.perf_counter() - start
        text.append(delta.content)

stream_text = "".join(text)
```

The script parses both final texts and prints timing metrics plus answer lengths so the latency comparison is easy to read.

## Run

```bash
python examples/03_streaming_vs_non_streaming.py
```

## Example Output

```text
Non-streaming total: 3.842s
Streaming first token: 0.418s
Streaming total: 3.615s
Non-streaming answer length: 694 chars
Streaming answer length: 681 chars
```

Exact numbers depend on your server, GPU load, model length, and network latency.
