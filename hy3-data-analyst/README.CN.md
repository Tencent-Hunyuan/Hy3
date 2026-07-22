# hy3-data-analyst

基于 Python 的 MCP（Model Context Protocol）Server，用于本地数据文件的探索、统计、可视化和智能问答。使用 FastMCP、pandas、matplotlib 构建，集成 Hy3 API（通过 OpenRouter）。

[English](README.md)

## 功能

- **4 个 MCP 工具**：`list_data_files`、`stats_summary`、`plot_chart`、`ask_data`
- **多格式支持**：CSV、JSON、Excel（.xlsx/.xls）
- **AI 智能问答**：集成 Hy3（通过 OpenRouter 或腾讯云 LKE）进行数据分析
- **离线模式**：无需 API Key 即可使用文件列表、统计摘要、图表绘制
- **跨平台**：Windows、Linux、macOS
- **一键安装**：`pip install -e .`

## 已验证的 MCP 客户端

本 Server 已在以下 MCP 客户端中测试通过：

- **CodeBuddy** — 全部工具正常使用
- **Trae** — 全部工具正常使用
二者视频demo请见 [demo/](demo/) 目录。
配置文件详见 [examples/](examples/) 中预制的 MCP 配置文件。

## 环境要求

- Python 3.10+
- 依赖项详见 [requirements.txt](requirements.txt)

## 安装

```bash
cd hy3-data-analyst
pip install -e .
```

或通过 requirements.txt 安装：

```bash
pip install -r requirements.txt
pip install -e .
```

## 快速开始

### 1. 配置环境变量

**方式 A — .env 文件（推荐）：**

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

**方式 B — 命令行快速设置：**

Windows (PowerShell):
```powershell
$env:HY3_API_KEY="your-key"; $env:HY3_BASE_URL="https://openrouter.ai/api/v1"; $env:HY3_MODEL="tencent/hy3:free"
```

Linux/macOS:
```bash
export HY3_API_KEY="your-key" && export HY3_BASE_URL="https://openrouter.ai/api/v1" && export HY3_MODEL="tencent/hy3:free"
```

`.env` 文件格式：

```
HY3_API_KEY=sk-你的密钥
HY3_BASE_URL="https://tokenhub-intl.tencentmaas.com/v1"
HY3_MODEL="hy3"
HY3_MCP_ROOT=/path/to/your/data/workspace
```

| 环境变量 | 是否必需 | 默认值 | 说明 |
|----------|----------|--------|------|
| `HY3_API_KEY` | 仅 `ask_data` 需要 | — | Hy3/OpenRouter 的 API 密钥 |
| `HY3_BASE_URL` | 否 | `https://openrouter.ai/api/v1` | API 端点地址 |
| `HY3_MODEL` | 否 | `tencent/hy3:free` | 模型名称 |
| `HY3_MCP_ROOT` | 否 | 当前工作目录 | 文件访问的工作区根目录 |

### 2. 启动 Server

```bash
hy3-data-analyst
```

或直接用 Python 运行：

```bash
python -m hy3_data_analyst.server
```

### 3. 在 MCP 客户端中配置

详细的客户端配置指南见 [docs/clients/](docs/clients/)：
- [CodeBuddy](docs/clients/codebuddy.md)
- [WorkBuddy](docs/clients/workbuddy.md)
- [Trae](docs/clients/trae.md)

预制的配置模板（复制到客户端的 MCP 设置中）：
- [examples/codebuddy.mcp.json](examples/codebuddy.mcp.json)
- [examples/workbuddy.mcp.json](examples/workbuddy.mcp.json)
- [examples/trae.mcp.json](examples/trae.mcp.json)

每个模板使用了通用占位符 — 使用前请将 `/absolute/path/to/your/python` 和 `/absolute/path/to/hy3-data-analyst/.env` 替换为你的实际路径。配置示例：

