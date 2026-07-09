# Hy3 MCP Server

English | [中文](README_CN.md)

This directory provides a production-friendly stdio MCP server for Tencent Hunyuan Hy3. It connects MCP clients to the official Tencent TokenHub endpoint or any Hy3 OpenAI-compatible endpoint served by vLLM, SGLang, or another compatible gateway.

## Highlights

- **Official API compatible by default**: the default request format matches the official TokenHub OpenAI-compatible example.
- **Hy3 reasoning mode when needed**: local vLLM/SGLang deployments can enable `chat_template_kwargs.reasoning_effort` with `HY3_ENABLE_REASONING_EFFORT=true`.
- **More than the minimum tools**: six tools are included for chat, code review, repository Q&A, long-context summarization, endpoint health checks, and client config generation.
- **Client-ready setup**: examples are included for CodeBuddy / WorkBuddy, Codex, and Trae.
- **Developer-friendly**: one-command install scripts, `.env` support, typed parameters, and unit tests that validate config and Hy3 request payloads.
- **Safe defaults**: official TokenHub-compatible endpoint, placeholder API key, model name `hy3`, and stdio transport.

## Tools

| Tool | Purpose |
| --- | --- |
| `hy3_chat` | General Hy3 chat with optional system prompt and reasoning mode. |
| `hy3_code_review` | Reviews code or diffs with findings-first output. |
| `hy3_repo_qa` | Answers repository questions from supplied context without fabricating missing facts. |
| `hy3_long_context_summarize` | Summarizes logs, docs, transcripts, or long code context. |
| `hy3_health_check` | Sends a tiny request to confirm the Hy3 endpoint is reachable. |
| `hy3_client_config` | Generates a ready-to-paste MCP configuration snippet. |

## Requirements

- Python 3.10+
- A running Hy3 OpenAI-compatible API endpoint, such as `https://tokenhub.tencentmaas.com/v1`
- `uv` or `pip`

For the official API, set your TokenHub API key in `HY3_API_KEY`. For local inference, start Hy3 first; the main Hy3 README shows vLLM and SGLang commands that serve `hy3` at `http://127.0.0.1:8000/v1`.

## Quick Start

```bash
cd MCP_Server
python -m pip install -e .
cp .env.example .env
```

Edit `.env` if your endpoint is different:

```bash
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_API_KEY=your_api_key_here
HY3_MODEL=hy3
HY3_DEFAULT_REASONING_EFFORT=no_think
HY3_ENABLE_REASONING_EFFORT=false
HY3_TIMEOUT_SECONDS=120
```

Run the server over stdio:

```bash
hy3-mcp-server
```

With `uv`, clients can also run it without manual activation:

```bash
uv --directory /absolute/path/to/Hy3/MCP_Server run hy3-mcp-server
```

## One-command Install

Linux / macOS:

```bash
bash scripts/install.sh
```

Windows PowerShell:

```powershell
.\scripts\install.ps1
```

## MCP Client Configuration

Replace `/absolute/path/to/Hy3/MCP_Server` with your local absolute path.

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

Add the server to your Codex MCP configuration:

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

## Suggested Usage

- Use `hy3_chat` for general prompts.
- Use `hy3_code_review` with `reasoning_effort="high"` for pull request review, security checks, and complex bug hunts.
- Use `hy3_repo_qa` after collecting relevant file snippets with your MCP client.
- Use `hy3_long_context_summarize` for logs, design docs, and long conversations.
- Run `hy3_health_check` first when debugging endpoint or credential issues.

## Testing

```bash
cd MCP_Server
python -m pip install -e ".[dev]"
pytest
```

The tests do not require a live Hy3 endpoint. They validate environment loading and the OpenAI-compatible request payload, including Hy3 reasoning mode.

## Troubleshooting

- `Connection refused`: start vLLM or SGLang and verify `HY3_BASE_URL`.
- `401` or authentication errors: set `HY3_API_KEY` to the gateway key. Local vLLM/SGLang often uses `EMPTY`.
- Official TokenHub calls should keep `HY3_ENABLE_REASONING_EFFORT=false`; local vLLM/SGLang can set it to `true`.
- Tool calls are slow: increase `HY3_TIMEOUT_SECONDS`, reduce `max_tokens`, or use `reasoning_effort="no_think"` for simple requests.
- Client cannot find `uv`: replace `"command": "uv"` with the absolute path to `uv`, or install the package and use `"command": "hy3-mcp-server"`.

## License

Apache-2.0, aligned with the Hy3 repository license.
