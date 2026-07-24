# 03 Streaming versus non-streaming

Compare first-chunk latency and total response time.

```bash
uv run --env-file .env python examples/03_streaming_vs_non_streaming.py
```

The same prompt is sent with `stream: false` and `stream: true`. The script reads the complete response in the first case and concatenates `delta.content` in the second case. Timing depends on network conditions, service load, and output length.

## Output example

```text
non-streaming total: 2.351s
streaming first chunk: 0.830s
streaming total: 1.859s
streaming text: 深圳是中国南方毗邻香港的经济特区和超大城市……
non-streaming text: 深圳是中国南部海滨的现代化大都市……
```

The Chinese text describes Shenzhen as a modern city and technology center. Timing and wording are samples from one run, not fixed guarantees.
