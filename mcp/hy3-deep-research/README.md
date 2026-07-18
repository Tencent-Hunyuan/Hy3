# Hy3 Deep Research MCP Server

> 犀牛鸟 Issue [#3](https://github.com/Tencent-Hunyuan/Hy3/issues/3)：基于 MCP 的 **深度研究助手**（搜索 + 读页 + Hy3 分析 / 结论文档）。  
> 目标分支：`rhinobird2026`。

可被 **Cursor / WorkBuddy（CodeBuddy）/ Cline** 等 MCP 客户端以 **stdio** 方式一键拉起；API Key 仅通过环境变量传入。

## 能力（4 个 Tools）

| Tool | 作用 |
|------|------|
| `web_search` | 网页搜索（DuckDuckGo，无需搜索 API Key） |
| `fetch_url` | 抓取 URL 并提取纯文本 |
| `hy3_analyze` | 用 Hy3 对资料做深度分析（可开 thinking） |
| `hy3_research_report` | 用 Hy3 生成结构化研究报告 |

推荐调用链：

```text
web_search → fetch_url（1～N 次）→ hy3_analyze → hy3_research_report
```

## 一键安装

在仓库根目录 `Hy3/`：

```bash
cd mcp/hy3-deep-research
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# 或：pip install -e .
cp .env.example .env
# 编辑 .env，填入 HY3_API_KEY（也可只在 MCP 客户端 env 中配置）
```

冒烟（不消耗额度）：

```bash
bash scripts/smoke_mock.sh
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `HY3_API_KEY` | 是* | TokenHub API Key（`HY3_MOCK=1` 时可省略） |
| `HY3_BASE_URL` | 否 | 默认 `https://tokenhub.tencentmaas.com/v1` |
| `HY3_MODEL` | 否 | 默认 `hy3` |
| `HY3_MOCK` | 否 | `1` 时走本地 mock，便于无 Key 联调 |

\* 真实调用必须提供 Key；**代码中不硬编码 Key**。

## Cursor 配置

将 [`configs/cursor.mcp.json`](./configs/cursor.mcp.json) 合并进 Cursor 的 MCP 设置（或项目 `.cursor/mcp.json`），并把路径/`HY3_API_KEY` 换成真实值。

示例（绝对路径更稳）：

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "/ABSOLUTE/PATH/TO/Hy3/mcp/hy3-deep-research/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/Hy3/mcp/hy3-deep-research/server.py"],
      "env": {
        "HY3_API_KEY": "sk-xxxxxxxx",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3"
      }
    }
  }
}
```

在 Cursor Agent 中可试：

> 使用 hy3-deep-research 工具，调研「MCP 协议是什么」，搜索后抓 1～2 个页面，再生成研究报告。

## WorkBuddy / CodeBuddy 配置

参考 [`configs/workbuddy.mcp.json`](./configs/workbuddy.mcp.json)。在客户端的 **MCP / 自定义工具** 中添加同结构配置（`command` + `args` + `env`）。

若支持 CLI 添加，逻辑等价于：用指定 Python 启动 `server.py`，并注入 `HY3_API_KEY`。

可运行 demo 话术：

> 调用 `web_search` 查「混元 Hy3 Agent」，再 `hy3_research_report` 输出一页执行摘要。

## 目录

```text
mcp/hy3-deep-research/
  server.py                 # MCP Server（stdio）
  requirements.txt
  pyproject.toml
  .env.example
  configs/cursor.mcp.json
  configs/workbuddy.mcp.json
  scripts/smoke_mock.sh
  docs/                     # 放置 demo.gif / demo.mp4
```

## Demo 录制

请录制 ≤1 分钟屏幕录像或 GIF，保存为：

- `mcp/hy3-deep-research/docs/demo.gif` 或 `demo.mp4`

建议镜头：Cursor/WorkBuddy 加载 MCP → 调用 `web_search` → `hy3_analyze` / `hy3_research_report` → 展示结果。

## 安全说明

- 勿把含真实 Key 的配置提交进 Git。  
- `web_search` / `fetch_url` 会访问公网；请仅用于合法公开网页。  
- Hy3 输出可能有幻觉，报告中的事实请人工复核。

## License

与 Hy3 仓库一致（Apache-2.0）。
