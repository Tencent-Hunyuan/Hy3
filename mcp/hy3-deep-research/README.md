# Hy3 Deep Research MCP

犀牛鸟 [#3](https://github.com/Tencent-Hunyuan/Hy3/issues/3) · 目标分支 `rhinobird2026`

学术深度研究 MCP：`clarify_or_plan` → `run_deep_research` → `critique_and_finalize`（另有 `web_search` / `fetch_url` / `get_research_status`）。检索走 arXiv / OpenAlex / Crossref；Key 仅环境变量。

## 安装

```bash
cd mcp/hy3-deep-research
bash install.sh          # Linux / macOS / Git Bash
```

```powershell
cd mcp\hy3-deep-research
.\install.ps1            # Windows
```

然后把 `HY3_API_KEY` 写入 `.env`，并把 `configs/generated/*.mcp.json` 拷进 Cursor / WorkBuddy 的 MCP 配置。

## 环境变量

| 变量 | 说明 |
|------|------|
| `HY3_API_KEY` | TokenHub Key（必填，除非 `HY3_MOCK=1`） |
| `HY3_BASE_URL` | 默认 `https://tokenhub.tencentmaas.com/v1` |
| `HY3_MODEL` | 默认 `hy3` |

## 用法

```text
clarify_or_plan("你的问题") → run_deep_research(session_id=...) → critique_and_finalize(session_id=...)
```

冒烟：`bash scripts/smoke_mock.sh`

## Demo

`docs/demo.gif` 或 `docs/demo.mp4`（≤1 分钟）

## License

Apache-2.0
