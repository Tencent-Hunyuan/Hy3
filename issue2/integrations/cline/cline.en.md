# Use Hy3 with Cline

> 中文：[cline.md](cline.md) · [Back to index](../README.en.md)

Cline is a VS Code coding agent that can edit files, run commands, and use a browser. Its official repository supports OpenRouter and arbitrary OpenAI-compatible APIs. Configure secrets through its provider form rather than editing internal secret files.

## Install

1. Use VS Code 1.93+ for Cline's terminal integration.
2. Install **Cline** by publisher `saoudrizwan` from the extension marketplace.
3. Record the installed version and prefer the current stable release. These fields were checked against the [official repository](https://github.com/cline/cline) on 2026-07-23.

## Configure

OpenRouter:

```text
API Provider: OpenRouter
OpenRouter API Key: <enter through the secret field>
Model: tencent/hy3
```

Self-hosted:

```text
API Provider: OpenAI Compatible
Base URL: http://127.0.0.1:8000/v1
API Key: EMPTY
Model ID: hy3
```

The OpenAI Compatible provider uses `/chat/completions`. Self-hosted vLLM must enable `--tool-call-parser hy_v3 --enable-auto-tool-choice` for agent tools.

## First conversation

Disable auto-approval or restrict it to reads, then ask Cline to list the workspace and read its README without writing, running commands, or using the network. Verify its timeline contains only reads and `git status --short` is unchanged.

## End-to-end task

Ask Cline to modify only `issue2/demo/`, normalize whitespace, validate questions at 10–500 characters, add success/short/long unit tests, and run the full suite without committing. Review every requested permission, confirm the path boundary, and rerun the tests yourself.

![Evidence Board offline screenshot](../../assets/evidence-board-offline.png)

## Troubleshooting

| Symptom | Fix |
|:---|:---|
| Hy3 absent from list | Refresh OpenRouter and search `tencent/hy3`, or type `hy3` in compatible mode |
| Tool calls become prose | Check the Hy3 tool parser and provider selection |
| HTTP 400 | Remove optional reasoning settings and test a basic request at temperature 0.9 |
| Unsafe autonomy | Disable Auto Approve or allow only reads and test commands |
| Terminal output missing | Update VS Code/Cline and enable shell integration |

Before submission, record a live Cline tool timeline with Hy3. The repository screenshot only shows the runnable outcome.
