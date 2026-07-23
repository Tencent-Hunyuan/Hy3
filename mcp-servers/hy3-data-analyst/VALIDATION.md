# Validation record

Validated locally on 2026-07-23 (Asia/Shanghai).

| Layer | Client/runtime | Result |
| --- | --- | --- |
| Static checks | Ruff 0.15.22 | Passed |
| Unit/integration tests | pytest on CPython 3.12 | Passed |
| MCP protocol | MCP Python SDK `ClientSession` over stdio | Initialized, listed 3 tools, called `profile_dataset` |
| AI client | WorkBuddy 2.115.0 bundled CodeBuddy CLI | Loaded the MCP server and called `profile_dataset` |

Observed result for `examples/sample_sales.csv` in both MCP checks:

- `rows_scanned`: 6
- `column_count`: 6
- `units`: 1 missing value

The machine did not provide a reachable Hy3 endpoint or `HY3_API_KEY`. The Hy3 request path is
therefore covered by mocked integration tests that assert the OpenAI-compatible request payload,
reasoning mode, grounded dataset context, response handling, and client cleanup. A live model call
remains environment-dependent and must not be represented as verified until an endpoint is supplied.
