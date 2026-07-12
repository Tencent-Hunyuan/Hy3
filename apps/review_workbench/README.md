# Hy3 Review Workbench

A lightweight web workbench for code changes: paste a unified diff and use Hy3 to generate a severity-ranked code review or a focused test plan.

## Demo video

[Watch the 23-second end-to-end demo](assets/demo.mp4).

The recording covers both built-in workflows and is under the two-minute submission limit.

## Hy3's role

Hy3 is the system's core reasoning engine. The application sends the code diff, business context, and review objective to a Hy3 OpenAI-compatible API. Hy3 interprets the change, identifies correctness, security, and reliability risks, explains their impact, and generates test recommendations. The FastAPI layer only validates input, reuses the shared prompt builders, calls the API, and sanitizes errors. It performs no training, fine-tuning, or local inference.

```text
Browser -> FastAPI -> existing prompt builders -> Hy3 API
        <- JSON/Markdown review or test plan <-
```

## Run locally

Python 3.10+ and a Hy3-compatible API endpoint are required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ./mcp_servers/code_review
pip install -r apps/review_workbench/requirements.txt
cp .env.example .env
```

Configure one API provider in `.env`. For example, with OpenRouter:

```bash
HY3_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-...
HY3_MODEL=tencent/hy3:free
HY3_REASONING_EFFORT=no_think
```

Start the application:

```bash
uvicorn apps.review_workbench.app:app --reload --port 8008
```

Open `http://127.0.0.1:8008`. The API key is read server-side from environment variables or `.env`; it is never included in the page, API responses, or error messages.

## Demo 1: Payment security review

Expected duration: about 45 seconds when presented separately.

1. Select `Payment security regression` from `Demo case`.
2. Keep `Code review` and `Balanced`, then click `Run Hy3 review`.
3. Show Hy3's severity-ranked findings for token leakage, unbounded recursive retries, timeout policy, and missing tests.
4. Click `Copy` to demonstrate that the result can be pasted directly into a PR comment.

## Demo 2: Retry test plan

Expected duration: about 45 seconds when presented separately.

1. Select `Retry reliability gap` from `Demo case`; the workbench switches to `Test plan` automatically.
2. Keep `pytest` and `High`, then click `Build test plan`.
3. Show Hy3's recommendations for retry counts, exception categories, backoff, terminal failure, and regression coverage.
4. Briefly resize the window to show the single-column mobile layout.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/status` | Return sanitized model connection status |
| `GET /api/examples` | Return the two deterministic demo diffs |
| `POST /api/review` | Ask Hy3 to generate a code review |
| `POST /api/tests` | Ask Hy3 to generate a test plan |

Each diff is limited to 24,000 characters. Hy3 calls use a 30-second timeout and retry an empty provider response up to two times. An external endpoint without credentials returns `503`; a timeout returns `504`; empty or failed upstream responses return a sanitized `502` response.

## Tests

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q \
  apps/review_workbench/tests \
  mcp_servers/code_review/tests
node --check apps/review_workbench/static/app.js
```

## CodeBuddy collaboration

The following parts of the application were completed with CodeBuddy collaboration:

- `app.py` and `schemas.py`: FastAPI routes, reuse of the Hy3 client, input limits, and sanitized error handling.
- `examples.py`: the payment security review and retry test-plan demos.
- `static/`: the two-mode workbench, responsive layout, safe result formatting, and copy interaction.
- `tests/test_app.py`: API contracts, credential redaction, failure handling, demo data, and static asset coverage.
- This README: setup, Hy3's role, demo flows, and recording instructions.

The existing `mcp_servers/code_review/` implementation remains unchanged. The web application reuses its Hy3 API client and prompt builders.
