# CodeBuddy / WorkBuddy

Both clients read a standard `.mcp.json`.

## Configure

Create `.mcp.json` in your project root, using
[`examples/clients/codebuddy.mcp.json`](../../examples/clients/codebuddy.mcp.json)
or [`examples/clients/workbuddy.mcp.json`](../../examples/clients/workbuddy.mcp.json):

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

Reload the client. The `hy3-code-review` server should expose `review_diff`,
`analyze_file`, and `git_diff_review`.

## Verify

```
Use hy3-code-review review_diff on this diff (reasoning_effort=low): <paste a diff>
```
