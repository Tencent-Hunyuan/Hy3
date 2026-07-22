# Cursor verification

- Recorded at: `2026-07-22T16:44:42+08:00`
- Verified at: `2026-07-22T16:49:24+08:00`
- Client: Cursor `3.12.17`
- Transport: native project-level stdio MCP
- Configuration: `.cursor/mcp.json`
- Connection evidence: Cursor listed the server's three OpenAPI tools before the call
- File side effects: none

## Native tool call

Cursor Agent directly called `detect_breaking_changes` with:

- `old_spec_path`: `examples/petstore-v1.yaml`
- `new_spec_path`: `examples/petstore-v2-breaking.yaml`
- `include_compatible`: `true`

Sanitized result shown by Cursor:

```text
tool: detect_breaking_changes
breaking_count: 5
warning_count: 1
compatible_count: 1
hy3_migration_analysis_non_empty: true
```

## Demo GIF

![Cursor native MCP demo](assets/cursor-native-mcp-demo.gif)

- Duration: `18.9s` (source wait time accelerated 2x)
- Resolution: `1000x920`
- Size: `4,747,670 bytes`
- SHA-256: `e444fd5d14565a66d2a3604bdd736741dd52d4d456ad4bc555b09077a861cd60`

The GIF shows Cursor listing the native MCP tools, directly invoking one tool, and rendering the
structured result. It contains no API key, Authorization header, or private API specification.
