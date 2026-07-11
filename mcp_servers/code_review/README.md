# hy3-code-review-mcp

[![PyPI](https://img.shields.io/pypi/v/hy3-code-review-mcp)](https://pypi.org/project/hy3-code-review-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/hy3-code-review-mcp)](https://pypi.org/project/hy3-code-review-mcp/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

中文文档：[README_CN.md](README_CN.md)

An MCP (Model Context Protocol) Server that brings **Hy3**'s 295B-parameter reasoning model into any MCP-compatible AI client as a plug-and-play code review assistant.

Plug it into **Claude Code**, **CodeBuddy**, **Cursor**, **Cline**, or any MCP client and get:

- Structured, severity-tagged code reviews from `git diff`
- Deep single-file analysis (security / performance / bugs / style)
- One-command pre-merge review of your local repository

---

## Requirements

| Dependency | Notes |
|---|---|
| Python ≥ 3.10 | |
| An OpenAI-compatible API endpoint | Local Hy3 (via vLLM/SGLang) **or** [OpenRouter](https://openrouter.ai/) |
| `uv` (recommended) or `pip` | For installation |

### Option 1 — Local Hy3 (vLLM / SGLang)

Follow the [Hy3 deployment guide](https://github.com/Tencent-Hunyuan/Hy3#deployment) to start vLLM or SGLang.
The default endpoint is `http://127.0.0.1:8000/v1`.

```bash
# Example: vLLM on 8×H20 GPUs
vllm serve tencent/Hy3 \
  --host 0.0.0.0 --port 8000 \
  --tensor-parallel-size 8 \
  --trust-remote-code
```

### Option 2 — OpenRouter (no GPU required)

Get a free API key at [openrouter.ai](https://openrouter.ai/), then set:

```bash
export HY3_BASE_URL=https://openrouter.ai/api/v1
export HY3_API_KEY=<your-openrouter-key>
export HY3_MODEL=tencent/hy3:free   # or google/gemini-2.5-flash for faster responses
```

---

## Installation

### Option A — one-liner with `uvx` (no install needed)

```bash
uvx hy3-code-review-mcp
```

### Option B — `pip install`

```bash
pip install hy3-code-review-mcp
hy3-code-review-mcp          # starts the MCP server on stdio
```

### Option C — from source

```bash
git clone https://github.com/mkun-dev/hy3-code-review-mcp
cd hy3-code-review-mcp
pip install -e .
hy3-code-review-mcp
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | vLLM / SGLang / OpenRouter endpoint |
| `HY3_API_KEY` | `EMPTY` | API key (`"EMPTY"` for local servers) |
| `HY3_MODEL` | `hy3` | Model name (e.g. `hy3`, `tencent/hy3:free`, `google/gemini-2.5-flash`) |
| `HY3_ALLOWED_ROOTS` | *(unset)* | Optional: colon-separated list of directories `analyze_file` may read |

**Never hard-code API keys.** Pass them via environment variables only.

---

## MCP Client Configuration

Per-client setup guides live in [`docs/clients/`](docs/clients/); ready-to-copy
config templates live in [`examples/clients/`](examples/clients/):

| Client | Guide | Template |
|---|---|---|
| Claude Code | [docs/clients/claude-code.md](docs/clients/claude-code.md) | [examples/clients/claude-code.json](examples/clients/claude-code.json) |
| Cline | [docs/clients/cline.md](docs/clients/cline.md) | [examples/clients/cline.json](examples/clients/cline.json) |
| Cursor | [docs/clients/cursor.md](docs/clients/cursor.md) | [examples/clients/cursor.json](examples/clients/cursor.json) |
| CodeBuddy / WorkBuddy | [docs/clients/codebuddy-workbuddy.md](docs/clients/codebuddy-workbuddy.md) | [examples/clients/codebuddy.mcp.json](examples/clients/codebuddy.mcp.json) |

The common shape is the same everywhere:

```json
{
  "mcpServers": {
    "hy3-code-review": {
      "command": "uvx",
      "args": ["hy3-code-review-mcp"],
      "env": {
        "HY3_BASE_URL": "https://openrouter.ai/api/v1",
        "HY3_API_KEY": "<your-openrouter-api-key>",
        "HY3_MODEL": "tencent/hy3:free"
      }
    }
  }
}
```

> **Windows** — if a client reports `spawn uvx ENOENT`, set `command` to the
> absolute path of `uvx.exe` (find it with `where uvx`). See
> [docs/clients/cline.md](docs/clients/cline.md).

Demo recordings: [`docs/demos/`](docs/demos/).

---

## Available Tools

### `review_diff`

Review a git diff text or `.diff`/`.patch` file.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `diff` | string | one of | — | Raw diff text (takes precedence over `diff_file`) |
| `diff_file` | string | one of | — | Path to `.diff` / `.patch` file |
| `context` | string | no | — | What this change is about |
| `reasoning_effort` | `"no_think"` \| `"low"` \| `"high"` | no | `"high"` | Hy3 reasoning depth |

**Example prompt:**
```
Use hy3-code-review to review_diff with the following diff: <paste diff here>
```

**Example output:**
```markdown
## Summary
This change replaces plain-text password comparison with MD5 hashing...

## Issues Found
- **[Severity: CRITICAL]** `auth/login.py:14` — MD5 is a broken hash algorithm...
  - Suggested fix: Use bcrypt or argon2.
- **[Severity: HIGH]** `auth/login.py:12` — SQL query is vulnerable to injection...

## Verdict
REQUEST CHANGES
```

---

### `analyze_file`

Deep analysis of a single source code file.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `file_path` | string | yes | — | Path to source file |
| `focus` | `"security"` \| `"performance"` \| `"style"` \| `"bugs"` \| `"all"` | no | `"all"` | What to focus on |
| `reasoning_effort` | string | no | `"high"` | Hy3 reasoning depth |

**Example prompt:**
```
Use hy3-code-review analyze_file on ./src/auth/login.py with focus=security
```

---

### `git_diff_review`

Automatically runs `git diff <base_branch>` in a local repo and produces a full review.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `repo_path` | string | yes | — | Absolute path to the git repo |
| `base_branch` | string | no | `"main"` | Base branch to diff against |
| `reasoning_effort` | string | no | `"high"` | Hy3 reasoning depth |

**Example prompt:**
```
Use hy3-code-review git_diff_review for repo_path=/home/user/myproject, base_branch=main
```

---

## Running the Demo

```bash
# Set env vars
export HY3_BASE_URL=http://127.0.0.1:8000/v1
export HY3_API_KEY=EMPTY
export HY3_MODEL=hy3

# Run demo
python examples/demo_review_diff.py
```

Expected output:

```
Available tools: ['review_diff', 'analyze_file', 'git_diff_review']

=== Hy3 Code Review ===

## Summary
This diff upgrades password comparison to use MD5 hashing, but introduces two serious issues...

## Issues Found
- **[Severity: CRITICAL]** `auth/login.py:15` — MD5 is cryptographically broken...
- **[Severity: HIGH]** `auth/login.py:12` — SQL injection vulnerability remains unfixed...

## Verdict
REQUEST CHANGES
```

---

## How It Works

```
MCP Client (Claude Code / CodeBuddy / Cursor / Cline)
        │  stdio transport
        ▼
hy3-code-review-mcp  (this server)
        │
        ├── read local files / run git commands
        │
        └── OpenAI-compatible HTTP call
                    │
                    ▼
            Hy3 API (vLLM / SGLang / OpenRouter)
            reasoning_effort=high
```

- Transport: **stdio** (local, zero network exposure)
- Hy3's `reasoning_effort="high"` is used by default for thorough reviews
- 256K context window handles large diffs and full files without truncation
- All API keys passed via environment variables — nothing hard-coded

---

## Security

- File reads are restricted to `HY3_ALLOWED_ROOTS` if set (path traversal protection)
- `base_branch` is validated against `^[A-Za-z0-9][A-Za-z0-9._/-]*$` (git injection prevention)
- `--no-ext-diff` and `GIT_CONFIG_NOSYSTEM=1` block RCE via malicious repo config
- Plaintext HTTP to non-local hosts triggers a stderr warning
- Errors are sanitized before returning to the client (no internal paths leaked)

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
