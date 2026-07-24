# 05 Reasoning mode

Compare normal and reasoning requests with Chat Completions.

```bash
uv run --env-file .env python examples/05_reasoning_mode.py
```

The script sends the same question twice and prints both final answers and the reasoning request's usage. Supported fields and values depend on the model and TokenHub service. Applications should not display private chain-of-thought content.

## Output example

```text
Normal mode:
37 × 24 = 888

Reasoning mode:
37 × 24 = 888

Reasoning usage:
CompletionUsage(... reasoning_tokens=232 ...)
```

The actual run returned Chinese explanations for the calculation. The important comparison is the final answer and the reasoning-token usage; private reasoning content should not be displayed by applications.
