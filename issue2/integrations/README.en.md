# Use Hy3 in Popular AI Tools

> 中文：[README.md](README.md)

These guides use Hy3 through an OpenAI-compatible endpoint and cover an API gateway, terminal coding, and VS Code agents. Every guide includes prerequisites, complete configuration, a first conversation, an end-to-end task, and troubleshooting.

| Tool | Surface | Guide | End-to-end task |
|:---|:---|:---|:---|
| OpenRouter | Web/API gateway | [Open](openrouter/openrouter.en.md) | Search sources with a tool call and write an evidence report |
| Aider | Terminal coding agent | [Open](aider/aider.en.md) | Create and test a Python slug utility |
| Cline | VS Code agent | [Open](cline/cline.en.md) | Fix a todo app and run its tests |
| Continue | VS Code/CLI agent | [Open](continue/continue.en.md) | Add validation and tests in Agent mode |
| Roo Code | VS Code agent | [Open](roo-code/roo-code.en.md) | Refactor across files and verify regression tests |

## Endpoint presets

| Setting | OpenRouter | Self-hosted vLLM/SGLang |
|:---|:---|:---|
| Base URL | `https://openrouter.ai/api/v1` | `http://127.0.0.1:8000/v1` |
| Model | `tencent/hy3` | `hy3` (or your served model name) |
| API key | `OPENROUTER_API_KEY` | Often `EMPTY`; follow your gateway policy |
| Protocol | OpenAI Chat Completions | OpenAI Chat Completions |

## Shared acceptance task

The guides use the same verification commands so results can be compared:

```bash
cd issue2/demo
python3 -m unittest discover -s tests -v
python3 server.py --check
```

The resulting offline UI is captured in [Evidence Board offline mode](../assets/evidence-board-offline.png). It proves only the local app and offline path; record a separate live tool interaction after adding your own Hy3 endpoint.

## Security conventions

- Never put keys in Markdown, screenshots, tracked files, or browser `localStorage`.
- Prefer environment variables or the product's secret store.
- Enable Hy3's tool-call parser when serving the model if you use Agent mode.
- Start coding agents in review/confirm mode and authorize commands and writes deliberately.
