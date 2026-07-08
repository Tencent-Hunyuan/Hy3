<p align="left">
    <a href="./zh-cn/03_latency_compare.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>

# Example 03: Non-streaming vs streaming latency

This example compares total latency for a normal request with first-token and total latency for a streaming request.

> Related: [Examples Index](./README.md) | [API Quickstart](../quickstart.md)

## Run

```bash
python examples/03_latency_compare.py
```

## Full request

Non-streaming:

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "请写一段约 300 字的说明..."}],
    temperature=0.7,
    top_p=1.0,
    max_tokens=700,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

Streaming:

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "请写一段约 300 字的说明..."}],
    temperature=0.7,
    top_p=1.0,
    max_tokens=700,
    stream=True,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

## Response parsing

```python
text = response.choices[0].message.content

first_token_time = None
for chunk in stream:
    content = getattr(chunk.choices[0].delta, "content", None)
    if content and first_token_time is None:
        first_token_time = time.perf_counter() - start
```

## Sample output

```text
=== latency comparison ===
non_stream_total_s: 8.214
stream_first_token_s: 0.732
stream_total_s: 8.046
non_stream_chars: 348
stream_chars: 352
```

Interpretation: streaming usually does not reduce total generation time, but it can reduce perceived latency because users see the first token earlier.
