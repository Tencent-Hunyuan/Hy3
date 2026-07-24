<p align="left">
   <a href="README.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

# Hy3 知识库问答 MCP Server

基于 [腾讯混元 Hy3](https://github.com/Tencent-Hunyuan/Hy3)（295B 参数、21B 激活的 MoE 模型）提供**知识库问答**能力的 MCP（Model Context Protocol）Server。

本 Server 让任何兼容 MCP 的客户端（CodeBuddy、WorkBuddy、Cursor、Cline 等）可以直接读取本地文档并向 Hy3 提问，无需额外开发。

## 功能特性

- **文档读取** — 支持 `.txt`、`.md`、`.csv`、`.json`、`.py`、`.pdf`、`.docx` 等格式
- **知识库问答** — 基于文档内容提问，Hy3 提供有依据的精准回答
- **智能摘要** — 生成详细、简要或要点式摘要
- **目录搜索与问答** — 扫描目录下相关文件，基于内容回答问题
- **网页搜索与问答** — 搜索网页获取最新信息，由 Hy3 提供精准回答
- **文档对比** — 对比多个文档，分析差异、共识或矛盾之处

## 快速开始

### 1. 环境要求

- Python 3.10+
- 有效的 Hy3 API Key（从[腾讯云 TokenHub](https://cloud.tencent.com/product/hunyuan) 获取）
- （可选）Tavily API Key，用于网页搜索（在 [https://tavily.com](https://tavily.com) 免费获取）

### 2. 安装

```bash
# 克隆仓库
git clone -b rhinobird2026 https://github.com/Tencent-Hunyuan/Hy3.git
cd Hy3

# 进入 MCP Server 目录
cd hy3-mcp-server

# 创建虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 以可编辑模式安装（使 `python -m hy3_mcp_server.server` 可用）
pip install -e .
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env
```

编辑 `.env` 文件，设置你的 API Key：

```
HY3_API_KEY=your_actual_api_key_here
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3
TAVILY_API_KEY=your_tavily_api_key_here
```

> **重要：** 请勿在源代码中硬编码 API Key，务必通过环境变量传入。

### 4. 运行 Server

```bash
# 方式一：通过包入口点运行（需先 pip install -e .）
hy3-mcp-server

# 方式二：作为 Python 模块运行
python -m hy3_mcp_server.server
```

## MCP 客户端配置

### CodeBuddy / WorkBuddy（项目级）

首先在 Python 环境中安装本包：

```bash
cd /path/to/hy3-mcp-server
pip install -e .
```

然后在项目根目录添加 `.mcp.json` 文件：

```json
{
  "mcpServers": {
    "hy3-knowledge-base": {
      "command": "python",
      "args": ["-m", "hy3_mcp_server.server"],
      "env": {
        "HY3_API_KEY": "your_api_key_here",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3",
        "TAVILY_API_KEY": "your_tavily_api_key_here"
      }
    }
  }
}
```

或通过 CLI 添加：

```bash
# CodeBuddy
codebuddy mcp add hy3-knowledge-base -- python -m hy3_mcp_server.server

# WorkBuddy
workbuddy mcp add hy3-knowledge-base -- python -m hy3_mcp_server.server
```

### Cursor

在 Cursor MCP 设置中添加（`Settings > MCP`）：

```json
{
  "mcpServers": {
    "hy3-knowledge-base": {
      "command": "python",
      "args": ["-m", "hy3_mcp_server.server"],
      "env": {
        "HY3_API_KEY": "your_api_key_here",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3",
        "TAVILY_API_KEY": "your_tavily_api_key_here"
      }
    }
  }
}
```

### Cline

添加到 `cline_mcp_settings.json`：

```json
{
  "mcpServers": {
    "hy3-knowledge-base": {
      "command": "python",
      "args": ["-m", "hy3_mcp_server.server"],
      "env": {
        "HY3_API_KEY": "your_api_key_here",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3",
        "TAVILY_API_KEY": "your_tavily_api_key_here"
      }
    }
  }
}
```

## 工具列表

### 1. `read_file`

读取本地文件并提取文本内容。

**参数：**
| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_path` | string | 是 | 要读取的文件路径 |
| `max_chars` | integer | 否 | 返回的最大字符数（默认：50000） |

**MCP 客户端中的使用示例：**
> "帮我读取 ./docs/architecture.md 文件"

### 2. `ask_about_documents`

基于一个或多个文档内容向 Hy3 提问，获取精准回答。

**参数：**
| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_paths` | array[string] | 是 | 作为上下文读取的文件路径列表 |
| `question` | string | 是 | 要提问的问题 |
| `reasoning_effort` | string | 否 | "no_think"（直接回复）、"low"（浅度思考）或 "high"（深度推理，默认） |

**MCP 客户端中的使用示例：**
> "根据 ./src/main.py 和 ./README.md，这个项目的架构是什么？"

### 3. `summarize_document`

使用 Hy3 对文档进行智能摘要，支持多种风格。

**参数：**
| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_path` | string | 是 | 文档路径 |
| `summary_type` | string | 否 | "comprehensive"（详细）、"brief"（简要）或 "bullet"（要点式，默认：comprehensive） |
| `max_length` | integer | 否 | 摘要目标字数（默认：500） |

**MCP 客户端中的使用示例：**
> "用要点式总结 ./report.pdf"

### 4. `search_files_and_answer`

在目录中搜索文件，并基于内容回答问题。

**参数：**
| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `directory` | string | 是 | 要搜索的目录路径 |
| `query` | string | 是 | 要搜索的问题或主题 |
| `file_pattern` | string | 否 | 文件匹配模式（如 "*.py"、"*.md"，默认："*"） |
| `max_files` | integer | 否 | 最多读取的文件数（默认：10） |

**MCP 客户端中的使用示例：**
> "搜索 ./src 目录，告诉我认证是怎么实现的"

### 5. `web_search_and_answer`

通过 Tavily Search API 搜索网页，然后使用 Hy3 回答。

**参数：**
| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 搜索查询 |
| `max_results` | integer | 否 | 最大搜索结果数（默认：5） |
| `reasoning_effort` | string | 否 | "no_think"（直接回复）、"low"（浅度思考）或 "high"（深度推理，默认） |

**MCP 客户端中的使用示例：**
> "搜索网页，了解 Python 3.13 的最新特性并解释"

### 6. `compare_documents`

对比两个或多个文档，使用 Hy3 分析差异。

**参数：**
| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_paths` | array[string] | 是 | 要对比的文件路径列表（至少 2 个） |
| `aspect` | string | 否 | "general"（一般对比）、"differences"（差异）、"agreements"（共识）或 "contradictions"（矛盾，默认：general） |
| `reasoning_effort` | string | 否 | "no_think"（直接回复）、"low"（浅度思考）或 "high"（深度推理，默认） |

**MCP 客户端中的使用示例：**
> "对比 ./docs/v1_spec.md 和 ./docs/v2_spec.md，突出差异"

## 架构

```
┌─────────────────────┐
│   MCP 客户端        │
│ (Cursor / Cline /   │
│  CodeBuddy / ...)   │
└─────────┬───────────┘
          │ MCP 协议（stdio）
          ▼
┌─────────────────────┐
│  hy3-mcp-server     │
│  ┌───────────────┐  │
│  │  FastMCP      │  │
│  │  (MCP 层)     │  │
│  └───────┬───────┘  │
│  ┌───────┴───────┐  │
│  │ 工具处理器     │  │
│  │ • read_file   │  │
│  │ • ask_about_  │  │
│  │   documents   │  │
│  │ • summarize_  │  │
│  │   document    │  │
│  │ • search_     │  │
│  │   files_and_  │  │
│  │   answer      │  │
│  │ • web_search_ │  │
│  │   and_answer  │  │
│  │ • compare_    │  │
│  │   documents   │  │
│  └───────┬───────┘  │
│  ┌───────┴───────┐  │
│  │ hy3_client    │  │──▶ Hy3 API（OpenAI 兼容）
│  │ (API 层)      │  │    tokenhub.tencentmaas.com
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ web_search    │  │──▶ Tavily Search API
│  │ (搜索层)      │  │    tavily.com
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ 文件解析器     │  │──▶ 本地文件系统
│  │ • 文本/PDF/   │  │
│  │   DOCX/代码   │  │
│  └───────────────┘  │
└─────────────────────┘
```

## 验证

本 Server 已在以下 MCP 客户端中验证可用：

1. **Cursor** — 通过 Settings > MCP 添加，工具在 Agent 模式中可见
2. **Cline** — 添加到 `cline_mcp_settings.json`，工具可在聊天中调用

自行验证步骤：
1. 在 MCP 客户端中配置本 Server
2. 提问："读取 ./README.md 文件并总结"
3. 客户端应依次调用 `read_file` 和 `summarize_document`

你应该能看到 6 个可用工具：`read_file`、`ask_about_documents`、`summarize_document`、`search_files_and_answer`、`web_search_and_answer` 和 `compare_documents`。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `HY3_API_KEY` | 是 | — | Hy3 API Key |
| `HY3_BASE_URL` | 否 | `https://tokenhub.tencentmaas.com/v1` | API 基础地址 |
| `HY3_MODEL` | 否 | `hy3` | 模型名称 |
| `TAVILY_API_KEY` | 否 | — | Tavily API Key（`web_search_and_answer` 工具需要） |

## 许可证

Apache License 2.0 — 与 [Hy3](https://github.com/Tencent-Hunyuan/Hy3) 相同
