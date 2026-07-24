# Hy3 LeadIntel MCP Server

Hy3 LeadIntel MCP Server is a local `stdio` MCP server for B2B sales and research operations. It packages Hy3 as a plug-and-play tool server for CodeBuddy, WorkBuddy, Cursor, Cline, and other MCP-compatible clients.

Unlike a generic knowledge-base chatbot, this server connects a real sales workflow:

1. Analyze a lead.
2. Retrieve grounded product or competitor evidence.
3. Generate an outreach plan.
4. Batch-score CSV or JSON lead lists.

It runs without a Hy3 key in deterministic offline mode for local verification. Set `HY3_API_KEY` and `HY3_API_BASE` to call a real Hy3 OpenAI-compatible endpoint.

## Tools

| Tool | Purpose |
|---|---|
| `analyze_lead` | Analyze company, industry, website, notes, and product context. Returns priority, deterministic signals, risks, and Hy3 analysis. |
| `query_knowledge_base` | Search local `.md`, `.txt`, `.csv`, and `.json` files, then ask Hy3 to answer with citations. |
| `generate_outreach_plan` | Generate first-touch copy, follow-up cadence, proof points, and CRM actions. |
| `batch_score_leads` | Read CSV/JSON lead lists, score each lead, optionally export a JSON report, and summarize the best outreach order. |
| `hy3_leadintel_status` | Show model, mode, root directory, and tool availability without exposing the API key. |

## Install

```bash
cd mcp_servers/leadintel
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
hy3-leadintel-mcp --selfcheck
```

One-command install from a local checkout:

```bash
uvx --from /ABS/PATH/TO/Hy3/mcp_servers/leadintel hy3-leadintel-mcp --selfcheck
```

## Hy3 Configuration

Offline mode is automatic when `HY3_API_KEY` is absent.

```bash
export HY3_API_BASE=http://127.0.0.1:8000/v1
export HY3_API_KEY=your_key_here
export HY3_MODEL=hy3
export HY3_REASONING_EFFORT=high
export HY3_LEADINTEL_ROOT=/ABS/PATH/TO/Hy3/mcp_servers/leadintel
```

Hy3's upstream quickstart recommends OpenAI-compatible `/v1/chat/completions`, `temperature=0.9`, `top_p=1.0`, and `reasoning_effort` in `chat_template_kwargs`; this server follows that wire format.

## Client Setup

### CodeBuddy / WorkBuddy

Use the project-level config in `clients/codebuddy.mcp.json`, or add an equivalent command:

```bash
codebuddy mcp add hy3-leadintel \
  -e HY3_API_BASE=http://127.0.0.1:8000/v1 \
  -e HY3_API_KEY=$HY3_API_KEY \
  -e HY3_MODEL=hy3 \
  -e HY3_LEADINTEL_ROOT=/ABS/PATH/TO/Hy3/mcp_servers/leadintel \
  -- uvx --from /ABS/PATH/TO/Hy3/mcp_servers/leadintel hy3-leadintel-mcp
```

Demo prompt:

```text
Use hy3_leadintel_status, then analyze_lead for Aurora Motion GmbH. It is a manufacturing automation company with an RFQ for export-ready hollow-cup motor samples.
```

### Cursor

Copy `clients/cursor.mcp.json` into your Cursor MCP config and replace absolute paths.

Demo prompt:

```text
Use query_knowledge_base to answer: What proof points support robotics motor outreach?
```

### Cline

Copy the `hy3-leadintel` entry from `clients/cline_mcp_settings.json` into Cline's MCP settings.

Demo prompt:

```text
Use batch_score_leads on examples/leads/sample_leads.csv and tell me which company should be contacted first.
```

### MCP Inspector

Use `clients/inspector.config.json` for the official MCP Inspector CLI. Replace `/ABS/PATH/TO/Hy3/mcp_servers/leadintel` before running:

```bash
npx --yes @modelcontextprotocol/inspector \
  --cli \
  --config clients/inspector.config.json \
  --server hy3-leadintel \
  --method tools/list
```

Tool-call demo:

```bash
npx --yes @modelcontextprotocol/inspector \
  --cli \
  --config clients/inspector.config.json \
  --server hy3-leadintel \
  --method tools/call \
  --tool-name hy3_leadintel_status
```

## Local Verification

```bash
cd mcp_servers/leadintel
python3 -m pytest -q
hy3-leadintel-mcp --selfcheck
python scripts/sdk_stdio_client.py
```

Expected result:

- tests pass;
- selfcheck reports `PASS`;
- MCP SDK stdio client initializes the MCP server, lists tools, and calls `hy3_leadintel_status`.

## Verified MCP Clients

The server was verified in two distinct MCP clients on 2026-07-24:

| Client | Version | Verification |
|---|---:|---|
| Claude Code CLI | 2.1.146 | `claude mcp list` reported `✓ Connected`; `claude -p` called `hy3_leadintel_status` and returned the status JSON. |
| MCP Inspector CLI | 1.0.0 | `tools/list` returned 5 tools; `tools/call --tool-name hy3_leadintel_status` returned `isError: false` with structured content. |

The sanitized command log is in `assets/client_verification.md`.

## Demo

The repository includes:

- `assets/demo_transcript.json`: a reproducible offline MCP transcript.
- `assets/demo.gif`: a small GIF showing the Claude Code and MCP Inspector client verification flow.
- `assets/client_verification.md`: sanitized command log for two real MCP client checks.
- `scripts/sdk_stdio_client.py`: an MCP SDK stdio client that can regenerate the transcript.

Offline demo output is clearly marked as offline. With a real Hy3 key, the same MCP tools call the configured Hy3 endpoint.

## Rhinobird 2026 Acceptance Mapping

| Requirement | Status | Evidence |
|---|---|---|
| Develop for `rhinobird2026` | Done | This directory is added under the `rhinobird2026` checkout. |
| MCP Python or TypeScript SDK | Done | `src/hy3_leadintel_mcp/server.py` uses MCP Python SDK `FastMCP`. |
| At least 3 tools | Done | 5 tools are exposed. |
| Hy3 API performs core reasoning | Done | `hy3_client.py` calls OpenAI-compatible `/chat/completions`; offline mode is only for deterministic demo and tests. |
| Add 1-2 data sources/tools | Done | Local knowledge-base files and CSV/JSON lead files. |
| Local stdio mode | Done | `app.run(transport="stdio")`. |
| No hardcoded API key | Done | Key is read only from `HY3_API_KEY`; status exposes only a boolean. |
| Verify in 2 MCP clients | Done | Claude Code CLI and MCP Inspector CLI both connected and called/listed MCP tools; see `assets/client_verification.md`. |
| One-command install | Done | `uvx --from ... hy3-leadintel-mcp` and `pip install -e .`. |
| Complete README | Done | Install, config, tools, demos, tests, and acceptance mapping are documented here. |
| Demo video/GIF | Done | `assets/demo.gif` and transcript included. |

## Safety Notes

- File reads are contained under `HY3_LEADINTEL_ROOT`.
- Unsupported file types are ignored by knowledge search.
- Batch scoring accepts only `.csv` and `.json`.
- Offline mode never sends data to a network endpoint.
