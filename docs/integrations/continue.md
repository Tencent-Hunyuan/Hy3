# Use Hy3 with Continue

## Overview

This guide shows how to configure the Continue VS Code extension to use Hy3 through an OpenAI-compatible provider.

Verification status: Continue with Hy3 through Tencent Cloud TokenHub mode was manually verified with screenshots.

## Prerequisites

- Continue version: `2.0.0`.
- VS Code extension identifier: `continue.continue`.
- Continue v2.0.0 uses local extension configuration.
- Choose one Hy3 setup mode:
  - TokenHub cloud API mode: manually verified.
  - Local self-hosted mode: Not verified in this PR.

## Option A: TokenHub Cloud API Mode

Use TokenHub when you want to call Hy3 through Tencent Cloud TokenHub without self-hosting.

See [tokenhub.md](tokenhub.md) for shared setup and safety notes.

The basic TokenHub Hy3 Chat Completions API smoke test is verified in [tokenhub.md](tokenhub.md). Continue through TokenHub was also manually verified.

| Setting | Value |
|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Chat completions endpoint | `https://tokenhub.tencentmaas.com/v1/chat/completions` |
| Provider | `openai` |
| Model | `hy3` |
| API key | User-created TokenHub API key, not committed and not documented |
| Protocol | OpenAI-compatible chat completions |
| Config name shown in UI | Main Config |
| Model display in Continue UI | Hy3 TokenHub |
| Chat mode used | Agent |

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

Continue connectivity with TokenHub mode was manually verified. Local self-hosted connectivity was not verified in this PR.

## Configure the Tool

Continue v2.0.0 was configured through the local extension configuration file:

```text
%USERPROFILE%\.continue\config.yaml
```

Verified provider configuration:

```yaml
models:
  - name: Hy3 TokenHub
    provider: openai
    model: hy3
    apiBase: https://tokenhub.tencentmaas.com/v1
    apiKey: <user-created TokenHub API key>
```

Do not commit or document API keys.

Exact secret storage behavior and advanced options are future verification items.

## First Chat

Mode: Agent.

Prompt:

```text
Hello Hy3. Please introduce yourself in two sentences.
```

Result: completed successfully.

## Real Task Demo

Mode: Agent.

Task:

```text
Please inspect README.md in this workspace and summarize what Hy3 is in three bullet points. Do not edit, create, delete, or modify any files.
```

Result: Continue read `README.md` and returned a three-bullet summary. No repository files were edited.

## Screenshots / GIFs

- First chat screenshot:

![Continue first chat with Hy3 through TokenHub](assets/continue/continue-first-chat-tokenhub.png)

- Real task demo screenshot:

![Continue README demo with Hy3 through TokenHub](assets/continue/continue-readme-demo-tokenhub.png)

Screenshots are included under `docs/integrations/assets/continue/`. GIFs are optional and were not added.

Screenshots and GIFs must not reveal API keys.

## Troubleshooting

- `401` errors can mean the TokenHub API key is missing, incomplete, invalid, or copied with extra text. Check that `apiKey` contains only the raw TokenHub API key, without `Bearer` and without extra whitespace.
- `apiBase` should be `https://tokenhub.tencentmaas.com/v1`, not the full `/chat/completions` endpoint.
- `model` should be `hy3`; the UI display name can be Hy3 TokenHub.
- TokenHub API key access scope for Hy3: Future verification item.
- Local endpoint connection issue: Not verified in this PR.
- Local self-hosted authentication or API key handling: Not verified in this PR.
- Streaming or tool-use behavior: Not verified in this PR.

## Verified Environment

| Item | Value |
|:---|:---|
| OS | Windows 10.0.26200 |
| Editor | VS Code |
| Extension | Continue (`continue.continue`) |
| Continue version | `2.0.0` |
| Setup mode | Tencent Cloud TokenHub cloud API mode |
| Hy3 server backend | TokenHub cloud API |
| Config file | `%USERPROFILE%\.continue\config.yaml` |
| Config name shown in UI | Main Config |
| Provider | `openai` |
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Chat completions endpoint | `https://tokenhub.tencentmaas.com/v1/chat/completions` |
| Model | `hy3` |
| Model display | Hy3 TokenHub |
| Chat mode | Agent |
| Verification date | 2026-07-08 |
