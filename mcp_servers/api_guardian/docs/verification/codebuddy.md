# CodeBuddy verification

- Verified at: `2026-07-22T16:26:05+08:00`
- Client: CodeBuddy Code CLI `2.125.0`
- Transport: local stdio
- Project configuration: repository-root `.mcp.json`
- Server health: `Connected`
- Permission scope: only `audit_openapi` through CodeBuddy's deferred MCP executor

## Tool call

CodeBuddy was instructed to call `audit_openapi` with:

- `spec_path`: `examples/insecure-api.yaml`
- `focus`: `security`

Sanitized client result:

```text
tool: audit_openapi
operation_count: 2
local_findings: 8
hy3_analysis_non_empty: true
```

The validation used a project-level MCP configuration with the API key supplied only through the
ignored local environment block. No credential or full provider response is stored in this file.
