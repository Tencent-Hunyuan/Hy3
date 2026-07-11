# Cursor

## Configure

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per project) and merge
in the config from [`examples/clients/cursor.json`](../../examples/clients/cursor.json):

```json
{
  "mcpServers": {
    "hy3-code-review": {
      "command": "uvx",
      "args": ["hy3-code-review-mcp"],
      "env": {
        "HY3_BASE_URL": "https://openrouter.ai/api/v1",
        "HY3_API_KEY": "<your-openrouter-api-key>",
        "HY3_MODEL": "tencent/hy3:free"
      }
    }
  }
}
```

Open **Settings → MCP** and confirm `hy3-code-review` is enabled with a green
status. On Windows, if the server fails with `ENOENT`, use the absolute path to
`uvx.exe` in `command` (see the note in [cline.md](cline.md)).

## Verify

In Cursor chat (Agent mode):

```
Use hy3-code-review review_diff on this diff (reasoning_effort=low): <paste a diff>
```
