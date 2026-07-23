# 03 — Non-streaming versus streaming latency

This example measures user-observable latency. It is an integration comparison,
not a model-only benchmark: network, queueing, client work, and server generation
are all included.

## Run

```bash
HY3_BENCH_RUNS=3 python examples/api/03_latency_comparison.py
```

Each run sends the same prompt twice: once non-streaming and once streaming.
Use a low run count on a metered endpoint.

## Complete requests

```python
request = {
    "model": config.model,
    "messages": [
        {
            "role": "user",
            "content": "Explain idempotency in HTTP APIs in about 120 words.",
        }
    ],
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 256,
    "extra_body": {
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
}

started = time.perf_counter()
response = client.chat.completions.create(**request, stream=False)
non_stream_total = time.perf_counter() - started

started = time.perf_counter()
chunks = client.chat.completions.create(**request, stream=True)
first_token = None
for _, answer_delta in stream_fragments(chunks):
    if answer_delta and first_token is None:
        first_token = time.perf_counter() - started
stream_total = time.perf_counter() - started
```

## Complete response parsing

The non-streaming call is complete when `create` returns. The streaming call is
complete only after consuming its iterator. Store one total per mode and the
first non-empty answer delta for TTFT, then compute arithmetic means:

```python
non_stream_average = statistics.fmean(item.total for item in non_stream_results)
stream_ttft_average = statistics.fmean(
    item.first_token for item in stream_results if item.first_token is not None
)
stream_total_average = statistics.fmean(item.total for item in stream_results)
```

## Example output

Illustrative format only:

```text
Target: base_url=<redacted-host> model=hy3 timeout=120s; runs per mode=3
Run 1: non-stream total=<seconds>s; stream TTFT=<seconds>s, total=<seconds>s
Run 2: non-stream total=<seconds>s; stream TTFT=<seconds>s, total=<seconds>s
Run 3: non-stream total=<seconds>s; stream TTFT=<seconds>s, total=<seconds>s

Averages
Non-stream total: <seconds>s
Stream TTFT: <seconds>s
Stream total: <seconds>s
```

## Interpretation

- Streaming normally improves time to visible output, not necessarily total time.
- A single run is easily distorted by cold starts and queueing.
- Keep prompt, sampling, output cap, endpoint, and reasoning mode identical.
- Record date, hardware or provider, and run count with any published result.
