# TRAE setup

The documented desktop baseline is TRAE SOLO CN 0.1.25 / VS Code 1.107.1. Use the project file
`.trae/mcp.json` and enable the `trae.mcp.enableWorkspaceMcp` setting. The checked-in
[TRAE example](../../examples/clients/trae.mcp.json) documents only `${workspaceFolder}`
interpolation; no other TRAE-specific variable syntax is assumed.

1. Copy the example to `.trae/mcp.json` in the repository root.
2. Keep `HY3_API_KEY` out of the JSON. Set it in PowerShell, then launch TRAE from that same shell:

   ```powershell
   $env:HY3_API_KEY = "<YOUR_ROTATED_HY3_KEY>"
   $env:HY3_BASE_URL = "https://openrouter.ai/api/v1"
   $env:HY3_MODEL = "tencent/hy3:free"
   $env:HY3_ENDPOINT_PROFILE = "openrouter"
   $env:HY3_REASONING_EFFORT = "none"
   trae .
   ```

3. Trust the workspace and confirm `hy3-knowledge` is connected before invoking a tool.

The MCP child inherits variables from the TRAE process only when TRAE itself was launched from the
secret-bearing PowerShell. If startup fails, open **Output → MCP Server Host** and check the resolved
`uvx` command, `${workspaceFolder}` paths, and missing-variable errors. Never paste the key into
diagnostic output or a tracked file.

[Back to the English README](../../README.md) · [返回中文 README](../../README_CN.md)
