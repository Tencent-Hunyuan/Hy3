# Hy3 API Guardian MCP Server

[中文](README.md) | English

Hy3 API Guardian is a local, read-only MCP server for governing OpenAPI 3.x contracts with
Tencent Hy3. It runs deterministic checks before asking Hy3 to reason over bounded evidence, which
makes the results easier to verify and less prone to invented endpoints.

This project implements Tencent Rhino-Bird 2026
[Hy3 Issue #3](https://github.com/Tencent-Hunyuan/Hy3/issues/3).

## Tools

| Tool | Purpose |
| --- | --- |
| `audit_openapi` | Audit correctness, security, reliability, evolvability, and DX |
| `detect_breaking_changes` | Compare two contracts and produce an impact-aware migration plan |
| `generate_contract_tests` | Generate pytest/httpx or Jest tests grounded in selected operations |

Every tool calls Hy3 for its core semantic reasoning. Local parsing and comparison provide
deterministic evidence.

## Install

Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install .
```

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
```

Or run directly from the local source with uv:

```bash
uvx --from . hy3-api-guardian
```

## Configuration

Required environment variable:

```text
HY3_API_KEY=<your TokenHub API key>
```

Useful defaults:

```text
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3
HY3_ALLOWED_ROOT=<directory containing the OpenAPI files>
HY3_REASONING_EFFORT=high
```

Run `hy3-api-guardian --check` to validate configuration without printing the secret.

Copy a client template from [`clients/`](clients/):

- CodeBuddy project config: `clients/codebuddy.project.example.json` → `.mcp.json`
- Cursor project config: `clients/cursor.project.example.json` → `.cursor/mcp.json`

Replace placeholders only in the local config. Never commit a real API key.

CodeBuddy recommends the repository-root `.mcp.json` for project scope and requires approval on
the first connection. Cursor reads project servers from `.cursor/mcp.json`. See the official
[CodeBuddy MCP documentation](https://www.codebuddy.ai/docs/cli/mcp) and
[Cursor MCP documentation](https://docs.cursor.com/context/model-context-protocol).

## Demo

![Cursor calling Hy3 API Guardian through native MCP](docs/verification/assets/cursor-native-mcp-demo.gif)

The recording shows Cursor discovering the project-level tools, directly calling
`detect_breaking_changes`, and rendering the structured `5 breaking / 1 warning / 1 compatible`
result. Sanitized verification records are under [`docs/verification/`](docs/verification/README.md).

## Demo prompts

```text
Use audit_openapi on examples/insecure-api.yaml with focus=security.
```

```text
Use detect_breaking_changes to compare examples/petstore-v1.yaml and
examples/petstore-v2-breaking.yaml, then propose a safe migration sequence.
```

```text
Use generate_contract_tests to create pytest tests for GET /pets/{petId} from
examples/petstore-v1.yaml.
```

The server never executes generated tests. Review them before running in an isolated test
environment. The real Hy3 smoke test additionally checks that generated pytest source parses as
valid Python.

## Security

- Read-only stdio server; no source-file writes or command execution.
- Real-path containment under `HY3_ALLOWED_ROOT`.
- Safe YAML loading with aliases rejected, plus size/depth/node limits.
- Best-effort credential and private-key redaction before provider calls.
- Untrusted-data boundaries in every model prompt.
- API keys are read from environment variables and never returned or logged.
- Bounded local JSON Pointer `$ref` resolution for parameters, path items, and request bodies.
- Remote `$ref` values are not fetched.

The deterministic comparator covers common compatibility changes; it is not a complete formal
OpenAPI compatibility proof. Hy3 augments those bounded findings with semantic impact analysis.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m build
```

Licensed under Apache-2.0, consistent with the parent Hy3 repository.
