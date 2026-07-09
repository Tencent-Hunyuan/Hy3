# Hy3 MCP Server

[English](README.md) | 中文

本目录提供一套面向开发者的 stdio MCP Server，用于把 CodeBuddy / WorkBuddy、Codex、Trae 等 MCP 客户端连接到腾讯混元 Hy3 的 OpenAI 兼容推理接口。接口可以是官方 TokenHub，也可以是 vLLM、SGLang 或其他兼容网关。

## 方案亮点

- **默认兼容官方 API**：默认请求格式与 TokenHub 官方 OpenAI 兼容示例保持一致。
- **需要时启用 Hy3 reasoning mode**：本地 vLLM/SGLang 部署可通过 `HY3_ENABLE_REASONING_EFFORT=true` 透传 `chat_template_kwargs.reasoning_effort`。
- **工具数量和场景都超过基础要求**：内置 6 个工具，覆盖通用对话、代码审查、仓库问答、长上下文总结、服务健康检查和客户端配置生成。
- **开箱即接 MCP 客户端**：README 直接给出 CodeBuddy / WorkBuddy、Codex、Trae 配置。
- **开发体验友好**：提供一键安装脚本、`.env` 自动读取、参数类型约束，以及无需真实 Hy3 服务即可运行的单元测试。
- **默认配置安全简单**：默认连接官方 TokenHub 兼容接口，API key 使用占位值，模型名 `hy3`，传输协议为 stdio。

## 工具列表

| 工具 | 用途 |
| --- | --- |
| `hy3_chat` | 通用 Hy3 对话，支持 system prompt 和 reasoning mode。 |
| `hy3_code_review` | 审查代码或 diff，优先输出可执行的问题发现。 |
| `hy3_repo_qa` | 基于用户提供的上下文回答仓库问题，避免编造缺失信息。 |
| `hy3_long_context_summarize` | 总结日志、文档、会议记录或长代码上下文。 |
| `hy3_health_check` | 发送一个轻量请求，确认 Hy3 接口可访问。 |
| `hy3_client_config` | 生成可直接粘贴的 MCP 客户端配置片段。 |

## 环境要求

- Python 3.10+
- 一个正在运行的 Hy3 OpenAI 兼容 API 服务，例如 `https://tokenhub.tencentmaas.com/v1`
- `uv` 或 `pip`

如果使用官方 API，请在 `HY3_API_KEY` 中设置 TokenHub API key。如果使用本地推理，请先启动 Hy3 服务；主仓库 README 中提供了 vLLM 和 SGLang 示例，默认可将 `hy3` 服务暴露在 `http://127.0.0.1:8000/v1`。

## 快速开始

```bash
cd MCP_Server
python -m pip install -e .
cp .env.example .env
```

如果你的服务地址不同，请修改 `.env`：

```bash
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_API_KEY=your_api_key_here
HY3_MODEL=hy3
HY3_DEFAULT_REASONING_EFFORT=no_think
HY3_ENABLE_REASONING_EFFORT=false
HY3_TIMEOUT_SECONDS=120
```

以 stdio 方式运行服务：

```bash
hy3-mcp-server
```

也可以让 MCP 客户端通过 `uv` 直接启动：

```bash
uv --directory /absolute/path/to/Hy3/MCP_Server run hy3-mcp-server
```

## 一键安装

Linux / macOS:

```bash
bash scripts/install.sh
```

Windows PowerShell:

```powershell
.\scripts\install.ps1
```

## MCP 客户端配置

请将 `/absolute/path/to/Hy3/MCP_Server` 替换为你本地的绝对路径。

### CodeBuddy / WorkBuddy

```json
{
  "mcpServers": {
    "hy3": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/Hy3/MCP_Server", "run", "hy3-mcp-server"],
      "env": {
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_API_KEY": "EMPTY",
        "HY3_MODEL": "hy3",
        "HY3_DEFAULT_REASONING_EFFORT": "no_think",
        "HY3_ENABLE_REASONING_EFFORT": "true"
      }
    }
  }
}
```

### Codex

在 Codex 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "hy3": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/Hy3/MCP_Server", "run", "hy3-mcp-server"],
      "env": {
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_API_KEY": "your_api_key_here",
        "HY3_MODEL": "hy3",
        "HY3_DEFAULT_REASONING_EFFORT": "high",
        "HY3_ENABLE_REASONING_EFFORT": "false"
      }
    }
  }
}
```

### Trae

```json
{
  "mcpServers": {
    "hy3": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/Hy3/MCP_Server", "run", "hy3-mcp-server"],
      "env": {
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_API_KEY": "your_api_key_here",
        "HY3_MODEL": "hy3",
        "HY3_DEFAULT_REASONING_EFFORT": "no_think",
        "HY3_ENABLE_REASONING_EFFORT": "false"
      }
    }
  }
}
```

## 推荐用法

- `hy3_chat`：通用问答和轻量生成。
- `hy3_code_review`：PR 审查、安全检查、复杂 bug 分析，建议使用 `reasoning_effort="high"`。
- `hy3_repo_qa`：先由客户端收集相关文件片段，再让 Hy3 基于上下文回答。
- `hy3_long_context_summarize`：处理日志、设计文档和长对话。
- `hy3_health_check`：排查服务地址、模型名或鉴权问题时优先运行。

## 测试

```bash
cd MCP_Server
python -m pip install -e ".[dev]"
pytest
```

测试不依赖真实 Hy3 服务，会验证环境变量读取和 OpenAI 兼容请求参数，包括 Hy3 的 reasoning mode。

## 常见问题

- `Connection refused`：请先启动 vLLM 或 SGLang，并检查 `HY3_BASE_URL`。
- `401` 或鉴权失败：请设置网关需要的 `HY3_API_KEY`。本地 vLLM/SGLang 通常可使用 `EMPTY`。
- 官方 TokenHub 调用建议保持 `HY3_ENABLE_REASONING_EFFORT=false`；本地 vLLM/SGLang 可设为 `true`。
- 工具调用较慢：增大 `HY3_TIMEOUT_SECONDS`，减少 `max_tokens`，简单任务使用 `reasoning_effort="no_think"`。
- 客户端找不到 `uv`：将 `"command": "uv"` 替换为 `uv` 的绝对路径，或安装本包后直接使用 `"command": "hy3-mcp-server"`。

## 许可证

Apache-2.0，与 Hy3 主仓库许可证保持一致。
