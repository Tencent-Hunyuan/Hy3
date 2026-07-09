# Use Hy3 with Codex CLI

## Overview

This guide shows how to configure OpenAI Codex CLI to use Hy3 through a custom OpenAI-compatible provider profile.

Verification status: Codex CLI with Hy3 through Tencent Cloud TokenHub mode was manually verified with screenshots.

## Prerequisites

- OpenAI Codex CLI version: `0.142.5`.
- Observed command paths:
  - `%APPDATA%\npm\codex`
  - `%APPDATA%\npm\codex.cmd`
- Choose one Hy3 setup mode:
  - TokenHub cloud API mode: manually verified.
  - Local self-hosted mode: Not verified in this PR.

## Option A: TokenHub Cloud API Mode

Use TokenHub when you want to call Hy3 through Tencent Cloud TokenHub without self-hosting.

See [tokenhub.md](tokenhub.md) for shared setup and safety notes.

The basic TokenHub Hy3 Chat Completions API smoke test is verified in [tokenhub.md](tokenhub.md). Codex CLI through TokenHub was also manually verified.

| Setting | Value |
|:---|:---|
| Codex profile | `hy3-tokenhub` |
| User-level profile path | `%USERPROFILE%\.codex\hy3-tokenhub.config.toml` |
| Model provider name | `tokenhub` |
| Codex model | `hy3` |
| TokenHub model | `hy3` |
| TokenHub base URL | `https://tokenhub.tencentmaas.com/v1` |
| TokenHub chat completions endpoint | `https://tokenhub.tencentmaas.com/v1/chat/completions` |
| API key environment variable | `TOKENHUB_API_KEY` |
| API key | User-created TokenHub API key, not committed and not documented |
| Protocol | OpenAI-compatible model provider through Codex CLI custom provider profile |

If the TokenHub API key access scope is limited, Hy3 must be included in that scope.

## Option B: Local Self-hosted Mode

Use local self-hosted mode when Hy3 is running as a local OpenAI-compatible chat completions server.

See [local-server.md](local-server.md) for the repository-documented vLLM and SGLang serving examples.

| Setting | Value |
|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` |
| Model | `hy3` |
| API key for local testing | `EMPTY` |
| API protocol | OpenAI-compatible chat completions |

For TokenHub cloud API mode, no local Hy3 server is required.

For local self-hosted mode, follow [local-server.md](local-server.md).

Codex CLI connectivity with TokenHub mode was manually verified. Local self-hosted connectivity was not verified in this PR.

## Configure the Tool

Codex CLI was configured with a user-level profile:

```text
%USERPROFILE%\.codex\hy3-tokenhub.config.toml
```

Do not commit `%USERPROFILE%\.codex\hy3-tokenhub.config.toml`, Codex auth files, or TokenHub API keys.

Verified profile shape:

```toml
model = "hy3"
model_provider = "tokenhub"

[model_providers.tokenhub]
name = "Tencent Cloud TokenHub"
base_url = "https://tokenhub.tencentmaas.com/v1"
env_key = "TOKENHUB_API_KEY"
```

Set the TokenHub API key in the current shell through `TOKENHUB_API_KEY`. Do not write the key into the profile file.

Verified modes:

- Interactive TUI mode first chat.
- Interactive TUI mode README summary task.
- Non-interactive exec mode first chat.
- Non-interactive exec mode README summary task.

## First Chat

Prompt:

```text
Hello Hy3. Please introduce yourself in two sentences. Do not inspect the repository or modify any files.
```

Interactive result: Codex CLI selected model `hy3` with provider `tokenhub` and returned a Hy3 response.

Exec command:

```powershell
codex --profile hy3-tokenhub exec "Hello Hy3. Please introduce yourself in two sentences. Do not inspect the repository or modify any files." 2> "$env:TEMP\codex-hy3-stderr.log"
```

Exec result: returned a concise Hy3 response.

## Real Task Demo

Interactive README task prompt:

```text
Please read README.md only. Do not print the full file contents. Summarize what Hy3 is in three bullet points based on the Model Introduction section. Do not edit, create, delete, or modify any files.
```

Interactive result: Codex CLI ran `Get-Content README.md` and returned a three-bullet summary based on the Model Introduction section.

Exec README task command:

```powershell
codex --profile hy3-tokenhub exec "Please inspect README.md, but keep the terminal output concise: read only the Model Introduction section or at most the first 80 lines, then summarize what Hy3 is in three bullet points. Do not print the entire README. Do not edit, create, delete, or modify any files." 2> "$env:TEMP\codex-hy3-stderr.log"
```

Exec result: returned a concise three-bullet summary.

No repository files were intentionally edited.

## Screenshots / GIFs

- Interactive first chat screenshot:

![Codex CLI interactive first chat with Hy3 through TokenHub](assets/codex-cli/codex-cli-interactive-first-chat-tokenhub.png)

- Interactive README demo screenshot:

![Codex CLI interactive README demo with Hy3 through TokenHub](assets/codex-cli/codex-cli-interactive-readme-demo-tokenhub.png)

- Exec first chat screenshot:

![Codex CLI exec first chat with Hy3 through TokenHub](assets/codex-cli/codex-cli-exec-first-chat-tokenhub.png)

- Exec README demo screenshot:

![Codex CLI exec README demo with Hy3 through TokenHub](assets/codex-cli/codex-cli-exec-readme-demo-tokenhub.png)

Screenshots are included under `docs/integrations/assets/codex-cli/`. GIFs are optional and were not added.

Screenshots and GIFs must not reveal API keys.

## Troubleshooting

- Codex may warn:

```text
Model metadata for `hy3` not found. Defaulting to fallback metadata.
```
- Some raw runs may print model-manager or stream-delta warnings, such as model list parsing warnings or `OutputTextDelta without active item`.
- Redirecting stderr to a temporary log can keep exec screenshots focused on the successful model response.
- A TokenHub `429 Too Many Requests` error may appear after repeated Codex runs; wait before retrying.
- Do not commit `%USERPROFILE%\.codex\hy3-tokenhub.config.toml` or any Codex auth files.
- Do not include or commit the TokenHub API key.
- TokenHub API key access scope for Hy3: Future verification item.
- Local endpoint connection issue: Not verified in this PR.
- Local self-hosted authentication or API key handling: Not verified in this PR.
- Streaming or tool-use behavior: Not verified in this PR.

## Verified Environment

| Item | Value |
|:---|:---|
| OS | Windows 10.0.26200 |
| Tool | OpenAI Codex CLI |
| Codex CLI version | `0.142.5` |
| Command path 1 | `%APPDATA%\npm\codex` |
| Command path 2 | `%APPDATA%\npm\codex.cmd` |
| Setup mode | Tencent Cloud TokenHub cloud API mode |
| Hy3 server backend | TokenHub cloud API |
| Codex profile | `hy3-tokenhub` |
| User-level profile path | `%USERPROFILE%\.codex\hy3-tokenhub.config.toml` |
| Model provider name | `tokenhub` |
| Codex model | `hy3` |
| TokenHub model | `hy3` |
| TokenHub base URL | `https://tokenhub.tencentmaas.com/v1` |
| Chat completions endpoint | `https://tokenhub.tencentmaas.com/v1/chat/completions` |
| API key env var | `TOKENHUB_API_KEY` |
| Verified modes | Interactive TUI and non-interactive exec |
| Verification date | 2026-07-09 |
