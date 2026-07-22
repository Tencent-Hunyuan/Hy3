# Verification evidence

This directory is reserved for sanitized, reproducible evidence gathered from real Hy3 and MCP
client runs. Never place an API key, Authorization header, user profile path, account identifier,
or private API contract here.

The pull request evidence includes:

- `hy3-live-smoke.json`: all three tools called through a real MCP stdio session and TokenHub Hy3.
- `codebuddy.md`: CodeBuddy version, connection status, tool call, and sanitized result summary.
- `cursor.md`: Cursor version, native MCP connection, direct tool call, and sanitized result.
- `assets/cursor-native-mcp-demo.gif`: recorded native Cursor MCP workflow.

Run the live smoke test from the package directory:

```powershell
$env:HY3_API_KEY = "your-key"
python scripts/live_smoke.py
```

The script prints only tool names, result counts, output lengths, model ID, token usage, and a
Python syntax-validation flag for generated pytest source. It does not print the key or full
provider responses.
