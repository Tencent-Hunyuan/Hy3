# Trae and CodeBuddy MCP Configuration

Trae and CodeBuddy use the same local stdio MCP server configuration. Keep one shared template and paste it into whichever client UI or project config you use.

The current hands-on examples are scoped to Trae and CodeBuddy. Cursor, Qoder, Cline, WorkBuddy, and other vibe-coding clients are not claimed as practiced yet.

## Install

From the Hy3 repository root:

```bash
conda activate llms
pip install -e ./mcp_servers/code_review[dev]
```

Confirm the package is installed in the conda environment:

```bash
python -c "import hy3_code_review_mcp; print(hy3_code_review_mcp.__file__)"
```

## Configure API Credentials

Create `.env` in the Hy3 repository root:

```bash
cp .env.example .env
```

For OpenRouter:

```bash
HY3_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-...
HY3_MODEL=tencent/hy3:free
HY3_REASONING_EFFORT=no_think
```

For local vLLM/SGLang:

```bash
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
HY3_REASONING_EFFORT=no_think
```

Do not paste API keys into client MCP config. The server reads them from `HY3_ENV_FILE`.

## Shared MCP Config

Use `examples/trae-codebuddy.mcp.json` as the template:

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

On this machine, after `conda activate llms`, `which python` returns:

```text
/opt/miniconda3/envs/llms/bin/python
```

So the local config can use:

```json
{
  "mcpServers": {
    "hy3-code-review": {
      "command": "/opt/miniconda3/envs/llms/bin/python",
      "args": ["-m", "hy3_code_review_mcp.server"],
      "env": {
        "HY3_ENV_FILE": "/Volumes/KimariYB Disk/Project/tencent/Hy3/.env"
      }
    }
  }
}
```

## Client Notes

Trae:

- Add the shared server block through Trae's MCP settings UI or project-level MCP config if your version supports it.
- Use the same command, args, and `HY3_ENV_FILE` environment variable.

CodeBuddy:

- CodeBuddy's local MCP config commonly lives at `~/.codebuddy/mcp.json`.
- Merge the `hy3-code-review` entry under `mcpServers`, or add the same stdio server through CodeBuddy's UI if available.

## Tool Call Demo

Prompt:

```text
Use hy3-code-review to review this demo code.
Call review_patch with:
- patch_text: use the diff returned by build_demo_patch() from mcp_servers/code_review/examples/review_demo_payment.py
- language: python
- focus: security, correctness, reliability, and missing tests
- context: Payment service helper that charges a user's saved payment token.
```

Expected tool:

```json
{
  "tool": "review_patch",
  "arguments": {
    "patch_text": "diff --git a/payment.py b/payment.py\nindex 1111111..2222222 100644\n--- a/payment.py\n+++ b/payment.py\n@@ -1,8 +1,20 @@\n import requests\n \n def charge_user(user_id, amount, token):\n+    print(\"charging\", user_id, amount, token)\n     response = requests.post(\n         \"https://payments.example.com/charge\",\n         json={\"user_id\": user_id, \"amount\": amount, \"token\": token},\n+        timeout=1,\n     )\n+    if response.status_code >= 500:\n+        return charge_user(user_id, amount, token)\n     response.raise_for_status()\n     return response.json()\n",
    "language": "python",
    "focus": "security, correctness, reliability, and missing tests",
    "context": "Payment service helper that charges a user's saved payment token."
  }
}
```

## Actual Trae Output

The following result was captured from Trae after calling the `hy3-code-review` MCP server on `examples/review_demo_payment.py`.

```markdown
Review Results

Blocker

- Sensitive data exposure via print - `print("charging", user_id, amount, token)` writes the payment token to stdout/logs. Tokens are secrets; this violates PCI/security best practices. Remove it or use redacted logging (`token[:4] + "****"`).
- Unbounded recursive retry on 5xx - `return charge_user(...)` with no limit or backoff causes infinite recursion / stack overflow and amplifies load on a failing gateway.

Major

- Non-idempotent retry correctness - Retrying on 5xx without an idempotency key can double-charge if the gateway processed but returned an error. Send an `Idempotency-Key` header.
- Hardcoded 1s timeout too low - May abort legitimate slow charges. Make it configurable, for example 5-10 seconds.

Minor / Nit

- No input validation (`amount > 0`, token format).
- Missing docstring/type hints.

Missing tests

- No unit tests mocking `requests.post` for success path, 4xx `raise_for_status`, 5xx retry bounded behavior, timeout handling, and token redaction.
- No integration or contract tests.

Concrete fix

Use `requests.Session` with `Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])`, add an `Idempotency-Key` header via `uuid4()`, validate input, make timeout a parameter, drop the print, and add pytest tests.
```
