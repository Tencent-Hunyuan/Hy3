# Trae 配置说明 / Trae Configuration Guide

Trae IDE supports the MCP (Model Context Protocol). This guide walks you through adding `hy3-data-analyst` as an MCP Server in Trae.

## 1. 打开 Trae MCP 设置 / Open Trae MCP Settings

1. Open Trae IDE.
2. Go to **Settings** → **MCP Servers** (or find the MCP configuration file location in Trae's settings).
3. Click **Add Server** or edit the MCP configuration JSON file directly.

## 2. 配置示例 / Configuration Example

Copy the template from [examples/trae.mcp.json](../../examples/trae.mcp.json) or use the JSON below.

Replace paths with your actual Python and project locations:

```json
{
  "mcpServers": {
    "hy3-data-analyst": {
      "command": "/absolute/path/to/your/python",
      "args": ["-m", "hy3_data_analyst.server"],
      "env": {
        "HY3_ENV_FILE": "/absolute/path/to/hy3-data-analyst/.env"
      }
    }
  }
}
```

### 路径替换说明 / Path Replacement Guide

- **`command`**: Absolute path to your Python interpreter.
  - Windows example: `C:/Users/YourName/AppData/Local/Python/pythoncore-3.14-64/python.exe`
  - Linux/macOS example: `/home/yourname/miniconda3/bin/python`
  - Find it: run `which python` (Linux/macOS) or `where python` (Windows)

- **`HY3_ENV_FILE`**: Absolute path to the `.env` file.
  - Copy `.env.example` to `.env` first, then fill in your `HY3_API_KEY`.
  - Example: `C:/Users/YourName/Desktop/hy3-data-analyst/.env`

### Quick Setup (One-liner env vars)

Instead of using `.env`, you can set environment variables directly in a terminal before launching Trae:

Windows (PowerShell):
```powershell
$env:HY3_API_KEY="sk-your-key"; $env:HY3_BASE_URL="https://tokenhub-intl.tencentmaas.com/v1"; $env:HY3_MODEL="hy3"
```

Linux/macOS:
```bash
export HY3_API_KEY="sk-your-key" && export HY3_BASE_URL="https://tokenhub-intl.tencentmaas.com/v1" && export HY3_MODEL="hy3"
```

## 3. 备选：使用 CLI 入口 / Alternative: CLI Entry Point

If you installed the package via `pip install -e .`, you can use:

```json
{
  "mcpServers": {
    "hy3-data-analyst": {
      "command": "hy3-data-analyst",
      "args": [],
      "env": {
        "HY3_ENV_FILE": "/absolute/path/to/hy3-data-analyst/.env"
      }
    }
  }
}
```

## 4. 验证 / Verification

After configuring and restarting Trae, try the following in the Trae chat:

```
请帮我列出当前目录下的数据文件 / Please list data files in the current directory.
```

If the Server starts successfully, Trae will call the `list_data_files` tool and display the results.

## 5. 典型工作流程 / Typical Workflow

A full analysis session in Trae might look like:

1. **List files**: "我有哪些数据文件？" → calls `list_data_files`
2. **Get stats**: "分析 sales.csv 的统计摘要" → calls `stats_summary`
3. **Plot chart**: "画出销量的折线图" → calls `plot_chart`, returns chart image
4. **Ask questions**: "哪个产品销售额最高？" → calls `ask_data`, returns AI analysis

## 6. 离线模式 / Offline Mode

`list_data_files`, `stats_summary`, and `plot_chart` work without `HY3_API_KEY`. Only `ask_data` requires it. If the key is missing, a clear error message is returned instead of crashing.
