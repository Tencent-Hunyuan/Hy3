# 02 Streaming

Read Chat Completions chunks incrementally and print the final usage.

```bash
uv run --env-file .env python examples/02_streaming.py
```

The script checks `chunk.choices` before reading `delta.content`. With `stream_options.include_usage: true`, the final usage chunk may have an empty `choices` array.

## Output example

Observed output from one run:

```text
深圳是中国南部海滨的现代化大都市，也是改革开放后迅速崛起的经济特区和创新之都。

usage: CompletionUsage(completion_tokens=62, prompt_tokens=21, total_tokens=83, ...)
```

English translation: “Shenzhen is a modern coastal metropolis in southern China, a special economic zone, and a center of innovation.” The usage details depend on the response.
