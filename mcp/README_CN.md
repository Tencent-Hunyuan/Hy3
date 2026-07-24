# Hy3 深度研究 MCP Server

一个开源、即插即用的 **MCP Server**，将[腾讯混元 Hy3](https://github.com/Tencent-Hunyuan/Hy3) API 封装为**深度研究助手**。任何支持 MCP 协议的 AI 客户端（CodeBuddy、WorkBuddy、Cursor、Cline 等）均可零开发接入。

## 功能概述

Server 暴露 **3 个 MCP 工具**，协同完成自动化多步研究：

| 工具 | 功能 | 外部数据源 |
|------|------|-----------|
| `search_web` | 搜索网络获取最新信息 | DuckDuckGo（免 key）或 Tavily（可选） |
| `fetch_url` | 提取网页正文 | trafilatura |
| `deep_research` | 编排完整研究：分解 → 搜索 → 阅读 → Hy3 综合 | Hy3 API + 以上两者 |

### 研究流程

```
用户问题
     │
     ▼
┌─────────────┐
│  Hy3 (low)  │  分解为子查询
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ search_web  │  搜索每个子查询（DuckDuckGo/Tavily）
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  fetch_url  │  阅读优质来源的全文
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Hy3 (high)  │  综合生成带 [n] 引用的报告
└──────┬──────┘
       │
       ▼
  结构化结果
  （报告 + 引用列表）
```

## 前置条件

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)**（推荐）或 pip
- **TokenHub API Key** — 在 <https://console.cloud.tencent.com/tokenhub> 获取

## 快速开始（一键安装）

### 方式 A：使用 uv（推荐）

```bash
# 克隆仓库并切换到 rhinobird2026 分支
git clone -b rhinobird2026 https://github.com/Tencent-Hunyuan/Hy3.git
cd Hy3/mcp

# 以可编辑模式安装
uv pip install -e ".[dev]"

# 设置 API Key
export HUNYUAN_API_KEY="sk-your-key-here"   # Linux/macOS
set HUNYUAN_API_KEY=sk-your-key-here         # Windows CMD
$env:HUNYUAN_API_KEY="sk-your-key-here"      # Windows PowerShell

# 启动 Server
hy3-deep-research
```

### 方式 B：使用 pip

```bash
git clone -b rhinobird2026 https://github.com/Tencent-Hunyuan/Hy3.git
cd Hy3/mcp

pip install -e ".[dev]"

export HUNYUAN_API_KEY="sk-your-key-here"
hy3-deep-research
```

### 方式 C：从预构建包安装（无需克隆源码）

预构建的 wheel 和 sdist 包位于 `dist/` 目录中。

```bash
# 从 wheel 安装（最快 — 无需编译）
pip install hy3_deep_research-0.1.0-py3-none-any.whl

# 或从 sdist 安装（源码分发包）
pip install hy3_deep_research-0.1.0.tar.gz

# 设置 API Key，然后运行
export HUNYUAN_API_KEY="sk-your-key-here"
hy3-deep-research
```

### 方式 D：免安装运行（uvx）

```bash
uvx --from /path/to/Hy3/mcp hy3-deep-research
```

## 配置说明

所有配置均通过**环境变量**传入，不硬编码任何 API Key。

将 `.env.example` 复制为 `.env` 并填入你的值：

```bash
cp .env.example .env
```

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `HUNYUAN_API_KEY` | **是** | — | TokenHub API Key |
| `HUNYUAN_BASE_URL` | 否 | `https://tokenhub.tencentmaas.com/v1` | Hy3 API 端点（TokenHub） |
| `HUNYUAN_MODEL` | 否 | `hy3` | 模型名称 |
| `HUNYUAN_REASONING_FORMAT` | 否 | `top` | reasoning_effort 传递方式：`top`（TokenHub）或 `template`（自部署） |
| `TAVILY_API_KEY` | 否 | — | 设置后使用 Tavily 替代 DuckDuckGo |
| `SEARCH_MAX_RESULTS` | 否 | `5` | 默认搜索结果数 |
| `FETCH_MAX_CHARS` | 否 | `8000` | 每页提取的最大字符数 |
| `FETCH_TIMEOUT` | 否 | `30` | 网页抓取超时（秒） |
| `RESEARCH_MAX_SUB_QUERIES` | 否 | `3` | Hy3 分解的最大子查询数 |
| `RESEARCH_MAX_SOURCES` | 否 | `3` | 全文阅读的最大来源数 |
| `RESEARCH_REASONING_EFFORT` | 否 | `high` | 综合报告的 Hy3 推理深度 |

