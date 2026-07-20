# Hy3 TaskRelay MCP

Hy3 TaskRelay is a local stdio MCP server for handing an interrupted long task to another session
or MCP client. Hy3 performs semantic extraction, conflict reasoning, and continuation planning.
Local code enforces input boundaries, credential redaction, stable IDs, evidence integrity,
timeouts, bounded retries, and output-schema validation.

The first release is deliberately stateless and read-only. It does not scan a repository, inspect
agent logs, write files, execute commands, or create a database. The caller saves and transports
the returned checkpoint.

## Scope and differentiation

TaskRelay is the explicit-input artifact layer for Issue #3. It is not a generic chat server,
repository agent, knowledge base, or native persistent memory. The closest submitted idea found in
the duplicate audit was [PR #78, CtxPilot](https://github.com/Tencent-Hunyuan/Hy3/pull/78), a
closed, unmerged Issue #4 application:

| Boundary | TaskRelay | CtxPilot PR #78 |
|---|---|---|
| Input | Material explicitly supplied in each MCP call | Agent logs and Git state collected automatically |
| State | Stateless portable schema artifact | Persistent application workflow |
| Side effects | No scanning and no file writes | Writes `HANDOFF.md` / `AGENTS.md`; includes a Web UI |
| Primary concern | Evidence-linked checkpoint, audit, and resume contract | Project/session harvesting and continuity |

The implementations therefore address adjacent product layers rather than duplicate submissions.

## 1. Install

Requirements: Python 3.10 or newer and either `uv` or `pip`. The package uses the stable v1 line of
the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x), pinned
to `mcp>=1.28.1,<2`.

From a Hy3 checkout:

```powershell
# Windows PowerShell
uv sync --directory mcp_servers/hy3_taskrelay --extra dev
uv run --directory mcp_servers/hy3_taskrelay hy3-taskrelay-mcp
```

```bash
# macOS / Linux
uv sync --directory mcp_servers/hy3_taskrelay --extra dev
uv run --directory mcp_servers/hy3_taskrelay hy3-taskrelay-mcp
```

An ordinary local install is also supported:

```bash
python -m pip install ./mcp_servers/hy3_taskrelay
hy3-taskrelay-mcp
# Equivalent entry point:
python -m hy3_taskrelay
```

The process waits for MCP JSON-RPC on stdin. Starting it directly is therefore expected to show no
interactive prompt.

## 2. Configure the Hy3 API

Set exactly three process environment variables. Keep the key in your operating-system secret
store or local shell environment; do not commit it, paste it into an issue, or send it in chat.

```powershell
$env:HY3_API_KEY = "<set-locally>"
$env:HY3_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
$env:HY3_MODEL = "hy3"
```

```bash
export HY3_API_KEY='<set-locally>'
export HY3_BASE_URL='https://tokenhub.tencentmaas.com/v1'
export HY3_MODEL='hy3'
```

The key is required only when a tool is called, so `initialize` and `tools/list` remain available
for diagnosis. `HY3_BASE_URL` must use HTTPS; loopback HTTP is accepted only for offline tests.
Unexpanded `${...}` placeholders are rejected instead of being sent to the API.

## 3. Add the server to a client

### CodeBuddy project configuration

