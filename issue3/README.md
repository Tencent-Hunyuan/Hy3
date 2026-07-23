# Hy3 MCP Data Analysis Server

基于 Hy3 深度推理能力的 MCP 数据分析助手。读取 CSV/JSON 数据集，执行统计分析和可视化建议，支持网络搜索辅助分析。

## 场景

数据分析助手 — 加载数据集 → 统计预览 → Hy3 深度分析 → 图表方案推荐。

## 工具

| 名称 | 作用 |
|------|------|
| `load_dataset` | 读取 CSV/JSON 文件，输出结构摘要、统计和预览 |
| `web_search` | 网络搜索（Tavily 优先，自动回退 DuckDuckGo） |
| `hy3_analyze` | 用 Hy3 深度分析数据，输出结构化报告 |
| `hy3_chart_guide` | 用 Hy3 推荐图表方案并生成 Python 绘图代码 |

文件访问限制在 `HY3_MCP_ROOT` 目录内。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `HY3_API_KEY` | 是 | — | OpenRouter 或 TokenHub 的 Key |
| `HY3_BASE_URL` | 否 | `https://openrouter.ai/api/v1` | Hy3 API 端点；TokenHub 用 `https://tokenhub.tencentmaas.com/v1` |
| `HY3_MODEL` | 否 | `tencent/hy3:free` | 模型名；TokenHub 用 `hy3` |
| `TAVILY_API_KEY` | 否 | — | Tavily 搜索 Key，未设则回退 DuckDuckGo |
| `HY3_MCP_ROOT` | 否 | 进程当前目录 | 文件访问根目录 |

不要把 Key 写进仓库。复制 `.env.example` 为 `.env` 后填写（`server.py` 会自动加载）。

## 安装

```bash
cd issue3
pip install -r requirements.txt
```

## 快速验证

```bash
# 直接函数测试（不启动 stdio）
python smoke_test.py

# MCP 协议端到端测试
python mcp_client_check.py
```

## 启动（stdio）

由 MCP 客户端拉起进程即可。本机手动启动示例：

**Windows PowerShell:**
```powershell
$env:HY3_API_KEY = "your-key"
$env:HY3_BASE_URL = "https://openrouter.ai/api/v1"
$env:HY3_MODEL = "tencent/hy3:free"
$env:TAVILY_API_KEY = "your-tavily-key"
$env:HY3_MCP_ROOT = "C:\path\to\workspace"
python server.py
```

或使用一键启动脚本：
```powershell
.\run_mcp.ps1
```

## 客户端配置

### Cline (VS Code)

参见 [`examples/cline_mcp_settings.json`](./examples/cline_mcp_settings.json)，将 `PYTHON_EXE` / `SERVER_PY` / `SERVER_DIR` 替换为你的实际路径。

### Cursor

参见 [`examples/cursor-mcp.json`](./examples/cursor-mcp.json)，修改 `command` 为 Python 路径，`args` 为 `server.py` 路径，填入环境变量。

### CodeBuddy / WorkBuddy

参见 [`examples/codebuddy-mcp.json`](./examples/codebuddy-mcp.json)，项目级 MCP 配置示例。

CLI 添加命令：
```bash
codebuddy mcp add hy3-data-analysis -- python /path/to/server.py
```

### MCP Inspector

参见 [`examples/mcp-inspector.md`](./examples/mcp-inspector.md)。

## 使用示例

1. `load_dataset` 加载 `sample_data.csv` 查看数据预览和统计
2. `web_search` 搜索「2026年消费电子市场趋势」
3. `hy3_analyze` 传入数据集 + 问题「分析各区域的销售趋势和产品表现」
4. `hy3_chart_guide` 传入数据集 + 「用柱状图对比各产品类别的总销售额」

## 演示

参见 [`demo.md`](./demo.md)。

## 文件结构

```text
issue3/
├── server.py              # MCP Server 主入口
├── smoke_test.py          # 直接函数测试
├── mcp_client_check.py    # stdio 协议测试客户端
├── run_mcp.ps1            # Windows 启动脚本
├── sample_data.csv        # 示例销售数据
├── sample_data.json       # 示例用户数据
├── requirements.txt       # Python 依赖
├── pyproject.toml         # 项目元数据
├── .env.example           # 环境变量模板
├── README.md              # 本文件
├── demo.md                # 演示指引
└── examples/              # MCP 客户端配置示例
    ├── cline_mcp_settings.json
    ├── cursor-mcp.json
    ├── codebuddy-mcp.json
    └── mcp-inspector.md
```

## 说明

- 本地 **stdio** 模式，不要求公网部署
- Key 仅通过环境变量 / `.env` 传入，不硬编码
- 路径安全：文件访问限制在 `HY3_MCP_ROOT` 内
- 搜索双后端：Tavily (高质量) → DuckDuckGo (零配置回退)
