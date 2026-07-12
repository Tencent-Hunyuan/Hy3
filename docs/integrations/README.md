<p align="left">
  English&nbsp; | &nbsp;<a href="README_CN.md">中文</a>
</p>

# Use Hy3 in popular AI tools

These guides show verified ways to connect Hy3 through Tencent TokenHub. Every flow was tested on July 12, 2026 with the latest available client release, model ID `hy3`, a successful first conversation, and a read-only repository task.

## Integration matrix

| Tool | Category | Protocol | Status | Guide |
|:---|:---|:---:|:---:|:---|
| Cline | VS Code agent | Chat Completions | Verified | [Guide](cline.md) |
| Continue | VS Code / JetBrains assistant | Chat Completions | Verified | [Guide](continue.md) |
| Aider `0.86.2` | CLI coding assistant | Chat Completions | Verified | [Guide](aider.md) |
| Dify + Tencent TokenHub plugin `0.0.4` | Low-code / agent platform | Chat Completions | Verified | [Guide](dify.md) |
| Codex CLI `0.144.1` | CLI coding agent | Responses API | Verified | [Guide](codex-cli.md) |

## Shared configuration

| Setting | Value |
|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model ID | `hy3` |
| API Key | A rotated Tencent TokenHub Key with Hy3 access |

Codex CLI uses TokenHub's Responses API compatibility layer. The other verified clients use the OpenAI-compatible Chat Completions path or a provider plugin that handles it internally.

## Validation task

Every real-task recording uses the same read-only prompt:

```text
Based only on the read-only files provided, summarize this application's
architecture, identify three concrete risks with file references, and propose
a three-step improvement plan. Do not modify files and do not run Git commands.
```

## Security

- Keep API Keys in environment variables, secret stores, or masked provider fields.
- Never place a Key in source code, prompts, screenshots, GIF frames, or Git history.
- Use a rotated Key for validation and review every tool action before approval.

## References

- [Tencent TokenHub](https://cloud.tencent.com/product/tokenhub)
- [Tencent TokenHub Codex guide](https://cloud.tencent.com/document/product/1823/133532)
- [Tencent TokenHub Dify plugin](https://marketplace.dify.ai/plugin/lws123321/tencent-tokenhub)
- [Cline OpenAI-compatible provider](https://docs.cline.bot/provider-config/openai-compatible)
- [Continue OpenAI provider](https://docs.continue.dev/customize/model-providers/top-level/openai)
- [Aider OpenAI-compatible APIs](https://aider.chat/docs/llms/openai-compat.html)
- [OpenAI Codex configuration reference](https://developers.openai.com/codex/config-reference/)
