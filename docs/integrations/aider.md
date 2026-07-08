# Use Hy3 with Aider CLI

## Overview

This guide shows how to configure Aider CLI to use Hy3 through an OpenAI-compatible provider.

Verification status: Aider CLI with Hy3 through Tencent Cloud TokenHub mode was manually verified with screenshots.

## Prerequisites

- Aider version: `0.86.2`.
- Observed executable path:
  - `C:\Users\smallfish\.local\bin\aider.exe`
- Choose one Hy3 setup mode:
  - TokenHub cloud API mode: manually verified.
  - Local self-hosted mode: Not verified in this PR.

## Option A: TokenHub Cloud API Mode

Use TokenHub when you want to call Hy3 through Tencent Cloud TokenHub without self-hosting.

See [tokenhub.md](tokenhub.md) for shared setup and safety notes.

The basic TokenHub Hy3 Chat Completions API smoke test is verified in [tokenhub.md](tokenhub.md). Aider CLI through TokenHub was also manually verified.

| Setting | Value |
|:---|:---|
| TokenHub base URL | `https://tokenhub.tencentmaas.com/v1` |
| TokenHub chat completions endpoint | `https://tokenhub.tencentmaas.com/v1/chat/completions` |
| Aider model | `openai/hy3` |
| TokenHub model | `hy3` |
| `OPENAI_API_BASE` | `https://tokenhub.tencentmaas.com/v1` |
| `OPENAI_API_KEY` | User-created TokenHub API key, not committed and not documented |
| Protocol | OpenAI-compatible chat completions |

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

Aider CLI connectivity with TokenHub mode was manually verified. Local self-hosted connectivity was not verified in this PR.

## Configure the Tool

Set the OpenAI-compatible environment variables before running Aider:

```powershell
$env:OPENAI_API_BASE = "https://tokenhub.tencentmaas.com/v1"
$env:OPENAI_API_KEY = "<user-created TokenHub API key>"
```

Do not commit or document API keys.

Use Aider model `openai/hy3`, which sends TokenHub model `hy3`.

If `aider.exe` is not on `PATH`, call it directly from:

```text
C:\Users\smallfish\.local\bin\aider.exe
```

or add `C:\Users\smallfish\.local\bin` to `PATH` for the current shell.

## First Chat

Command:

```text
C:\Users\smallfish\.local\bin\aider.exe --model openai/hy3 --no-show-model-warnings --message "Hello Hy3. Please introduce yourself in two sentences. Do not inspect the repository or modify any files."
```

Result: completed successfully.

## Real Task Demo

Command:

```text
C:\Users\smallfish\.local\bin\aider.exe --model openai/hy3 --no-show-model-warnings --no-gitignore --read README.md --message "Please inspect README.md in this workspace and summarize what Hy3 is in three bullet points. Do not edit, create, delete, or modify any files."
```

Result: Aider added `README.md` to the chat as read-only and returned a three-bullet summary. No repository files were edited.

## Screenshots / GIFs

- First chat screenshot:

![Aider first chat with Hy3 through TokenHub](assets/aider/aider-first-chat-tokenhub.png)

- Real task demo screenshot:

![Aider README demo with Hy3 through TokenHub](assets/aider/aider-readme-demo-tokenhub.png)

Screenshots are included under `docs/integrations/assets/aider/`. GIFs are optional and were not added.

Screenshots and GIFs must not reveal API keys.

## Troubleshooting

- Aider may warn that `openai/hy3` has unknown context window size and costs. Use `--no-show-model-warnings` to suppress this warning after manual verification.
- Aider may ask whether to add `.aider*` to `.gitignore`. For this docs PR, use `--no-gitignore` or answer `N`, then remove local `.aider.chat.history.md`, `.aider.input.history`, and `.aider.tags.cache.v4` before committing.
- Aider may create local `.aider*` files; these should not be committed.
- If `aider.exe` is not on `PATH`, call it directly from `C:\Users\smallfish\.local\bin\aider.exe` or add that directory to `PATH` for the current shell.
- Do not include or commit the TokenHub API key.
- TokenHub API key access scope for Hy3: Future verification item.
- Local endpoint connection issue: Not verified in this PR.
- Local self-hosted authentication or API key handling: Not verified in this PR.
- Streaming or tool-use behavior: Not verified in this PR.

## Verified Environment

| Item | Value |
|:---|:---|
| OS | Windows 10.0.26200 |
| Tool | Aider CLI |
| Aider version | `0.86.2` |
| Executable path | `C:\Users\smallfish\.local\bin\aider.exe` |
| Setup mode | Tencent Cloud TokenHub cloud API mode |
| Hy3 server backend | TokenHub cloud API |
| `OPENAI_API_BASE` | `https://tokenhub.tencentmaas.com/v1` |
| Aider model | `openai/hy3` |
| TokenHub model | `hy3` |
| Chat completions endpoint | `https://tokenhub.tencentmaas.com/v1/chat/completions` |
| Verification date | 2026-07-09 |
