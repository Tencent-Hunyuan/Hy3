# Hy3 Mainstream AI Tool Integration Guide · Index

> 🌐 中文版本： [README.md](README.md)

## Overview

This documentation collection is intended for **end users**. It explains how to integrate **Tencent Hunyuan Hy3** (a 295B MoE model with an OpenAI-compatible API) into 5 mainstream AI platforms / client tools, so that developers and creators can leverage Hy3's reasoning, Agent, and long-context capabilities in their everyday workflows — without self-hosting a service.

> **Hy3 Capability Cheat-Sheet**
> - **Reasoning mode**: `reasoning_effort` accepts `no_think` (direct reply) / `low` / `high` (deep chain-of-thought)
> - **Agent / Tool Calling**: native Function Call support, works with the vLLM `hy_v3` parser
> - **Context window**: up to 256K tokens
> - **Recommended params**: `temperature=0.9`, `top_p=1.0` (official recommendation)

## Covered Tools

| # | Tool | Type | Use Case | Guide |
|:---:|:---|:---|:---|:---:|
| 1 | **OpenRouter** | Aggregated API Gateway | Zero-deploy, multi-model A/B, unified billing | [→](openrouter/openrouter.en.md) |
| 2 | **Cursor** | AI IDE | Coding, completion, project-level Agent | [→](cursor/cursor.en.md) |
| 3 | **CodeBuddy / WorkBuddy** | AI Dev Assistant | Full-stack generation, workflow automation | [→](codebuddy/codebuddy.en.md) |
| 4 | **Codex CLI** | Terminal AI Coding | CLI coding, automation scripts | [→](codex-cli/codex-cli.en.md) |
| 5 | **Dify** | Low-code Agent Platform | Visual Agent orchestration, RAG knowledge base | [→](dify/dify.en.md) |

## Quick Selection

- **Want the fastest Hy3 experience?** → [OpenRouter](openrouter/openrouter.en.md)
- **Want to code with Hy3 in an IDE?** → [Cursor](cursor/cursor.en.md)
- **Want to build a full-stack project?** → [CodeBuddy](codebuddy/codebuddy.en.md) / [Codex CLI](codex-cli/codex-cli.en.md)
- **Want to build an Agent workflow?** → [Dify](dify/dify.en.md)

## Prerequisites

All tools share one prerequisite: **a reachable Hy3 OpenAI-compatible endpoint**. You can obtain one via:

1. **Self-hosted service** (recommended): deploy with vLLM/SGLang per the [Hy3 README](../../README.md)
2. **API proxy**: call Hy3 through an aggregator such as OpenRouter (no GPU needed)
3. **Cloud service**: official channels such as Tencent Cloud AI Studio

> 💡 All examples in this documentation assume `base_url` = `http://127.0.0.1:8000/v1` and `model` = `hy3`.
> When using a proxy like OpenRouter, replace these with the corresponding base_url and model ID.
