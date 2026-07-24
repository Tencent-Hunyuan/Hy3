# 07 Responses API streaming

Read Responses API SSE events and print text deltas.

```bash
uv run --env-file .env python examples/07_responses_streaming.py
```

The script handles `response.output_text.delta`, `response.completed`, and `response.failed`. It parses raw SSE with the Python standard library because the current TokenHub `response.created` event may contain `output: null`, which can break high-level Responses stream parsers in some OpenAI SDK versions.

## Output example

```text
深圳是中国南部滨海的现代化大都市，也是粤港澳大湾区的核心引擎之一……

usage: {'input_tokens': 21, 'output_tokens': 58, 'total_tokens': 79}
```

English translation: “Shenzhen is a modern coastal metropolis in southern China and one of the core engines of the Guangdong-Hong Kong-Macao Greater Bay Area.”
