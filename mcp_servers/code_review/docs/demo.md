# Demo Script

Use this script to record the required demo GIF or video.

## Setup

```bash
pip install ./mcp_servers/code_review
cp .env.example .env
```

Edit `.env` with a working Hy3 endpoint and API key.

## Demo 1: Trae

1. Add `mcp_servers/code_review/examples/trae-codebuddy.mcp.json` to Trae's MCP settings.
2. Open this repository and use `mcp_servers/code_review/examples/review_demo_payment.py` as the review target.
3. Ask:

```text
Use hy3-code-review to review this demo code.
Call review_patch with the diff returned by build_demo_patch() from mcp_servers/code_review/examples/review_demo_payment.py.
Focus on security, correctness, reliability, and missing tests.
```

4. Show the `review_patch` tool call and Hy3 review response.

## Demo 2: CodeBuddy

1. Add `mcp_servers/code_review/examples/trae-codebuddy.mcp.json` to CodeBuddy's MCP settings, or merge the same server entry into `~/.codebuddy/mcp.json`.
2. Ask:

```text
Use hy3-code-review to suggest pytest coverage for the review_demo_payment.py diff.
Call suggest_tests with risk_level "high".
```

3. Show the tool call arguments and test suggestions.

## Client Scope

This branch documents practical setup for Trae and CodeBuddy only. Cursor, Qoder, Cline, WorkBuddy, and other vibe-coding clients may support a similar MCP stdio config, but they have not been practiced here yet.

## Real OpenRouter Smoke Test Output

The following output was captured from a successful `review_patch` call through the same Hy3/OpenRouter-compatible path. A later repeat attempt on 2026-07-08 hit OpenRouter `502` responses, so keep this fixture as a known-good example and rerun when the upstream endpoint is healthy.

Tool request:

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

Response parsing:

```json
{
  "review": "<markdown review text>",
  "metadata": {
    "language": "python",
    "focus": "security, correctness, reliability, and missing tests",
    "diff_chars": 574
  }
}
```

Example model output:

```markdown
## Summary

The change adds logging, a one-second timeout, and recursive retry behavior around a payment charge request. It introduces a blocker security leak and major reliability/correctness risks in a payment path.

## Findings ordered by severity

- blocker - `payment.py:charge_user` logs the raw payment token with `print("charging", user_id, amount, token)`. This can expose sensitive payment credentials in stdout, container logs, CI logs, and centralized logging systems. It is a direct credential leak and likely violates payment data handling requirements.
- major - `payment.py:charge_user` retries 5xx responses with unbounded recursion. A persistent upstream outage can exhaust the Python stack, keep workers occupied, and amplify traffic to the payment provider.
- major - The retry path can duplicate charges because the request has no idempotency key and blindly repeats the same payment operation after a 5xx. A provider may process the original request even when the client receives a server error.
- minor - `timeout=1` is hard-coded and very aggressive for a payment provider. This can create false timeouts under normal network variance and increase the chance of duplicate retry behavior.

## Missing or weak tests

- Add a test proving sensitive values such as `token` are not printed or logged.
- Add tests for 5xx responses to verify bounded retry behavior and backoff.
- Add a regression test for idempotency headers or request identifiers on retry.
- Add timeout handling tests so network failures return a controlled error instead of recursively retrying forever.

## Concrete fix suggestions

- Remove token logging. If logging is required, log a request id, user id, amount, and a redacted token suffix only when policy allows it.
- Replace recursion with a bounded retry loop using exponential backoff and jitter.
- Send an idempotency key with the charge request and reuse it across retries.
- Make timeout configurable and handle `requests.Timeout` and `requests.RequestException` explicitly.
```

## Actual Trae Client Output

This output was captured from Trae after calling the MCP server with `review_patch` on `mcp_servers/code_review/examples/review_demo_payment.py`.

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

## Output to Attach

Attach the generated GIF/video to the PR or issue comment. The repository intentionally does not commit large binary demo files.
