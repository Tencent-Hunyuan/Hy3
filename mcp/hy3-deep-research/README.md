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

**检索默认仅学术源**：`arXiv API` → `OpenAlex` → `Crossref`（合并去重 + 相关性排序）。
中文问题会生成偏 **方法/架构/训练** 的英文学术检索词，并过滤会议同名噪声。
报告强制包含 **「方法脉络与创新」** 主体章节（范式演进、相对前代创新点）。
抓取优先论文摘要页，跳过 PDF 直链。

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

在仓库中进入本目录后执行：

```bash
cd mcp/hy3-deep-research
bash install.sh
```

脚本会：创建 `.venv` → 安装依赖与本包 → 生成 `.env`（若不存在）→ 写出带**绝对路径**的客户端配置到 `configs/generated/` → 做一次 import 冒烟。

手工等效步骤（可选）：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp -n .env.example .env
```

Mock 冒烟（无 Key）：

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
| `HY3_SEARCH_ALLOW_WEB` | 预留；当前默认学术-only，勿依赖通用网页 |

**禁止硬编码 Key。**

## 推荐调用（客户端）

```text
1. clarify_or_plan("……研究问题……")
2. run_deep_research(session_id="<上一步返回>")
3. critique_and_finalize(session_id="...")
```

或一步：`run_deep_research(query="...")`（内部自动建计划）。

## Cursor / WorkBuddy

一键安装后优先使用：

- [`configs/generated/cursor.mcp.json`](./configs/generated/cursor.mcp.json)
- [`configs/generated/workbuddy.mcp.json`](./configs/generated/workbuddy.mcp.json)

（`install.sh` 生成；路径已是本机绝对路径。目录默认 gitignore，勿提交含真实 Key 的副本。）

模板（需自行改路径）见 [`configs/cursor.mcp.json`](./configs/cursor.mcp.json)、[`configs/workbuddy.mcp.json`](./configs/workbuddy.mcp.json)。

把其中 `HY3_API_KEY` 换成真实 Key，合并进客户端 MCP 配置后重启客户端。

### Windows 上的 WorkBuddy

stdio MCP **在 WorkBuddy 所在电脑本地拉起**，因此：

1. 把本仓库拷到 Windows（或 `git clone`）
2. 安装 [Python 3.10+](https://www.python.org/downloads/)，勾选 *Add python.exe to PATH*
3. 在 PowerShell 中安装：

```powershell
cd C:\path\to\Hy3\mcp\hy3-deep-research
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
pip install -e .
copy .env.example .env
# 编辑 .env，填入 HY3_API_KEY
```

4. 打开 WorkBuddy → **插件 / 技能** → **MCP 服务器** → 编辑配置（用户级约在 `%USERPROFILE%\.workbuddy\mcp.json`，项目级为 `<项目>\.workbuddy\mcp.json`）
5. 粘贴并改成你的真实路径，参考 [`configs/workbuddy.windows.mcp.json`](./configs/workbuddy.windows.mcp.json)：

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "C:\\Users\\你的用户名\\Hy3\\mcp\\hy3-deep-research\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\你的用户名\\Hy3\\mcp\\hy3-deep-research\\server.py"],
      "env": {
        "HY3_API_KEY": "你的TokenHub密钥",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3"
      }
    }
  }
}
```

6. 保存后状态应为 🟢；对话里试：`用 hy3-deep-research 的 web_search 搜索 vision language model survey`

**不要**把 Linux 机上的 `/home/bld/...` 路径填进 Windows WorkBuddy。若坚持用当前 Linux 仓库，可在 Windows 装 WSL2，把 `command`/`args` 改成 WSL 内路径，或通过 `wsl.exe` 启动（需本机已装好同一套 `.venv`）。

示例话术：

> 用 hy3-deep-research：先 clarify_or_plan「MCP 协议在 IDE Agent 中的实践」，再 run_deep_research，最后 critique_and_finalize，给我带 [E#] 引用的报告。

## Demo

将 ≤1 分钟录屏放到 `docs/demo.gif` 或 `docs/demo.mp4`。

## License

Apache-2.0（与 Hy3 仓库对齐）
