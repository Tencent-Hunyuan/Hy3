# Hy3 MCP Server

This example implements a local stdio MCP Server powered by Hy3. It exposes three tools for common agent workflows:

- `hy3_code_review`: review a diff and return prioritized findings.
- `hy3_document_qa`: answer a question from supplied documents with citations.
- `hy3_data_insight`: inspect CSV or JSON data and produce an analysis plan plus takeaways.

Hy3 is used as the reasoning engine through its OpenAI-compatible chat completions API. API keys are never hard-coded; configure them through environment variables.

## Install

```bash
cd examples/hy3-mcp-server
pip install -e .
```

## Environment

```bash
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
```

For local smoke tests without a running Hy3 endpoint, set:

```bash
export HY3_MOCK="1"
```

Mock mode is only for demos and tests. Production use should point `HY3_BASE_URL` at a real Hy3-compatible endpoint.

## Run

```bash
hy3-mcp-server
```

The server runs over stdio and is intended to be started by an MCP client.

## CodeBuddy / WorkBuddy Configuration

Project-level MCP configuration example:

```json
{
  "mcpServers": {
    "hy3-mcp-server": {
      "command": "hy3-mcp-server",
      "env": {
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_API_KEY": "EMPTY",
        "HY3_MODEL": "hy3"
      }
    }
  }
}
```

One runnable tool-call demo:

```text
Use the hy3_code_review tool with this diff and focus on regressions:

diff --git a/app.py b/app.py
+ user_input = request.args["q"]
+ cursor.execute("select * from docs where title = '%s'" % user_input)
```

## Cursor Configuration

Add this server to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "hy3-mcp-server": {
      "command": "python",
      "args": ["-m", "hy3_mcp_server.server"],
      "env": {
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_API_KEY": "EMPTY",
        "HY3_MODEL": "hy3"
      }
    }
  }
}
```

## Demo Flows

Demo 1: Code review.

```bash
HY3_MOCK=1 python -m hy3_mcp_server.demo code-review
```

Demo 2: Document QA.

```bash
HY3_MOCK=1 python -m hy3_mcp_server.demo document-qa
```

These demos exercise the same tool functions that the MCP server exposes. Replace `HY3_MOCK=1` with real Hy3 environment variables for live model calls.

## Development

```bash
python -m pytest
python -m compileall src
```

## Notes For The Rhino-Bird Issue

- The implementation uses the MCP Python SDK and local stdio mode.
- It exposes three tools with names, schemas, and docstrings.
- Core reasoning is delegated to Hy3 through the OpenAI-compatible API.
- The package can be installed with `pip install -e .` or built as a wheel.
- CodeBuddy/WorkBuddy and Cursor configuration examples are included above.