Copy [`examples/clients/codebuddy.mcp.json`](examples/clients/codebuddy.mcp.json) to `.mcp.json` at
the Hy3 project root. This repository already includes that project file. CodeBuddy documents the
project location, first-connection approval, headless approval settings, and exact tool permission
names in its [official MCP guide](https://www.codebuddy.ai/docs/cli/mcp).

The equivalent persistent registration command is:

```bash
codebuddy mcp add-json --scope project hy3-taskrelay '{"type":"stdio","command":"uv","args":["run","--directory","mcp_servers/hy3_taskrelay","hy3-taskrelay-mcp"],"env":{"HY3_API_KEY":"${HY3_API_KEY}","HY3_BASE_URL":"${HY3_BASE_URL:-https://tokenhub.tencentmaas.com/v1}","HY3_MODEL":"${HY3_MODEL:-hy3}"}}'
```

Approve a project MCP server interactively on first connection. For a reproducible headless call,
CodeBuddy requires an explicit project-server approval setting. The validation run also exposed
and allowed only the single TaskRelay tool:

```powershell
$prompt = 'Call taskrelay_create_checkpoint once with the public synthetic fixture and return its structured result.'
codebuddy --model hy3 --output-format text `
  --strict-mcp-config --mcp-config .mcp.json `
  --settings '{"enabledMcpjsonServers":["hy3-taskrelay"]}' `
  --tools 'NoDefer(mcp__hy3-taskrelay__taskrelay_create_checkpoint)' `
  --allowedTools 'mcp__hy3-taskrelay__taskrelay_create_checkpoint' `
  -y -p $prompt
```

`-y` bypasses interactive permission prompts. Use it only with the strict server config and exact
tool allowlist shown above. The official installation command is
`npm install -g @tencent-ai/codebuddy-code`; CodeBuddy Code 2.124.0 was used for validation.

### Codex project configuration

Copy [`examples/clients/codex.config.toml`](examples/clients/codex.config.toml) to
`.codex/config.toml` at the Hy3 project root. This repository already includes that file. Codex
loads project-scoped configuration only for a trusted project. Its
[official MCP guide](https://developers.openai.com/codex/mcp) documents `env_vars`, tool allowlists,
and timeouts. `env_vars` forwards values from the client process and does not store them in TOML.

```bash
codex mcp list
codex
```

Confirm that `hy3-taskrelay` and exactly three TaskRelay tools appear before asking Codex to audit
the checkpoint and create a resume brief. The checked-in 240-second client timeout is longer than
the server's 105-second total structured-generation budget.

### Optional Cursor project configuration

Copy [`examples/clients/cursor.mcp.json`](examples/clients/cursor.mcp.json) to
`.cursor/mcp.json` at the project root. Cursor documents this location in its
[official MCP guide](https://docs.cursor.com/context/model-context-protocol). Cursor is an optional
third-client example and was not required for the recorded CodeBuddy + Codex flow.

## 4. Make the first call

Ask the client to call `taskrelay_create_checkpoint` with a small synthetic input:

```json
{
  "goal": "Fix the empty-cart total regression.",
  "session_material": "The previous session reproduced test_empty_cart_total and stopped before the patch.",
  "constraints": ["Do not change the public API."],
  "decisions": ["Add the regression test first."],
  "evidence": [
    {
      "evidence_id": "ev_test_log",
      "content": "test_empty_cart_total expected Decimal('0.00') but received None.",
      "source": "synthetic pytest log"
    }
  ]
}
```

Save the exact structured checkpoint. The artifact chain is:

1. Pass that checkpoint to `taskrelay_audit_checkpoint`. Optional `additional_evidence` here means
   evidence learned after checkpoint creation.
2. The audit result carries the complete evidence catalogue: unchanged checkpoint evidence plus
   any audit-time evidence.
3. Pass the exact checkpoint and audit result to `taskrelay_create_resume_brief`. Its optional
   `additional_evidence` is only for evidence learned after the audit; do not re-pass evidence
   already carried by the audit.

Stable IDs are derived from canonical content. Editing an artifact while retaining its old ID is
rejected.

## 5. Tools

| Tool | Purpose | Main output |
|---|---|---|
| `taskrelay_create_checkpoint` | Extract portable state from explicit task material | Goal, grounded facts, constraints, decisions, open questions, next steps, evidence catalogue, stable checkpoint ID |
| `taskrelay_audit_checkpoint` | Find contradictions, missing constraints, stale assumptions, and unsupported claims | Severity-ranked findings with evidence IDs and corrections |
| `taskrelay_create_resume_brief` | Plan continuation from a checkpoint and audit | Concise context, prioritized steps, validation gates, blockers, and prohibited actions |

All three tools are annotated read-only, non-destructive, idempotent, and open-world. Open-world is
true because a call reaches the external Hy3 API. Each success result includes MCP
`structuredContent` plus a compact JSON text block for clients that do not expose structured
content directly.

Evidence IDs must begin with `ev_` and be unique. Model-authored conclusions, actions, blockers,
and prohibited actions must cite caller-supplied IDs. Explicit caller constraints and decisions may
retain an empty evidence list; the audit does not flag them merely for being explicit context. An
unknown reference triggers at most one controlled repair request. Invalid output after that
attempt is rejected.

## 6. Limits and failure behavior

| Operation | Aggregate serialized input | Additional limits |
|---|---:|---|
| Create checkpoint | 30,000 characters | 1–50 evidence; up to 30 constraints and 30 decisions |
| Audit | 200,000 characters | Up to 20 new evidence items |
| Resume | 500,000 characters | Up to 20 post-audit evidence items; continuation context up to 4,000 characters |

- Final artifact limits are 65,000 characters for a checkpoint, 300,000 for an audit, and 500,000
  for a resume brief. Hy3 drafts are separately capped before local evidence attachment.
- HTTP response transport is capped at 512,000 bytes; assistant content is capped at 100,000
  characters before JSON, Pydantic, identity, and evidence-reference validation.
- One structured operation, including the original generation and at most one repair, has a
  105-second total budget. Individual HTTP attempts use a 45-second timeout.
- HTTP 400, 401, and 403 fail immediately. HTTP 429, 502, 503, 504, and network timeouts use at
  most two retries. Numeric and HTTP-date `Retry-After` values are honored up to 30 seconds;
  TokenHub capacity error `429006` follows the 429 path.
- Requests use `temperature=0.9`, `top_p=1.0`, and Hy3 `reasoning_effort=high`.
- Caller payloads and failed model output are marked as untrusted data in system instructions.
- Errors omit response bodies, request IDs, account data, keys, cookies, authorization values,
  connection strings, and unsafe caller identifiers.

## 7. Troubleshooting

`HY3_API_KEY is required`: set the variable in the environment that launches the MCP client, then
restart or reconnect the server. A literal `${HY3_API_KEY}` is intentionally treated as missing.

`HY3 authentication failed`: verify the key locally and confirm its TokenHub/model permissions. Do
not paste the key into a bug report.

`HY3_BASE_URL` error: use a complete HTTPS OpenAI-compatible base URL ending in `/v1`, without
embedded credentials, query, or fragment.

Server not discovered: run the client from the Hy3 project root, execute `codebuddy mcp list` or
`codex mcp list`, and verify that `uv` is on the client's PATH. For CodeBuddy headless mode, include
the project-server approval setting above. For Codex, trust the project or use user-scoped MCP
configuration. Stdio logs belong on stderr; non-JSON output on stdout is a server bug.

Schema or evidence error: errors identify only safe contract fields when possible and never echo
caller values or unknown IDs. Check the documented field and aggregate limits, evidence-ID format,
artifact linkage, and whether resume evidence is genuinely new. If an existing artifact contains
credential-like material, recreate it from sanitized source material. Never edit an artifact while
retaining its old content-derived ID.

## 8. Real-client validation and demo

The 2026-07-20 cross-client run used one public synthetic fixture:

1. CodeBuddy Code 2.124.0 called `taskrelay_create_checkpoint` through a strict single-tool
   allowlist and created `cp_b3067b1cc7f4a430` with three grounded facts and two next steps.
2. Codex CLI 0.144.6 received that exact structured checkpoint in an ephemeral, read-only run.
3. Codex called `taskrelay_audit_checkpoint` (`clean`, zero findings) and then
   `taskrelay_create_resume_brief`, creating `resume_bff690737dece30f` with priority order 1 → 2.

The schema-valid artifacts are in [`docs/client_artifacts`](docs/client_artifacts). Sanitized
client-event records are in [`docs/clients`](docs/clients). The
[actual-call screenshots and short GIF](docs/demo) are rendered from those real call records and
exact artifact IDs. Credentials, prompts, raw provider responses, request metadata, account data,
and personal paths are not committed.

## 9. Offline verification and evaluations

The default suite never calls the real API:

```bash
uv run --directory mcp_servers/hy3_taskrelay pytest
uv run --directory mcp_servers/hy3_taskrelay ruff format --check .
uv run --directory mcp_servers/hy3_taskrelay ruff check .
uv run --directory mcp_servers/hy3_taskrelay python evals/run.py
```

The evaluation bank contains 14 independent checks over two public synthetic fixtures:
[`interrupted_bug_fix.json`](examples/fixtures/interrupted_bug_fix.json) and
[`requirements_change.json`](examples/fixtures/requirements_change.json).

MCP Inspector can exercise the stdio server after installation:

```bash
npx -y @modelcontextprotocol/inspector uv run --directory mcp_servers/hy3_taskrelay hy3-taskrelay-mcp
```

## Acceptance evidence map

| Issue requirement | Repository evidence | Remaining external gate |
|---|---|---|
| Official MCP SDK and stdio | `pyproject.toml`, SDK memory-session tests, raw stdio test, [Inspector record](docs/inspector_2026-07-20.json) | None |
| At least three clear tools | `server.py`, Pydantic contracts, tool-list and call tests | None |
| Hy3 performs core reasoning | Prompts, validated structured generation, real HTTP client, [three-operation smoke](docs/live_smoke_2026-07-20.json) | None |
| Environment-only key | `config.py`, redaction/error tests, sanitized [client records](docs/clients) | None |
| Two MCP clients including CodeBuddy/WorkBuddy | CodeBuddy + Codex configs, versions, successful real calls, schema-valid [artifacts](docs/client_artifacts) | None |
| One-command install | Console entry point, wheel/sdist with license, [clean-install record](docs/verification_2026-07-20.md) | None |
| Demo GIF/video | [CodeBuddy → Codex actual-call demo](docs/demo/taskrelay_cross_client.gif) over a public synthetic fixture | None |