```json
{
  "mcpServers": {
    "hy3-data-analyst": {
      "command": "/path/to/your/python",
      "args": ["-m", "hy3_data_analyst.server"],
      "env": {
        "HY3_ENV_FILE": "/path/to/hy3-data-analyst/.env"
      }
    }
  }
}
```

如果你已通过 `pip install -e .` 安装，也可以使用 CLI 入口：

```json
{
  "mcpServers": {
    "hy3-data-analyst": {
      "command": "hy3-data-analyst",
      "args": [],
      "env": {
        "HY3_ENV_FILE": "/path/to/hy3-data-analyst/.env"
      }
    }
  }
}
```

## 工具列表

| 工具 | 说明 |
|------|------|
| `list_data_files` | 列出目录下的 CSV/JSON/Excel 文件 |
| `stats_summary` | 生成统计摘要（形状、缺失值、数值统计、分类频数） |
| `plot_chart` | 绘制折线图/柱状图/散点图/直方图并保存为 PNG |
| `ask_data` | 基于数据内容回答自然语言问题（需要 Hy3 API Key） |

## 典型使用流程

与 AI 客户端对话的典型流程：

1. **列出文件**：对话输入“我有哪些数据文件？”
   → `list_data_files` 返回可用的数据文件列表

2. **获取统计**：对话输入“帮我分析 sales.csv 的统计摘要”
   → `stats_summary` 返回行数、缺失值、数值统计、分类频数

3. **绘制图表**：对话输入“画一个各区域销售额的柱状图”
   → `plot_chart` 生成 PNG 图片并返回路径和趋势分析

4. **智能问答**：对话输入“哪个区域的销售额最高？为什么？”
   → `ask_data` 调用 Hy3 进行 AI 分析并返回答案

## 使用示例

### 列出数据文件

```
工具: list_data_files
参数: {"path": "."}
→ 列出工作区中所有 .csv, .json, .xlsx, .xls 文件
```

### 获取统计摘要

```
工具: stats_summary
参数: {"file_path": "examples/sales.csv"}
→ 返回 Markdown 格式的统计摘要
```

### 绘制图表

```
工具: plot_chart
参数: {
  "file_path": "examples/sales.csv",
  "x_column": "日期",
  "y_column": "销量",
  "chart_type": "line",
  "title": "销售趋势"
}
→ 保存图表到 charts/ 目录，返回路径和趋势分析
```

### 智能问答

```
工具: ask_data
参数: {"file_path": "examples/sales.csv", "question": "哪个区域的销售额最高？"}
→ 调用 Hy3 API 分析数据并返回答案
```

## 离线模式

`list_data_files`、`stats_summary`、`plot_chart` 三个工具**不需要** API Key。仅 `ask_data` 需要 `HY3_API_KEY`。如果未设置，调用 `ask_data` 时会返回清晰的错误提示，不会崩溃。

## 测试

```bash
pip install -e ".[dev]"
pytest tests/
```

### 协议验证（无需 GUI）

```bash
python stdio_client.py
```

这会启动 Server 子进程并验证 MCP JSON-RPC 协议。

## 演示

参见 [demo/README.md](demo/README.md) 了解演示视频的内容说明（视频展示在多个 MCP 客户端中调用 4 个工具的完整流程）。

## 项目结构

```
hy3-data-analyst/
├── src/hy3_data_analyst/
│   ├── __init__.py
│   ├── server.py          # 主入口
│   ├── config.py          # 环境变量读取与验证
│   ├── data_utils.py      # 安全文件 I/O
│   ├── stats.py           # 统计摘要
│   ├── plot.py            # 图表绘制
│   ├── hy3_client.py      # Hy3 API 客户端
│   └── tools.py           # MCP 工具注册
├── tests/                 # pytest 测试
├── examples/              # 示例数据和 MCP 配置
├── docs/clients/          # 客户端配置说明
├── demo/                  # 演示视频占位
├── requirements.txt       # Python 依赖
├── pyproject.toml         # 包元数据与安装配置
├── stdio_client.py        # 协议测试客户端
├── .env.example           # 环境变量模板
└── .gitignore
```

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
