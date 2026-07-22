# CodeBuddy 配置说明 / CodeBuddy Configuration Guide

## 1. 复制配置模板

将 [examples/codebuddy.mcp.json](../../examples/codebuddy.mcp.json) 的内容复制到 CodeBuddy 的 MCP 配置文件（通常是 `~/.codebuddy/mcp.json` 或项目下的 `.codebuddy/mcp.json`）。

## 2. 修改路径

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

将以下两个路径替换为你本机的实际路径：

- **`command`**: Python 解释器的绝对路径。
  - Windows 示例: `C:/Users/YourName/miniconda3/python.exe`
  - Linux/macOS 示例: `/home/yourname/miniconda3/envs/llms/bin/python`
  - 查找方式: 在终端运行 `which python` (Linux/macOS) 或 `where python` (Windows)

- **`HY3_ENV_FILE`**: `.env` 文件的绝对路径。
  - 本项目已提供 `.env.example`，请复制为 `.env` 并填入你的 API Key。

## 3. 可选：使用命令行入口

如果你已通过 `pip install -e .` 安装了本包，也可以简化为：

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

但为兼容性考虑，推荐使用 Python 直接调用模块的方式（上一种）。

## 4. 验证

重启 CodeBuddy 后，在对话中尝试：

```
请帮我列出当前目录下的数据文件
```

如果 Server 正常启动，CodeBuddy 会调用 `list_data_files` 工具并返回结果。

## 5. 离线模式

即使没有设置 `HY3_API_KEY`，以下工具也可以正常使用：
- `list_data_files` — 列出数据文件
- `stats_summary` — 生成统计摘要
- `plot_chart` — 绘制图表

只有 `ask_data` 需要 API Key。
