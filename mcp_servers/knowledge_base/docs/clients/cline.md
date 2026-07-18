# Cline setup

Verified on 2026-07-11 with Cline CLI `3.0.39` (`cline --version`). The installed
`cline mcp add --help` exposes `--transport`, `--header`, `--yes`, and `--json`; this version
does not expose `--scope project`. Project isolation is therefore provided by
`CLINE_MCP_SETTINGS_PATH`, not by a scope flag.

Run these commands from the Hy3 repository root. The MCP subprocess inherits the launching
shell environment, so keep the rotated key only in this PowerShell process:

```powershell
$env:CLINE_MCP_SETTINGS_PATH = Join-Path $PWD ".cline\cline_mcp_settings.json"
$packageDir = (Resolve-Path ".\mcp_servers\knowledge_base").Path
$env:HY3_API_KEY = "<YOUR_ROTATED_HY3_KEY>"
$env:HY3_BASE_URL = "https://openrouter.ai/api/v1"
$env:HY3_MODEL = "tencent/hy3:free"
$env:HY3_ENDPOINT_PROFILE = "openrouter"
$env:HY3_REASONING_EFFORT = "none"
$env:HY3_KB_ROOTS = (Resolve-Path ".\mcp_servers\knowledge_base\examples\knowledge_base").Path
cline mcp add hy3-knowledge --yes -- uvx --from $packageDir hy3-knowledge-mcp
cline config mcp --json
cline
```

The checked-in [Cline JSON example](../../examples/clients/cline.json) uses stdio transport and the
single repository-root placeholder `C:\path\to\Hy3` because Cline settings may live outside the
repository. Its package and working-directory paths are derived from that root; replace it with one
real absolute path. Do not put a real key in the JSON.

If the server does not connect, run `cline config mcp --json`, confirm the command path, and start
Cline again from the same PowerShell. A shell started before the environment variables were set
cannot pass those values to its child process.

[Back to the English README](../../README.md) · [返回中文 README](../../README_CN.md)
