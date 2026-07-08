# Cursor MCP Configuration

Cursor uses the same stdio MCP server. Use `examples/cursor.mcp.json`.

## Install

```bash
pip install ./mcp_servers/deep_research
```

## Configure

Add the server to `~/.cursor/mcp.json` (or the project-level `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "hy3-research": {
      "command": "/absolute/path/to/conda/envs/llms/bin/python",
      "args": ["-m", "hy3_research_mcp.server"],
      "env": {
        "HY3_ENV_FILE": "/absolute/path/to/Hy3/.env"
      }
    }
  }
}
```

## Tool Call Demo

Prompt:

```text
Use the hy3-research MCP server.
Call research_question with:
- question: "What are Hy3's recommended vLLM serving flags for MTP?"
- searches: "Hy3 vLLM MTP speculative, vLLM hy_v3 tool parser"
- depth: "balanced"
- read_top_pages: 1
```

Cursor may also call `web_search_tool` and `read_url_tool` directly to gather
sources before synthesis.