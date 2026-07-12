<p align="left">
  English&nbsp; | &nbsp;<a href="codex-cli_CN.md">中文</a>
</p>

# Use Hy3 in Codex CLI

## Overview

Tencent TokenHub exposes a Responses API endpoint compatible with current Codex CLI custom providers. This flow was validated on July 12, 2026 with Codex CLI `0.144.1` and model ID `hy3`.

## Configuration

Add this configuration to the user-level `~/.codex/config.toml`:

```toml
model_provider = "hy3-tokenhub"
model = "hy3"
disable_response_storage = true

[model_providers.hy3-tokenhub]
name = "Hy3 via TokenHub"
base_url = "https://tokenhub.tencentmaas.com/v1"
env_key = "HY3_API_KEY"
wire_api = "responses"
```

Set the Key in the current PowerShell session, then launch Codex from the repository root:

```powershell
$env:HY3_API_KEY = "<TENCENT_TOKENHUB_API_KEY>"
codex
```

![Codex CLI configuration](assets/codex-cli-01-config.png)

## Connection check

```text
Reply with exactly: Hy3 connection verified
```

![Codex CLI first conversation](assets/codex-cli-02-first-chat.png)

Codex CLI may warn that built-in metadata for `hy3` is unavailable and use fallback metadata. The validated conversation still completes, but model-specific context and reasoning defaults may require explicit configuration in future releases.

## Read-only repository task

Attach only the intended read-only files and use this exact prompt:

```text
Based only on the read-only files provided, summarize this application's
architecture, identify three concrete risks with file references, and propose
a three-step improvement plan. Do not modify files and do not run Git commands.
```

![Codex CLI real read-only task](assets/codex-cli-03-real-task.gif)

## Troubleshooting

- Current Codex CLI custom providers require `wire_api = "responses"`; do not set Chat Completions mode.
- Confirm `HY3_API_KEY` is available to the process that launches Codex.
- Fully restart Codex after changing `config.toml` or the environment variable.

## References

- [Tencent TokenHub: use Hy3 in Codex](https://cloud.tencent.com/document/product/1823/133532)
- [OpenAI Codex configuration reference](https://developers.openai.com/codex/config-reference/)
