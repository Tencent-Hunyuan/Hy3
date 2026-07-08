# Use Hy3 with CodeBuddy Code

## Overview

This guide shows how to configure CodeBuddy Code to use Hy3 through an OpenAI-compatible provider.

Verification status: TODO: verify manually.

## Prerequisites

- CodeBuddy Code installation and version: TODO: verify manually.
- Choose one Hy3 setup mode:
  - TokenHub cloud API mode.
  - Local self-hosted mode.

## Option A: TokenHub Cloud API Mode

Use TokenHub when you want to call Hy3 through Tencent Cloud TokenHub without self-hosting.

See [tokenhub.md](tokenhub.md) for shared setup and safety notes.

| Setting | Value |
|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model | `hy3` |
| API key | User-created TokenHub API key |
| Protocol | OpenAI-compatible |

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

## Start Hy3 as an OpenAI-compatible Server

For TokenHub cloud API mode, no local Hy3 server is required.

For local self-hosted mode, follow [local-server.md](local-server.md).

CodeBuddy Code-specific connectivity with either endpoint: TODO: verify manually.

## Configure the Tool

Tool-specific configuration path: TODO: verify manually.

Use either TokenHub cloud API mode or local self-hosted mode when configuring the provider. Do not commit API keys.

Any CodeBuddy Code-specific provider name, custom model field, secret storage, or advanced option: TODO: verify manually.

## First Chat

Prompt:

```text
Hello Hy3. Please introduce yourself in two sentences.
```

Observed response: TODO: verify manually.

## Real Task Demo

Task:

```text
Ask Hy3 through CodeBuddy Code to explain a small code change and list one possible risk.
```

Demo steps and result: TODO: verify manually.

## Screenshots / GIF

- First chat screenshot: TODO: verify manually.
- Real task demo screenshot or GIF: TODO: verify manually.

Add verified media under `docs/integrations/assets/codebuddy-code/`.

Screenshots and GIFs must be captured from real runs before this PR is marked ready for review.

## Troubleshooting

- TokenHub API key handling: TODO: verify manually.
- TokenHub API key access scope for Hy3: TODO: verify manually.
- Local endpoint connection issue: TODO: verify manually.
- Model selection issue: TODO: verify manually.
- Streaming or tool-use behavior: TODO: verify manually.

## Verified Environment

| Item | Value |
|:---|:---|
| OS | TODO: verify manually |
| CodeBuddy Code version | TODO: verify manually |
| Setup mode | TODO: verify manually |
| Hy3 server backend | TODO: verify manually |
| Base URL | TODO: verify manually |
| Model | `hy3` |
| Verification date | TODO: verify manually |
