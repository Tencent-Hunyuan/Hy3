# Hy3 MCP Server

[中文文档](README_CN.md)

An MCP (Model Context Protocol) server that exposes Hy3 LLM capabilities
to any MCP-compatible client (Claude Code, CodeBuddy, Cursor, Cline, etc.).

## Tools

| Tool | Description |
|------|-------------|
| `hy3_chat` | General-purpose chat with Hy3 |
| `hy3_code` | Code generation, explanation, review, debugging |
| `hy3_analyze` | Text analysis: summarize, extract, classify, sentiment |

## Quick Start

```bash
pip install -r requirements.txt
export HY3_BASE_URL=http://127.0.0.1:8000/v1
export HY3_API_KEY=EMPTY
```

Then register in your MCP client's `settings.json`:

```json
{
  "mcpServers": {
    "hy3": {
      "command": "python",
      "args": ["/path/to/examples/mcp-server/server.py"],
      "env": {
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_API_KEY": "EMPTY"
      }
    }
  }
}
```

## Requirements

- Python 3.10+
- A running Hy3 API endpoint (vLLM or SGLang)
- `openai` and `mcp` packages
