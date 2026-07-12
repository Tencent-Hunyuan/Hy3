# Hy3 Code Review MCP Server

`hy3-code-review-mcp` is a local stdio MCP Server that exposes Hy3-powered code review tools to MCP clients. The current examples and hands-on validation cover Trae and CodeBuddy.

Cursor, Qoder, Cline, WorkBuddy, and other vibe-coding clients may support the same MCP stdio shape, but they have not been practiced for this branch yet.

The server reads a git diff, pasted patch, or test-planning request, calls a Hy3 OpenAI-compatible API, and returns structured markdown review output.

## Tools

| Tool | Purpose | Key parameters |
| --- | --- | --- |
| `review_git_diff` | Read a local git diff and ask Hy3 for a prioritized code review. | `repo_path`, `base_ref`, `target_ref`, `focus`, `max_chars` |
| `review_patch` | Review a pasted patch or unified diff. | `patch_text`, `language`, `focus`, `context` |
| `suggest_tests` | Generate unit, integration, edge-case, and regression test suggestions for a diff. | `diff_text`, `test_framework`, `risk_level` |

## Install

From this repository:

```bash
pip install ./mcp_servers/code_review
```

For local development:

```bash
pip install -e ./mcp_servers/code_review[dev]
```

After installation, the MCP server command is:

```bash
hy3-code-review-mcp
```

If you installed the package inside a conda environment, GUI clients may not inherit that environment's `PATH`. In that case, configure the client with the environment's Python executable:

```json
{
  "command": "/absolute/path/to/conda/envs/llms/bin/python",
  "args": ["-m", "hy3_code_review_mcp.server"]
}
```

## Configure Hy3 API

The server never hardcodes API keys. Use environment variables or a `.env` file.

When running from this repository, place `.env` in the repository root:

```bash
cp .env.example .env
```

The server searches for `.env` from the current working directory upward. You can also point to a specific file:

```bash
export HY3_ENV_FILE=/absolute/path/to/.env
```

Local vLLM/SGLang example:

```bash
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
HY3_TEMPERATURE=0.2
HY3_TOP_P=1.0
HY3_MAX_TOKENS=1600
HY3_REASONING_EFFORT=no_think
```

OpenRouter example:

```bash
HY3_BASE_URL=https://openrouter.ai/api/v1
HY3_API_KEY=sk-or-...
# OPENROUTER_API_KEY=sk-or-... also works when HY3_API_KEY is unset or EMPTY
HY3_MODEL=tencent/hy3:free
HY3_REASONING_EFFORT=no_think
```

Tencent Cloud Hunyuan example:

```bash
HY3_BASE_URL=https://api.hunyuan.cloud.tencent.com/v1
HUNYUAN_API_KEY=...
HY3_MODEL=hunyuan-turbos-latest
```

For OpenRouter, `HY3_REASONING_EFFORT=no_think` maps to `{"reasoning": {"effort": "none"}}`. For local vLLM/SGLang, it maps to Hy3 chat template kwargs.

## Client Configuration

Trae and CodeBuddy use the same stdio server process. Prefer a project-level MCP config when the client supports it, and pass only `HY3_ENV_FILE` in the client config so API keys stay in your local `.env`.

### Trae / CodeBuddy

Use `examples/trae-codebuddy.mcp.json` as the shared stdio config template. See `docs/clients/trae-codebuddy.md` for setup details and the actual Trae review output.

Example prompt:

```text
Use hy3-code-review to review the demo code in mcp_servers/code_review/examples/review_demo_payment.py. Focus on correctness, security, reliability, and missing tests.
```

### Unverified MCP Clients

Cursor, Qoder, Cline, WorkBuddy, and other vibe-coding clients have not been practiced in this branch. If a client accepts `mcpServers` JSON, it will likely use the same stdio shape, but this repository does not claim those clients are verified yet:

```json
{
  "mcpServers": {
    "hy3-code-review": {
      "command": "/absolute/path/to/conda/envs/llms/bin/python",
      "args": ["-m", "hy3_code_review_mcp.server"],
      "env": {
        "HY3_ENV_FILE": "/absolute/path/to/Hy3/.env"
      }
    }
  }
}
```

Example prompt:

```text
Use the hy3-code-review MCP server. Call review_git_diff with repo_path set to this project, base_ref "main", and focus "correctness, security, and missing tests".
```

## Tool Examples

### `review_git_diff`

```json
{
  "repo_path": "/absolute/path/to/project",
  "base_ref": "main",
  "target_ref": null,
  "focus": "correctness, security, reliability, and tests",
  "max_chars": 24000
}
```

### `review_patch`

```json
{
  "patch_text": "diff --git a/app.py b/app.py\n+ risky_change()",
  "language": "python",
  "focus": "correctness and missing tests",
  "context": "Backend service handling user requests."
}
```

### `suggest_tests`

```json
{
  "diff_text": "diff --git a/app.py b/app.py\n+ add_retry_loop()",
  "test_framework": "pytest",
  "risk_level": "high"
}
```

## Test

```bash
PYTHONPATH=mcp_servers/code_review/src pytest -q mcp_servers/code_review/tests
python -m py_compile mcp_servers/code_review/src/hy3_code_review_mcp/*.py
```

## Demo Recording Checklist

1. Install the package with `pip install ./mcp_servers/code_review`.
2. Configure `.env` with Hy3 API settings.
3. Add the server to Trae and CodeBuddy.
4. In Trae, call `review_patch` against `examples/review_demo_payment.py`.
5. In CodeBuddy, call `review_patch` or `suggest_tests` against the same demo diff.
6. Record the screen as a GIF or video and attach it to the PR or issue comment.

## Safety Notes

- The server only reads local git data for the `repo_path` explicitly passed by the MCP client.
- Diffs are truncated by `max_chars` before being sent to Hy3.
- API keys are read from environment variables or `.env`; they are not logged or returned by tools.
- Hy3 requests use a 30-second timeout and retry empty provider responses up to two times.
- stdio MCP servers must not write logs to stdout. This server does not print during normal operation.