## 客户端配置

开箱即用的配置文件位于 [`client_configs/`](./client_configs/)。选择对应客户端的文件，将 `your-tokenhub-api-key-here` 替换为你的真实 Key，并将路径调整为你的本地克隆路径。

### CodeBuddy / WorkBuddy

将 `codebuddy_mcp.json` 作为 `.mcp.json` 放在项目根目录，或通过 CLI 添加：

```bash
# CLI 方式
trae mcp add hy3-deep-research -- uvx --from /path/to/Hy3/mcp hy3-deep-research \
  -e HUNYUAN_API_KEY=sk-your-key \
  -e HUNYUAN_BASE_URL=https://tokenhub.tencentmaas.com/v1 \
  -e HUNYUAN_REASONING_FORMAT=top
```

或在项目根目录创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "uvx",
      "args": ["--from", "/path/to/Hy3/mcp", "hy3-deep-research"],
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_MODEL": "hy3",
        "HUNYUAN_REASONING_FORMAT": "top"
      }
    }
  }
}
```

### Cursor

在项目根目录创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "uvx",
      "args": ["--from", "/path/to/Hy3/mcp", "hy3-deep-research"],
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_REASONING_FORMAT": "top"
      }
    }
  }
}
```

重启 Cursor 后，工具将出现在 MCP 面板中。

### Cline

编辑 Cline 扩展设置目录中的 `cline_mcp_settings.json`：

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "uvx",
      "args": ["--from", "/path/to/Hy3/mcp", "hy3-deep-research"],
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_REASONING_FORMAT": "top"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 使用 `python -m` 直接运行（无需 uv）

如果不想使用 `uvx`，安装包后使用 `pip install -e .`，然后用：

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "hy3-deep-research",
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_REASONING_FORMAT": "top"
      }
    }
  }
}
```

或使用 `python -m`：

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "python",
      "args": ["-m", "hy3_deep_research"],
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_REASONING_FORMAT": "top"
      }
    }
  }
}
```

## 工具说明

### `search_web`

搜索网络获取最新信息。

**参数：**
- `query`（字符串，必填）— 搜索查询词。
- `max_results`（整数，默认 5）— 返回结果上限（1-20）。

**返回：** `[{title, url, snippet}, ...]`

### `fetch_url`

抓取网页并提取干净的正文内容。仅支持 http/https 协议。

**参数：**
- `url`（字符串，必填）— 网页完整 URL（仅限 http/https）。
- `max_chars`（整数，默认 8000）— 返回文本的最大字符数。

**返回：** `{url, title, content, success, error}`

### `deep_research`

对指定主题进行深度研究并生成带引用的报告。

**参数：**
- `query`（字符串，必填）— 研究问题或主题。
- `max_search_results`（整数，默认 5）— 每个子查询的最大搜索结果数。
- `max_sources_to_fetch`（整数，默认 3）— 全文阅读的最大 URL 数。
- `reasoning_effort`（字符串，默认 "high"）— Hy3 推理深度：`no_think`、`low` 或 `high`。

**返回：** `{query, sub_queries, sources_searched, sources_fetched, report, citations}`

## Demo 演示

### Demo 视频

仓库中包含一份 demo 视频 [`demo/demo.mp4`](./demo/demo.mp4)，演示内容包括：

1. 在 WorkBuddy 中连接 MCP Server（可见 3 个工具）。
2. 调用 `search_web` 搜索网络结果。
3. 调用 `fetch_url` 提取页面正文。
4. 调用 `deep_research` 运行完整流程：Hy3 分解 → 搜索 → 抓取 → Hy3 综合，生成带 `[n]` 引用的报告。

### 自动化 Demo 脚本

提供了开箱即用的 demo 脚本 [`demo/demo_mcp_client.py`](./demo/demo_mcp_client.py)，它会以子进程启动 MCP Server，执行 MCP 握手，列出工具，并依次调用每个工具——与真实 MCP 客户端行为一致。

```bash
# 设置 API Key
export HUNYUAN_API_KEY="sk-your-key-here"

# 运行 demo（使用默认查询）
python demo/demo_mcp_client.py

# 或指定自定义研究问题
python demo/demo_mcp_client.py --query "大语言模型中的 MoE 架构是什么？"
```

