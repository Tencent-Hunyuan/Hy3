# Hy3 Integrations

This directory contains end-user integration guides for running Hy3 through popular AI tools and clients.

The guides assume that Hy3 is already running as a local OpenAI-compatible chat completions server.

## Base Settings

Use these Hy3 settings throughout the guides:

| Setting | Value |
|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` |
| Model | `hy3` |
| API key for local testing | `EMPTY` |
| API protocol | OpenAI-compatible chat completions |

## Run Hy3 Locally

For shared local server setup, see [local-server.md](local-server.md).

The repository quickstart documents calling Hy3 through an OpenAI-compatible chat completions API after deploying Hy3 with vLLM or SGLang. See the root README sections for [Quickstart](../../README.md#quickstart) and [Deployment](../../README.md#deployment).

The documented local client settings are:

```text
Base URL: http://127.0.0.1:8000/v1
Model: hy3
API key: EMPTY
```

The root README documents vLLM and SGLang server examples that listen on port `8000` and set `--served-model-name hy3`.

## Guides

| Tool | Guide | Verification status |
|:---|:---|:---|
| Local Hy3 server | [local-server.md](local-server.md) | Repo-documented server facts only |
| Cline | [cline.md](cline.md) | TODO: verify manually |
| Continue | [continue.md](continue.md) | TODO: verify manually |
| Roo Code | [roo-code.md](roo-code.md) | TODO: verify manually |
| Aider | [aider.md](aider.md) | TODO: verify manually |
| Dify | [dify.md](dify.md) | TODO: verify manually |

## Manual Verification Checklist

- [ ] Confirm the current installation method and minimum version for each tool.
- [ ] Confirm the exact UI path or configuration file for each tool.
- [ ] Confirm each tool accepts the local Hy3 OpenAI-compatible endpoint.
- [ ] Run a first chat with `model=hy3`.
- [ ] Run one real task demo for each tool.
- [ ] Capture real screenshots or GIFs from verified runs.
- [ ] Document troubleshooting notes based on observed issues.
- [ ] Record the verified OS, tool version, Hy3 server backend, and date.

## Screenshots / GIFs

Screenshots and GIFs will be added only after real manual verification.

Do not add generated, mocked, or placeholder media as verification evidence.

Screenshots and GIFs must be captured from real local runs before this PR is marked ready for review.

## Showcase Project

TODO: verify manually.

Add the separate small showcase project repository here after it is created and tested:

- Repository: TODO: verify manually
- Demo GIF or video: TODO: verify manually
- README/run instructions: TODO: verify manually
