# MCP Client Verification

Verification date: 2026-07-24

This file records real MCP client checks for `hy3-leadintel-mcp`. All commands were run from `mcp_servers/leadintel` in offline demo mode, with local absolute paths sanitized to `/ABS/PATH/TO/Hy3/mcp_servers/leadintel`.

## Client 1: Claude Code CLI 2.1.146

Add the server:

```bash
claude mcp add hy3-leadintel-verify hy3-leadintel-mcp \
  -s local \
  -e HY3_OFFLINE=1 \
  -e HY3_LEADINTEL_ROOT=/ABS/PATH/TO/Hy3/mcp_servers/leadintel
```

Health check:

```bash
claude mcp list
```

Observed result:

```text
hy3-leadintel-verify: hy3-leadintel-mcp - ✓ Connected
```

Tool call:

```bash
claude -p 'Call the MCP tool hy3_leadintel_status and return only its JSON result.' \
  --model deepseek-v4-flash \
  --allowedTools 'mcp__hy3-leadintel-verify__hy3_leadintel_status' \
  --output-format json \
  --max-budget-usd 0.25
```

Observed result excerpt:

```json
{
  "server": "hy3-leadintel-mcp",
  "model": "hy3",
  "api_key_present": false,
  "mode": "offline",
  "tools": [
    "analyze_lead",
    "query_knowledge_base",
    "generate_outreach_plan",
    "batch_score_leads",
    "hy3_leadintel_status"
  ]
}
```

## Client 2: MCP Inspector CLI 1.0.0

Run `tools/list`:

```bash
npx --yes @modelcontextprotocol/inspector \
  --cli \
  --config /tmp/hy3-leadintel-inspector.config.json \
  --server hy3-leadintel \
  --method tools/list
```

Observed result:

```text
5 tools listed: analyze_lead, query_knowledge_base, generate_outreach_plan, batch_score_leads, hy3_leadintel_status
```

Call `hy3_leadintel_status`:

```bash
npx --yes @modelcontextprotocol/inspector \
  --cli \
  --config /tmp/hy3-leadintel-inspector.config.json \
  --server hy3-leadintel \
  --method tools/call \
  --tool-name hy3_leadintel_status
```

Observed result excerpt:

```json
{
  "structuredContent": {
    "server": "hy3-leadintel-mcp",
    "model": "hy3",
    "api_key_present": false,
    "mode": "offline",
    "tools": [
      "analyze_lead",
      "query_knowledge_base",
      "generate_outreach_plan",
      "batch_score_leads",
      "hy3_leadintel_status"
    ]
  },
  "isError": false
}
```
