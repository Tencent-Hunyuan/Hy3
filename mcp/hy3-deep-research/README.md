# Hy3 Deep Research MCP

犀牛鸟 [#3](https://github.com/Tencent-Hunyuan/Hy3/issues/3) · 目标分支 `rhinobird2026`

学术深度研究 MCP：`clarify_or_plan` → `run_deep_research` → `critique_and_finalize`（另有 `web_search` / `fetch_url` / `get_research_status`）。检索走 arXiv / OpenAlex / Crossref。

## 安装

```bash
cd mcp/hy3-deep-research && bash install.sh
```

```powershell
cd mcp\hy3-deep-research; .\install.ps1
```

## 配置 Key（推荐）

在 **Cursor / WorkBuddy 的 MCP config** 里写 `env`（安装脚本会生成带绝对路径的模板）：

1. 打开 `configs/generated/cursor.mcp.json` 或 `workbuddy.mcp.json`
2. 把 `env.HY3_API_KEY` 改成你的 TokenHub Key
3. 整段合并进客户端 MCP 配置并保存

Server 启动后通过 `os.getenv` 读取客户端注入的环境变量。  
（可选：本地 `.env` 仅用于 CLI/冒烟，不会覆盖客户端已注入的 Key。）

| 变量 | 说明 |
|------|------|
| `HY3_API_KEY` | 必填（除非 `HY3_MOCK=1`） |
| `HY3_BASE_URL` | 默认 `https://tokenhub.tencentmaas.com/v1` |
| `HY3_MODEL` | 默认 `hy3` |

## 用法

```text
clarify_or_plan("...") → run_deep_research(session_id=...) → critique_and_finalize(session_id=...)
```

冒烟：`bash scripts/smoke_mock.sh`（需 `HY3_MOCK=1`）

## Demo

`docs/demo.gif` 或 `docs/demo.mp4`

## License

Apache-2.0