脚本执行流程：
1. 启动 MCP Server 并执行 `initialize` 握手。
2. 调用 `tools/list` 显示所有 3 个已注册工具。
3. 调用 `search_web` 搜索网络结果。
4. 调用 `fetch_url` 阅读第一个结果的全文。
5. 调用 `deep_research` 运行完整流程并打印带引用的研究报告。

### 在 MCP 客户端中进行深度研究

配置好 Server 后，在 AI 客户端中提问：

> "使用 deep_research 工具研究：腾讯混元 Hy3 的核心架构创新有哪些？"

客户端将依次执行：
1. 调用 `deep_research` 传入查询。
2. Hy3 将其分解为子查询，如 `["Hy3 MoE 架构", "Hunyuan Hy3 技术报告", "Hy3 推理能力"]`。
3. 每个子查询在网络上搜索。
4. 抓取并阅读优质来源。
5. Hy3 综合生成带行内 `[1]`、`[2]` 引用的研究报告。

## 客户端验证

本 Server 已在以下 MCP 客户端中验证通过：

| 客户端 | 状态 | 配置文件 |
|--------|------|----------|
| WorkBuddy | ✅ 已验证 | `client_configs/workbuddy_mcp.json` |
| Cursor | ✅ 已验证 | `client_configs/cursor_mcp.json` |
| Cline | ✅ 已验证 | `client_configs/cline_mcp_settings.json` |

## 使用 MCP Inspector 验证

使用官方 MCP Inspector 独立测试 Server：

```bash
# 安装 MCP Inspector（如尚未安装）
npx @modelcontextprotocol/inspector

# 或直接指向你的 Server：
npx @modelcontextprotocol/inspector uvx --from /path/to/Hy3/mcp hy3-deep-research
```

打开 Inspector UI（通常为 `http://localhost:6274`），连接后逐个测试工具。

## 项目结构

```
mcp/
├── pyproject.toml              # 包配置、依赖、入口点
├── .python-version             # Python 3.10
├── .env.example                # 环境变量模板
├── Makefile                    # 开发便捷命令
├── README.md                   # 英文文档
├── README_CN.md                # 中文文档（本文件）
├── CHANGELOG.md                # 变更日志
├── client_configs/             # 开箱即用的客户端配置
│   ├── codebuddy_mcp.json
│   ├── workbuddy_mcp.json
│   ├── cursor_mcp.json
│   ├── cline_mcp_settings.json
│   └── python_direct_mcp.json
├── demo/                       # Demo 客户端 + 视频
│   ├── demo_mcp_client.py      # 启动 Server，调用全部 3 个工具
│   └── demo.mp4                # Demo 视频
├── src/
│   └── hy3_deep_research/
│       ├── __init__.py         # 包元数据 + 导出
│       ├── __main__.py         # python -m 入口
│       ├── config.py           # 基于环境变量的配置
│       ├── hy3_client.py       # Hy3 API 封装（超时 + 重试）
│       ├── models.py           # Pydantic 数据模型
│       ├── server.py           # FastMCP 服务器组装 + 入口
│       └── tools/
│           ├── __init__.py     # 工具导出
│           ├── search.py       # search_web 工具
│           ├── fetch.py        # fetch_url 工具（含 socket 超时 + URL 校验）
│           └── research.py     # deep_research 编排工具
├── tests/                      # 测试套件
└── dist/                       # 预构建包
    ├── hy3_deep_research-0.1.0-py3-none-any.whl
    └── hy3_deep_research-0.1.0.tar.gz
```

## 可靠性特性

- **Hy3 API 调用**：120 秒超时，3 次指数退避重试（1s/2s/4s），覆盖 `APITimeoutError`、`RateLimitError`、`ConnectionError`。
- **网页抓取**：可配置的 socket 超时（`FETCH_TIMEOUT`，默认 30 秒），防止卡死在无响应的服务器上。
- **URL scheme 校验**：`fetch_url` 仅接受 `http://` 和 `https://` 协议的 URL。
- **搜索退避**：DuckDuckGo 失败时最多重试 3 次，增量延迟。
- **结构化错误处理**：所有工具在失败时返回结构化结果，不会导致 Server 崩溃。

## 许可证

Apache License 2.0 — 与 [Hy3](https://github.com/Tencent-Hunyuan/Hy3) 主项目一致。
