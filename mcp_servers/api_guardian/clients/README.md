# MCP client templates

These files are safe-to-commit examples. They contain placeholders, never real credentials.

| Client | Example | Local destination |
| --- | --- | --- |
| CodeBuddy | `codebuddy.project.example.json` | `<project>/.mcp.json` |
| Cursor | `cursor.project.example.json` | `<project>/.cursor/mcp.json` |

After copying a template locally:

1. Set `command` to the absolute Python executable where `hy3-api-guardian` is installed.
2. Replace the `HY3_API_KEY` placeholder locally.
3. Set `HY3_ALLOWED_ROOT` to the project directory containing the OpenAPI files.
4. Keep the local config out of Git.

The server starts with `python -m hy3_api_guardian` over stdio.
