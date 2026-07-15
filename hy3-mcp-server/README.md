# Hy3 MCP Server

An MCP (Model Context Protocol) server that exposes Hy3 AI capabilities as plug-and-play tools for any MCP-compatible AI client (CodeBuddy, WorkBuddy, Cursor, Cline, etc.).

## Tools

| Tool | Description |
|---|---|
| `ask_hy3` | Chat directly with Hy3. Supports reasoning modes: `no_think` (fast), `low` (brief reasoning), `high` (deep chain-of-thought). |
| `search_and_analyze` | Web search (DuckDuckGo) + Hy3 analysis for comprehensive answers. |
| `file_analyze` | Read a local file and ask Hy3 to analyze, summarize, or answer questions about its content. |

## Quick Start

### Prerequisites

- Python >= 3.10

### Install & Run

```bash
cd hy3-mcp-server
pip install -e .
HY3_API_KEY=sk-xxx hy3-mcp-server
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
cd hy3-mcp-server
uv sync
HY3_API_KEY=sk-xxx uv run hy3-mcp-server
```

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `HY3_API_KEY` | Yes | - | Your Hy3 API key |
| `HY3_BASE_URL` | No | `https://tokenhub-intl.tencentmaas.com/v1` | Hy3 API base URL |
| `HY3_MODEL_NAME` | No | `hy3` | Model name |

## Client Configuration

### CodeBuddy (`.mcp.json`)
```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "hy3-mcp-server",
      "env": { "HY3_API_KEY": "${HY3_API_KEY}" }
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "hy3-mcp-server",
      "env": { "HY3_API_KEY": "${HY3_API_KEY}" }
    }
  }
}
```

### Cline (`cline_docs/mcp_settings.json`)
```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "hy3-mcp-server",
      "env": { "HY3_API_KEY": "${HY3_API_KEY}" }
    }
  }
}
```

## Testing with MCP Inspector

```bash
HY3_API_KEY=sk-xxx npx @modelcontextprotocol/inspector hy3-mcp-server
```

## License

Apache-2.0
