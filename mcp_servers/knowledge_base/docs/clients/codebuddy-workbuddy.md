# CodeBuddy and WorkBuddy setup

## CodeBuddy

On the 2026-07-11 validation host, `Get-Command codebuddy` returned no executable
(`CODEBUDDY_AVAILABLE=False`). Therefore the sequence below could not be executed on that host and
is not claimed as version-verified. It is the project's required project-scope integration sequence;
run `codebuddy --version` and `codebuddy mcp add --help` on the installed client before relying on it.

From the Hy3 repository root, define the complete child-process environment before adding the stdio
server. The key is supplied by the launching shell and is never stored in the project configuration:

```powershell
$packageDir = (Resolve-Path ".\mcp_servers\knowledge_base").Path
$env:HY3_MCP_SOURCE = $packageDir
$env:HY3_API_KEY = "<YOUR_ROTATED_HY3_KEY>"
$env:HY3_BASE_URL = "https://openrouter.ai/api/v1"
$env:HY3_MODEL = "tencent/hy3:free"
$env:HY3_ENDPOINT_PROFILE = "openrouter"
$env:HY3_REASONING_EFFORT = "none"
$env:HY3_KB_ROOTS = (Resolve-Path ".\mcp_servers\knowledge_base\examples\knowledge_base").Path
codebuddy mcp add --scope project hy3-knowledge -- uvx --from $packageDir hy3-knowledge-mcp
codebuddy mcp list
codebuddy mcp get hy3-knowledge
```

The `mcp add`, `mcp list`, and `mcp get` commands do not persist the current shell's `HY3_*`
environment. Keep the same PowerShell open for the actual client session. From that PowerShell, use
the installed CodeBuddy version's supported launch method; first confirm it with `codebuddy --help`
and the product documentation. Because CodeBuddy was unavailable on the validation host, this guide
does not invent an exact client-start command.

For declarative setup, copy the [CodeBuddy example](../../examples/clients/codebuddy.mcp.json) to
the project's `.mcp.json`. The example uses only plain `${VAR}` expansion; it does not assume an
unverified default-value expression. Explicitly define `HY3_MCP_SOURCE`, `HY3_API_KEY`,
`HY3_BASE_URL`, `HY3_MODEL`, `HY3_ENDPOINT_PROFILE`, `HY3_REASONING_EFFORT`, and `HY3_KB_ROOTS` in
the launching environment. Start the actual client from that same PowerShell where all variables are defined;
`.mcp.json` references the environment but does not persist its values. Keep a real key out of the
file and version control.

## WorkBuddy

Copy the [WorkBuddy example](../../examples/clients/workbuddy.mcp.json) to
`.workbuddy/mcp.json` and replace the `C:\path\to\Hy3` repository-root placeholder. The tracked
template intentionally contains no API-key field, so it cannot override a key inherited from the
launching environment. Supply the key through that environment or WorkBuddy's local, untracked
secret setting in **Plugins → MCP Servers → Configure MCP**, then import, enable, and inspect the
server. WorkBuddy setup is UI-driven here; this guide intentionally does not claim a WorkBuddy CLI
interface.

For either client, confirm the working directory, `uvx` availability, allowed root, and endpoint
profile if the server fails to start. Rotate any credential accidentally placed in a screenshot,
log, or tracked configuration.

[Back to the English README](../../README.md) · [返回中文 README](../../README_CN.md)
