<p align="left">
  English&nbsp; | &nbsp;<a href="continue_CN.md">中文</a>
</p>

# Use Hy3 in Continue

## Overview

Continue can use its OpenAI provider with a custom `apiBase`. This flow was validated with the latest Continue release available on July 12, 2026.

## Configuration

Store the TokenHub Key as a Continue secret named `HY3_API_KEY`, then add this model to `config.yaml`:

```yaml
name: Hy3 Config
version: 0.0.1
schema: v1

models:
  - name: Hy3
    provider: openai
    model: hy3
    apiBase: https://tokenhub.tencentmaas.com/v1
    apiKey: ${{ secrets.HY3_API_KEY }}
    roles:
      - chat
      - edit
      - apply
```

![Continue configuration](assets/continue-01-config.png)

## Connection check

```text
Reply with exactly: Hy3 connection verified
```

![Continue first conversation](assets/continue-02-first-chat.png)

## Read-only repository task

Add only the intended files as context and use this exact prompt:

```text
Based only on the read-only files provided, summarize this application's
architecture, identify three concrete risks with file references, and propose
a three-step improvement plan. Do not modify files and do not run Git commands.
```

![Continue real read-only task](assets/continue-03-real-task.gif)

## Troubleshooting

- If the model is absent, reload Continue after saving `config.yaml`.
- Confirm the secret name matches `HY3_API_KEY` exactly.
- Keep the Base URL at the `/v1` root; do not append `/chat/completions`.

## References

- [Tencent TokenHub](https://cloud.tencent.com/product/tokenhub)
- [Continue OpenAI provider](https://docs.continue.dev/customize/model-providers/top-level/openai)
