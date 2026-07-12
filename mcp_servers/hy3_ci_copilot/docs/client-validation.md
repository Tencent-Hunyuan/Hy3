# MCP Client Validation

Validation date: 2026-07-12

Both client runs used the checked-in project configuration from the package directory and a
private, Git-ignored `.env` file. No API key is stored in this document or the demo.

## Live Hy3 Endpoint Check

A live OpenRouter preflight used the configured alias `tencent/hy3` and returned:

- Resolved model: `tencent/hy3-20260706`
- Provider: `GMICloud`
- Response marker: `HY3_LIVE_OK`

The MCP tools use the same OpenAI-compatible endpoint configuration. The model used by the host
client to choose a tool is separate from the Hy3 model used inside this server.

## CodeBuddy CN 1.106.1

CodeBuddy loaded [the project configuration](../.mcp.json), connected to `hy3-ci-copilot`, and
discovered all four tools. The successful demo used CodeBuddy's Hy3 host model and called
`diagnose_ci_failure` exactly once with:

```json
{
  "log_path": "logs/failed.log",
  "repository_path": "examples/demo_repository",
  "output_language": "zh-CN",
  "reasoning_effort": "low"
}
```

Observed result:

- MCP status: `running successfully`
- Response marker: `HY3_CODEBUDDY_CLIENT_OK`
- Primary cause: `legacy-release-tool==0.8.0` imports the Python 3.12-removed `distutils` module
- Verification command: `python3.12 -c "import distutils"`

![CodeBuddy calling Hy3 CI Copilot](demo.gif)

## Claude Code 2.1.153

Claude Code loaded the same project configuration with `--strict-mcp-config`. Its initialization
event reported `hy3-ci-copilot` as connected and exposed all four tools. It called
`diagnose_ci_failure` with:

```json
{
  "log_path": "logs/failed.log",
  "repository_path": "examples/demo_repository",
  "output_language": "en",
  "reasoning_effort": "high"
}
```

Observed result:

- CLI result subtype: `success`
- Response marker: `HY3_CLAUDE_CLIENT_OK`
- End-to-end duration: `64.443s`
- Primary cause and verification command matched the CodeBuddy result

These are live client calls, not mocked protocol tests. The automated test suite separately uses a
local fake Chat Completions endpoint so it remains deterministic and does not consume API quota.
