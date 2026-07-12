# Hy3 Incident Agent

A standalone engineering incident investigator powered by Hy3. Give it a failure description and trusted text files; Hy3 builds an investigation plan, calls bounded local tools, gathers evidence, and streams a grounded root-cause report to the browser.

## Hy3's role

Hy3 is the Agent's reasoning and control layer. On every round it receives the incident context and prior tool observations, then decides whether to list files, search evidence, read a line range, run an allowlisted check, or produce the final report. The local FastAPI application validates and executes those requests but does not decide the investigation path.

All model calls use the configured OpenAI-compatible Hy3 API. The application performs no training, fine-tuning, or local inference.

```text
Browser -> FastAPI -> Hy3 plan/tool decision
                         |
              bounded local tool execution
                         |
Browser <- NDJSON trace <- Hy3 grounded report
```

## Tools

| Tool | Boundary |
| --- | --- |
| `list_files` | Lists relative workspace paths and sizes |
| `search_files` | Literal case-insensitive search, at most 80 matches |
| `read_file` | Reads at most 300 numbered lines from one relative path |
| `run_checks` | Runs only `pytest` or `py_compile`, with a 20-second timeout |

Each observation is limited to 12,000 characters. Paths must remain inside the per-request temporary workspace. Commands use fixed argument arrays and never pass through a shell.

## Trusted code warning

The `pytest` check executes uploaded project code. Only upload code that you own and trust. The command allowlist prevents arbitrary shell selection, but it is not an operating-system sandbox for hostile Python code.

## Run locally

Python 3.10+ and a Hy3-compatible endpoint are required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r apps/incident_agent/requirements.txt
cp .env.example .env
```

Configure `.env`, for example with OpenRouter:

```bash
HY3_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-...
HY3_MODEL=tencent/hy3:free
HY3_REASONING_EFFORT=no_think
```

Start the Agent:

```bash
uvicorn apps.incident_agent.app:app --reload --port 8010
```

Open `http://127.0.0.1:8010`. API keys stay server-side and are never included in the stream or the page.

## Demo 1: Retry budget regression

1. Select `Retry budget regression`.
2. Click `Start investigation`.
3. Follow Hy3 as it reads `client.py`, inspects `test_client.py`, and runs pytest.
4. Show the final off-by-one diagnosis, evidence, fix, and verification plan.

## Demo 2: Worker startup failure

1. Select `Worker startup failure`.
2. Click `Start investigation`.
3. Follow the searches for `WORKER_QUEUE` and `WORKER_QUEUE_NAME` across logs and configuration.
4. Show the final deployment/configuration mismatch report.

Both flows are designed to fit in one recording under two minutes.

## Limits

- Up to 8 UTF-8 text files per request.
- Up to 512 KiB per file and 2 MiB total.
- Supported types: `.py`, `.txt`, `.log`, `.json`, `.yaml`, `.yml`, `.toml`, `.md`.
- Up to 8 Hy3 tool rounds.
- Temporary evidence is removed when the stream ends or is canceled.

## Tests

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q \
  apps/incident_agent/tests \
  apps/review_workbench/tests \
  mcp_servers/code_review/tests
node --check apps/incident_agent/static/app.js
```

## CodeBuddy collaboration

The following blocks were completed with CodeBuddy collaboration:

- `workspace.py` and `demos.py`: validated temporary evidence workspaces and two deterministic incidents.
- `tools.py`: path-safe file tools and allowlisted checks.
- `agent.py`: the Hy3 tool-calling loop, bounded observations, and streamed event protocol.
- `app.py` and `schemas.py`: multipart validation, sanitized status, demo metadata, and NDJSON responses.
- `static/`: the live investigation timeline, cancel flow, safe report rendering, and responsive layout.
- `tests/`: workspace, tool, orchestration, API, stream, and documentation coverage.
