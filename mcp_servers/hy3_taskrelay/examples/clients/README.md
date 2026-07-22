# Client configuration status

`codebuddy.mcp.json`, `codex.config.toml`, and `cursor.mcp.json` are project-level examples. They
assume they are copied into the root of a Hy3 checkout and use only relative paths. None contains a
credential value.

CodeBuddy Code 2.124.0 and Codex CLI 0.144.6 were validated with real MCP calls over the same public
synthetic fixture. Their sanitized records and schema-valid outputs are in
[`../../docs/clients`](../../docs/clients) and
[`../../docs/client_artifacts`](../../docs/client_artifacts). Cursor remains an optional,
format-checked third-client example and was not used for the two-client gate.

## Reproduce CodeBuddy headless discovery

Review `.mcp.json` before approving it. Project MCP servers need first-connection approval.
Headless mode cannot show that UI, so this command explicitly enables only `hy3-taskrelay`, ignores
unrelated MCP configurations, exposes the required deferred tool, and allows only that exact tool:

```powershell
$prompt = 'Call taskrelay_create_checkpoint once with the public synthetic fixture and return its structured result.'
codebuddy --model hy3 --output-format text `
  --strict-mcp-config --mcp-config .mcp.json `
  --settings '{"enabledMcpjsonServers":["hy3-taskrelay"]}' `
  --tools 'NoDefer(mcp__hy3-taskrelay__taskrelay_create_checkpoint)' `
  --allowedTools 'mcp__hy3-taskrelay__taskrelay_create_checkpoint' `
  -y -p $prompt
```

`-y` skips interactive permission prompts; do not use it without the strict MCP config and exact
tool allowlist above.

## Reproduce Codex discovery

Codex loads `.codex/config.toml` only for a trusted project. Review the checkout and configuration,
trust only that reviewed checkout, and never work around project trust by putting `HY3_API_KEY` in
TOML.

```bash
codex mcp list
codex
```

Verify that `hy3-taskrelay` exposes exactly three tools. The recorded validation used an ephemeral,
read-only Codex run with explicit MCP-only configuration.
