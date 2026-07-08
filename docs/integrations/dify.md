# Use Hy3 with Dify

## Overview

This guide shows how to configure Dify to use a local Hy3 OpenAI-compatible chat completions server.

Verification status: TODO: verify manually.

## Prerequisites

- Dify installation and version: TODO: verify manually.
- Hy3 served locally with an OpenAI-compatible endpoint.
- Local Hy3 base settings:

| Setting | Value |
|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` |
| Model | `hy3` |
| API key for local testing | `EMPTY` |
| API protocol | OpenAI-compatible chat completions |

## Start Hy3 as an OpenAI-compatible Server

Follow the shared local setup in [local-server.md](local-server.md). It summarizes the repository-documented vLLM and SGLang serving examples and the local OpenAI-compatible API settings.

Dify-specific connectivity with this endpoint: TODO: verify manually.

## Configure the Tool

Tool-specific configuration path: TODO: verify manually.

Use these Hy3 settings when configuring the provider:

```text
Base URL: http://127.0.0.1:8000/v1
Model: hy3
API key: EMPTY
Protocol: OpenAI-compatible chat completions
```

Any Dify-specific provider name, custom model field, hosted-versus-local networking detail, or advanced option: TODO: verify manually.

## First Chat

Prompt:

```text
Hello Hy3. Please introduce yourself in two sentences.
```

Observed response: TODO: verify manually.

## Real Task Demo

Task:

```text
Build a simple Dify chat workflow that asks Hy3 to summarize a short document and return three action items.
```

Demo steps and result: TODO: verify manually.

## Screenshots / GIF

- First chat screenshot: TODO: verify manually.
- Real task demo screenshot or GIF: TODO: verify manually.

Add verified media under `docs/integrations/assets/dify/`.

Screenshots and GIFs must be captured from real local runs before this PR is marked ready for review.

## Troubleshooting

- Endpoint connection issue: TODO: verify manually.
- Authentication or API key handling: TODO: verify manually.
- Model selection issue: TODO: verify manually.
- Streaming or tool-use behavior: TODO: verify manually.
- Local networking from Dify to the Hy3 server: TODO: verify manually.

## Verified Environment

| Item | Value |
|:---|:---|
| OS | TODO: verify manually |
| Dify version | TODO: verify manually |
| Hy3 server backend | TODO: verify manually |
| Base URL | `http://127.0.0.1:8000/v1` |
| Model | `hy3` |
| Verification date | TODO: verify manually |
