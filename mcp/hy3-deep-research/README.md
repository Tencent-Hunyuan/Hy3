# Hy3 Deep Research MCP Server

> 犀牛鸟 Issue [#3](https://github.com/Tencent-Hunyuan/Hy3/issues/3)  
> 目标分支：`rhinobird2026`

把业界 Deep Research 常见闭环收进 MCP Server（参考 OpenAI / Gemini Deep Research、LangChain Open Deep Research）：

```text
clarify_or_plan
    → run_deep_research（并行子查询检索 → 精读 → 反思缺口 → 跟进检索 → 带引用草稿）
    → critique_and_finalize（引用审计 + 不确定性终稿）
```

原子工具 `web_search` / `fetch_url` 仍可单独调用。

## Tools

| Tool | 作用 |
|------|------|
| `clarify_or_plan` | Hy3 生成研究简报、可并行子问题、停止条件、大纲；返回 `session_id` |
| `run_deep_research` | **内建多轮研究闭环**（并行搜索+抓页+反思补洞+草稿） |
| `critique_and_finalize` | 审稿 / 引用审计 → 终稿 |
| `get_research_status` | 查看会话计划、证据、缺口 |
| `web_search` | 原子：网页搜索 |
| `fetch_url` | 原子：抓取页面正文 |

## 一键安装

在仓库根目录 `Hy3/`：

```bash
cd mcp/hy3-deep-research
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 或只在 MCP 客户端 env 配 Key
```

冒烟（无 Key）：

```bash
bash scripts/smoke_mock.sh
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `HY3_API_KEY` | TokenHub Key（`HY3_MOCK=1` 时可省） |
| `HY3_BASE_URL` | 默认 `https://tokenhub.tencentmaas.com/v1` |
| `HY3_MODEL` | 默认 `hy3` |
| `HY3_MOCK` | `1` = 本地 mock 联调 |

**禁止硬编码 Key。**

## 推荐调用（客户端）

```text
1. clarify_or_plan("……研究问题……")
2. run_deep_research(session_id="<上一步返回>")
3. critique_and_finalize(session_id="...")
```

或一步：`run_deep_research(query="...")`（内部自动建计划）。

## Cursor / WorkBuddy

见 [`configs/cursor.mcp.json`](./configs/cursor.mcp.json)、[`configs/workbuddy.mcp.json`](./configs/workbuddy.mcp.json)。

请把 `command` 换成 `.venv/bin/python` 的**绝对路径**，`args` 指向本目录 `server.py`，并填入真实 `HY3_API_KEY`。

示例话术：

> 用 hy3-deep-research：先 clarify_or_plan「MCP 协议在 IDE Agent 中的实践」，再 run_deep_research，最后 critique_and_finalize，给我带 [E#] 引用的报告。

## Demo

将 ≤1 分钟录屏放到 `docs/demo.gif` 或 `docs/demo.mp4`。

## License

Apache-2.0（与 Hy3 仓库对齐）
