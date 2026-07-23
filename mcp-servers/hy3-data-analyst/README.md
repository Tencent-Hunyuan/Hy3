# Hy3 Data Analyst MCP Server

[中文说明](README_CN.md)

A local, stdio-based [Model Context Protocol](https://modelcontextprotocol.io/) server that
combines safe CSV/JSON inspection with Tencent Hy3 reasoning. It is designed for data-quality,
business-analysis, and report-writing workflows in CodeBuddy, WorkBuddy, Cursor, and other MCP
clients.

![Protocol demo](docs/demo.gif)

## Tools

| Tool | Hy3 call | Purpose |
| --- | --- | --- |
| `profile_dataset` | No | Inspect schema, missing values, unique counts, numeric statistics, and bounded samples |
| `analyze_dataset` | Yes | Answer a question using the generated profile and sample rows |
| `generate_data_report` | Yes | Produce an evidence-grounded Markdown report for a stated objective |

All tools accept `.csv`, `.json`, `.jsonl`, and `.ndjson`. Files must be below `HY3_DATA_DIR`.

## Requirements

- Python 3.10 or newer
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pipx`
- A Hy3 OpenAI-compatible endpoint for the two reasoning tools. Follow the repository's
  [deployment guide](../../README.md#deployment) to start vLLM or SGLang.

## One-command install

From this directory:

```bash
uv tool install .
```

The `hy3-data-analyst` command is then available to MCP clients. To update an existing install:

```bash
uv tool install --force .
```

For development, no global install is required. A non-editable sync avoids hidden `.pth`
compatibility issues in newer Python maintenance releases:

```bash
uv sync --dev --no-editable
uv run --no-sync hy3-data-analyst
```

The process uses stdio, so an empty terminal after startup is expected. MCP clients manage it
automatically.

## Configuration

No API key is stored in source code. Configure the server process through environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `HY3_API_BASE` | `http://127.0.0.1:8000/v1` | OpenAI-compatible Hy3 base URL |
| `HY3_API_KEY` | `EMPTY` | API key; `EMPTY` is suitable for an unsecured local server |
| `HY3_MODEL` | `hy3` | Served model name |
| `HY3_DATA_DIR` | Server working directory | Only directory the tools may read |
| `HY3_MAX_FILE_BYTES` | `10485760` (10 MiB) | Per-file safety limit |
| `HY3_TIMEOUT_SECONDS` | `120` | Hy3 request timeout |

Copy [`.env.example`](.env.example) as a reference, but pass values from the MCP client config or a
secret manager. Do not commit a real key.

## Client setup

Before using a template, replace all `/ABSOLUTE/PATH/...` placeholders. Use `command -v uvx` to get
the executable path. Absolute paths are important because desktop apps may use a smaller `PATH`
than your terminal. The templates use `uvx --from <package-path>`, which creates an isolated,
non-editable install and needs no manual activation.

### CodeBuddy / WorkBuddy

CodeBuddy's current project-level config is `<project>/.mcp.json`. Copy
[`client-configs/codebuddy.mcp.json`](client-configs/codebuddy.mcp.json) there, update its paths and
environment, then restart or refresh MCP servers.

For a one-off CLI check without changing user configuration:

```bash
codebuddy \
  --mcp-config client-configs/codebuddy.mcp.json \
  --strict-mcp-config \
  --settings '{"enabledMcpjsonServers":["hy3-data-analyst"]}' \
  -p "Use profile_dataset on examples/sample_sales.csv and report the row count."
```

WorkBuddy's custom MCP dialog accepts the same stdio JSON. A separate
[`client-configs/workbuddy.mcp.json`](client-configs/workbuddy.mcp.json) is included for direct
import.

### Cursor

Copy [`client-configs/cursor.mcp.json`](client-configs/cursor.mcp.json) to
`<project>/.cursor/mcp.json`, update its paths and environment, then enable `hy3-data-analyst` in
Cursor's MCP settings.

## Tool-call examples

Profile a file without a model call:

```json
{
  "file_path": "examples/sample_sales.csv",
  "max_rows": 10000,
  "sample_rows": 5
}
```

Ask Hy3 an analytical question:

```json
{
  "file_path": "examples/sample_sales.csv",
  "question": "Which region has the strongest observed revenue, and what are the limitations?",
  "reasoning_effort": "high",
  "sample_rows": 10
}
```

Generate a decision-oriented report:

```json
{
  "file_path": "examples/sample_sales.csv",
  "objective": "Help a sales manager prioritize regions while highlighting data-quality risks",
  "reasoning_effort": "high"
}
```

See [`examples/demo-prompts.md`](examples/demo-prompts.md) for prompts that MCP clients can execute.

## Verification

Run formatting/static checks, unit tests, and an actual stdio protocol round trip:

```bash
uv sync --dev --no-editable
uv run --no-sync ruff check .
uv run --no-sync pytest
uv run --no-sync python scripts/check_mcp.py
```

The smoke client initializes an MCP session, verifies the exact three-tool inventory, and calls
`profile_dataset` on the included sample. The test suite mocks the unavailable remote model while
verifying that dataset context, the question, and reasoning mode are sent through the Hy3 call
path. To verify a real model deployment, set `HY3_API_BASE`/`HY3_API_KEY` and call either reasoning
tool from an MCP client.

## Safety and data boundaries

- Resolved paths cannot escape `HY3_DATA_DIR`, including through `..` or symlinks.
- Unsupported formats and oversized files are rejected before parsing.
- At most 100,000 rows are scanned and at most 20 sample rows are sent to Hy3.
- API keys are environment-only and redacted if an SDK error happens to include them.
- `profile_dataset` is fully local. The two Hy3 tools send the generated profile and selected sample
  rows to the configured endpoint, so use `sample_rows=0` for sensitive datasets.
- The server never modifies source datasets.

## Current limitations

- Numeric statistics are descriptive (`min`, `max`, and `mean`) and do not replace a full analytics
  engine.
- Nested JSON values are serialized as strings; deeply nested normalization is intentionally out of
  scope.
- `rows_scanned` is the scanned count, not a guaranteed total when `truncated` is `true`.

## License

Apache License 2.0, consistent with the parent repository.
