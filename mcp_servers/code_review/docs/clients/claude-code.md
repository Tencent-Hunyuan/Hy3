# Claude Code

Verified with Claude Code (CLI).

## Option A — one command

```bash
claude mcp add --scope user hy3-code-review uvx hy3-code-review-mcp \
  --env HY3_BASE_URL=https://openrouter.ai/api/v1 \
  --env HY3_API_KEY=<your-openrouter-api-key> \
  --env HY3_MODEL=tencent/hy3:free
```

## Option B — edit `~/.claude.json`

Merge the config from
[`examples/clients/claude-code.json`](../../examples/clients/claude-code.json)
into the `mcpServers` object:

```json
{
  "hy3-code-review": {
    "type": "stdio",
    "command": "uvx",
    "args": ["hy3-code-review-mcp"],
    "env": {
      "HY3_BASE_URL": "https://openrouter.ai/api/v1",
      "HY3_API_KEY": "<your-openrouter-api-key>",
      "HY3_MODEL": "tencent/hy3:free"
    }
  }
}
```

Restart Claude Code. Run `/mcp` to confirm `hy3-code-review` is connected and
exposes `review_diff`, `analyze_file`, `git_diff_review`.

## Verify

```
Use hy3-code-review review_diff on this diff (reasoning_effort=low): <paste a diff>
```
