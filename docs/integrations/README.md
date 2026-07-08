# Hy3 Integrations

This directory contains end-user integration guides for running Hy3 through popular AI tools and clients.

The guides cover two setup modes:

- **TokenHub cloud API mode**: use Hy3 through Tencent Cloud TokenHub without self-hosting.
- **Local self-hosted mode**: run Hy3 locally as an OpenAI-compatible chat completions server.

Client verification status is tracked in the guide table below.

## Setup Modes

| Mode | Setup | Status |
|:---|:---|:---|
| TokenHub cloud API | [tokenhub.md](tokenhub.md) | Basic Chat Completions smoke test verified; tool integrations still TODO |
| Local self-hosted server | [local-server.md](local-server.md) | Repo-documented server facts only |

## TokenHub Cloud API Mode

Use TokenHub cloud API mode when you want to call Hy3 through Tencent Cloud TokenHub without hosting the model yourself.

TokenHub settings used by these guides:

| Setting | Value |
|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model | `hy3` |
| API key | User-created TokenHub API key, never committed |
| Provider/protocol | OpenAI-compatible |

See [tokenhub.md](tokenhub.md) for setup notes and safety requirements.

## Local Self-hosted Mode

Use local self-hosted mode when you run Hy3 yourself and expose the repository-documented local OpenAI-compatible endpoint.

Local settings used by these guides:

| Setting | Value |
|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` |
| Model | `hy3` |
| API key for local testing | `EMPTY` |
| API protocol | OpenAI-compatible chat completions |

For shared local server setup, see [local-server.md](local-server.md). The repository quickstart documents calling Hy3 through an OpenAI-compatible chat completions API after deploying Hy3 with vLLM or SGLang. See the root README sections for [Quickstart](../../README.md#quickstart) and [Deployment](../../README.md#deployment).

## Guides

| Tool | Guide | Verification status |
|:---|:---|:---|
| Cline | [cline.md](cline.md) | TokenHub mode verified with screenshots |
| Roo Code | [roo-code.md](roo-code.md) | TokenHub mode verified with screenshots |
| Kilo Code | [kilo-code.md](kilo-code.md) | TokenHub mode verified with screenshots |
| OpenCode | [opencode.md](opencode.md) | TODO: verify manually |
| CodeBuddy Code | [codebuddy-code.md](codebuddy-code.md) | TODO: verify manually |

## Manual Verification Checklist

- [ ] Confirm the current installation method and minimum version for each tool.
- [ ] Confirm the exact UI path or configuration file for each tool.
- [ ] Confirm each tool accepts the TokenHub OpenAI-compatible endpoint.
- [ ] Confirm each tool accepts the local Hy3 OpenAI-compatible endpoint.
- [ ] Confirm TokenHub API key scope includes Hy3 when access scope is limited.
- [ ] Run a first chat with `model=hy3`.
- [ ] Run one real task demo for each tool.
- [ ] Capture real screenshots or GIFs from verified runs.
- [ ] Document troubleshooting notes based on observed issues.
- [ ] Record the verified OS, tool version, setup mode, Hy3 server backend when local, and date.

## Screenshots / GIFs

Screenshots and GIFs are added only after real manual verification.

Do not add generated, mocked, or placeholder media as verification evidence.

Screenshots and GIFs must be captured from real local runs before this PR is marked ready for review.

## Showcase Project

TODO: verify manually.

Add the separate small showcase project repository here after it is created and tested:

- Repository: TODO: verify manually
- Demo GIF or video: TODO: verify manually
- README/run instructions: TODO: verify manually
