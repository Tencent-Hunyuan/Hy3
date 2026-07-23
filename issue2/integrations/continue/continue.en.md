# Use Hy3 with Continue

> 中文：[continue.md](continue.md) · [Back to index](../README.en.md)

Continue ships VS Code/JetBrains extensions and the `cn` CLI. Current releases use `config.yaml`; legacy `config.json` is deprecated.

## Install

Install **Continue - open-source AI code agent** by `Continue`, or the official `cn` CLI. Prefer the current stable release. The YAML below was checked against the official [OpenAI provider](https://docs.continue.dev/customize/model-providers/top-level/openai) and [config reference](https://docs.continue.dev/reference) on 2026-07-23.

## Configure

Save as `~/.continue/config.yaml` and keep the key in an environment secret:

```yaml
name: Hy3 Agent
version: 1.0.0
schema: v1

models:
  - name: Hy3 via OpenRouter
    provider: openai
    model: tencent/hy3
    apiBase: https://openrouter.ai/api/v1
    apiKey: ${{ secrets.OPENROUTER_API_KEY }}
    capabilities:
      - tool_use
    roles:
      - chat
      - edit
      - apply
    defaultCompletionOptions:
      temperature: 0.9
      maxTokens: 4096
```

For self-hosting, use `http://127.0.0.1:8000/v1`, model `hy3`, and the gateway's key policy. Explicit `tool_use` enables Agent tools for a new custom model.

## First conversation

Reload the config, select **Hy3 via OpenRouter**, and ask Chat mode to summarize only the open README with the exact file path and no edits. Verify the model ID in logs and an unchanged worktree.

## End-to-end task

In Agent mode, ask Continue to modify only `issue2/demo/`, return HTTP 415 for non-JSON research requests, add an HTTP test, run the full suite, and avoid dependencies and commits. Review each Apply diff and rerun tests independently.

![Evidence Board offline screenshot](../../assets/evidence-board-offline.png)

## Troubleshooting

| Symptom | Fix |
|:---|:---|
| YAML ignored | Validate `name/version/schema`, reload, and inspect Continue logs |
| Agent unavailable | Add `capabilities: [tool_use]` and verify endpoint tools support |
| `/responses` fails | Add `useResponsesApi: false` to force Chat Completions |
| Secret empty | Export before launching VS Code and fully restart it |
| Unrelated Apply edits | Constrain paths in the prompt/rules and inspect the diff |
