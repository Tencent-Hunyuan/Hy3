# WorkBuddy 接入说明

## 项目级 MCP 配置示例

在 WorkBuddy 的项目级 MCP 配置（`.workbuddy/mcp.json` 或客户端设置）中加入：

```json
{
  "mcpServers": {
    "hy3-data-analysis": {
      "command": "python",
      "args": ["-m", "hy3_mcp_server.server"],
      "cwd": "your_real_path",
      "env": {
        "PYTHONPATH": "src",
        "PYTHONUTF8": "1",
        "HY3_API_KEY": "在此填入你的_Hy3_API_Key",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3",
        "LLM_REASONING_EFFORT": "high"
      }
    }
  }
}
```

## CLI 添加命令（参考）

```bash
workbuddy mcp add hy3-data-analysis \
  --command python \
  --args "-m hy3_mcp_server.server" \
  --cwd "your_real_path\hy3_mcp_server" \
  --env PYTHONPATH=src \
  --env PYTHONUTF8=1 \
  --env HY3_API_KEY=在此填入你的_Hy3_API_Key \
  --env HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1 \
  --env HY3_MODEL=hy3 \
  --env LLM_REASONING_EFFORT=high
```

