# Use Hy3 with Roo Code

## Overview

This guide shows how to configure Roo Code to use Hy3 through an OpenAI-compatible provider.

Verification status: Roo Code with Hy3 through Tencent Cloud TokenHub mode was manually verified with screenshots.

## Prerequisites

- Verified Roo Code version: `3.54.0`.
- VS Code extension identifier: `rooveterinaryinc.roo-cline`.
- Install Roo Code from the VS Code Extensions view, or use:

```powershell
code --install-extension rooveterinaryinc.roo-cline
```

- Confirm the installed extension and version:

```powershell
code --list-extensions --show-versions | Select-String -Pattern "roo|veterinary|cline"
```

Expected verified result:

```text
rooveterinaryinc.roo-cline@3.54.0
```

- Choose one Hy3 setup mode:
  - TokenHub cloud API mode: manually verified.
  - Local self-hosted mode: Not verified in this PR.

## Option A: TokenHub Cloud API Mode

Use TokenHub when you want to call Hy3 through Tencent Cloud TokenHub without self-hosting.

See [tokenhub.md](tokenhub.md) for shared setup and safety notes.

The basic TokenHub Hy3 Chat Completions API smoke test is verified in [tokenhub.md](tokenhub.md). Roo Code-specific setup through TokenHub was also manually verified.

| Setting | Value |
|:---|:---|
| API configuration label | `Hy3 TokenHub` (user-defined display name) |
| API provider | OpenAI Compatible |
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Chat Completions endpoint | `https://tokenhub.tencentmaas.com/v1/chat/completions` |
| Model | `hy3` |
| API key | User-created TokenHub API key, not committed and not documented |
| Protocol | OpenAI-compatible Chat Completions |

If the TokenHub API key access scope is limited, Hy3 must be included in that scope.

## Option B: Local Self-hosted Mode

Use local self-hosted mode when Hy3 is running as a local OpenAI-compatible Chat Completions server.

See [local-server.md](local-server.md) for the repository-documented vLLM and SGLang serving examples.

| Setting | Value |
|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` |
| Model | `hy3` |
| API key for local testing | `EMPTY` |
| API protocol | OpenAI-compatible Chat Completions |
| Verification status | Not verified in this PR |

For TokenHub cloud API mode, no local Hy3 server is required.

For local self-hosted mode, follow [local-server.md](local-server.md).

Roo Code-specific connectivity with TokenHub mode was manually verified. Local self-hosted connectivity was not verified in this PR.

## Configure the Tool

Roo Code setup path: **Roo Code sidebar -> Configure provider -> OpenAI Compatible provider settings**.

For the verified TokenHub configuration:

| Field | Verified value |
|:---|:---|
| API configuration label | `Hy3 TokenHub` |
| API provider | OpenAI Compatible |
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model | `hy3` |
| API key | User-created TokenHub API key, not committed and not documented |

`Hy3 TokenHub` is only a user-defined display label for the Roo Code API configuration. The actual connection is determined by the provider, base URL, model, and API key fields.

Exact Roo Code secret-storage behavior and untested advanced options are outside the scope of this verification.

## First Chat

Prompt:

```text
Reply only in English and write exactly two sentences. Describe how you can help with code review, debugging, testing, explanation, and refactoring. Do not identify yourself, mention any company or organization, refer to the current repository or workspace, inspect files, or use tools.
```

Result: Roo Code returned exactly two English sentences describing code-review, debugging, testing, explanation, and refactoring capabilities. It did not inspect files or use tools for this first-chat task.

## Real Task Demo

Task:

```text
Reply only in English. Read README.md only, without printing the full file, and summarize the Model Introduction in exactly three concise bullet points: architecture and scale; core capabilities; open-source and deployment. Use tools only as needed to read README.md. Do not inspect any other files, run unrelated commands, or edit, create, delete, or modify anything.
```

Result: Roo Code read `README.md` and returned three English bullet points covering architecture and scale, core capabilities, and open-source deployment. No repository files were edited.

## Screenshots / GIF

- First chat screenshot:

![Roo Code first chat with Hy3 through TokenHub](assets/roo-code/roo-code-first-chat-tokenhub.png)

- Real task demo screenshot:

![Roo Code README demo with Hy3 through TokenHub](assets/roo-code/roo-code-readme-demo-tokenhub.png)

Screenshots are included under `docs/integrations/assets/roo-code/`. GIFs are optional and were not added.

Screenshots and GIFs must not reveal API keys.

## Troubleshooting

- Verify the installed extension identifier with `code --list-extensions --show-versions`; the verified identifier is `rooveterinaryinc.roo-cline`.
- A custom API configuration label such as `Hy3 TokenHub` can make the active TokenHub profile easier to identify in screenshots and normal use. The label itself does not change connection behavior.
- TokenHub API key handling was verified by using a user-created key without committing, documenting, or displaying it.
- TokenHub API key access scope for Hy3: Future verification item.
- Local endpoint connection issue: Not verified in this PR.
- Local self-hosted authentication or API key handling: Not verified in this PR.
- Model selection issue: TokenHub mode verified with `hy3`.
- Roo Code used its built-in file-reading flow for the README demo. Dedicated OpenAI-protocol tool-calling behavior was not independently tested in this PR.
- Dedicated streaming-behavior testing was not performed in this PR.

## Verified Environment

| Item | Value |
|:---|:---|
| OS | Windows 11 25H2 (build 26200) |
| Editor | VS Code |
| Extension | Roo Code (`rooveterinaryinc.roo-cline`) |
| Roo Code version | `3.54.0` |
| Roo mode | Architect |
| API configuration label | `Hy3 TokenHub` |
| Setup mode | Tencent Cloud TokenHub cloud API mode |
| Hy3 server backend | TokenHub cloud API |
| API provider | OpenAI Compatible |
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model | `hy3` |
| Verified modes | First chat without tool use and read-only README summary |
| Verification date | 2026-07-10 |
