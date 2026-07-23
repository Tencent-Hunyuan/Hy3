# Hy3 Integrations and Evidence Board

This directory implements [Issue #2](https://github.com/Tencent-Hunyuan/Hy3/issues/2):

- [Five end-user integration guides](integrations/README.en.md)
- [Hy3 Evidence Board](demo/README.en.md), a small web app that keeps API keys on the server and uses Hy3 tool calling to search a local knowledge base before writing an evidence-backed report

![Eight-second offline Evidence Board walkthrough](assets/evidence-board-demo.gif)

> 中文：[README.md](README.md)

## Verification boundary

Configuration fields and commands were checked against each product's official documentation. Offline mode, tests, and the web UI run without an API key. A real Hy3 request requires either an OpenRouter key or a reachable self-hosted OpenAI-compatible Hy3 endpoint. Offline output is visibly marked and never presented as model output.

## Layout

```text
issue2/
├── integrations/       # Bilingual integration guides
├── demo/               # Standalone-ready showcase source
└── assets/             # Locally captured screenshots and demo media
```
