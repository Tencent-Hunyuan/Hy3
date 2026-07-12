# Hy3 Review Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, dependency-light Web workbench that sends pasted code diffs to Hy3 for prioritized review or targeted test planning and includes two repeatable demos.

**Architecture:** A standalone FastAPI app under `apps/review_workbench/` serves a dependency-free HTML/CSS/JavaScript interface and JSON APIs. The backend reuses `hy3_code_review_mcp` configuration, Hy3 client, prompt builders, and review functions; the browser receives only model output and non-secret metadata.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Pydantic 2, pytest, FastAPI TestClient/httpx, vanilla HTML/CSS/JavaScript, existing OpenAI-compatible Hy3 client.

## Global Constraints

- Keep all implementation on branch `feat/hy3-review-workbench` until explicitly merged.
- Use Hy3 only through the existing OpenAI-compatible API client; no training, fine-tuning, or local inference implementation.
- Limit each diff to 24,000 characters.
- Do not add authentication, persistence, GitHub OAuth, repository hosting integration, or automatic code modification.
- API keys remain server-side and must never appear in status responses, HTML, JavaScript, logs, or errors.
- Both built-in demos must be runnable in three clicks and suitable for a recording under two minutes.

---

## File Map

- `apps/__init__.py`: marks the application namespace.
- `apps/review_workbench/__init__.py`: exports the FastAPI application package.
- `apps/review_workbench/app.py`: creates FastAPI routes, dependency injection, configuration checks, and upstream error translation.
- `apps/review_workbench/schemas.py`: Pydantic request and public response contracts.
- `apps/review_workbench/examples.py`: deterministic payment and retry demo diffs.
- `apps/review_workbench/static/index.html`: accessible workbench markup.
- `apps/review_workbench/static/styles.css`: restrained responsive visual system.
- `apps/review_workbench/static/app.js`: state, API requests, safe result formatting, examples, copy action, and errors.
- `apps/review_workbench/requirements.txt`: Web runtime and test dependencies.
- `apps/review_workbench/tests/test_app.py`: backend contract and static app tests.
- `apps/review_workbench/README.md`: setup, Hy3 role, demos, architecture, recording checklist, and CodeBuddy contribution record.
- `README.md`, `README_CN.md`: links to the Web workbench.

---

### Task 1: Backend API Contracts And Hy3 Calls

**Files:**
- Create: `apps/__init__.py`
- Create: `apps/review_workbench/__init__.py`
- Create: `apps/review_workbench/schemas.py`
- Create: `apps/review_workbench/app.py`
- Create: `apps/review_workbench/requirements.txt`
- Create: `apps/review_workbench/tests/test_app.py`

**Interfaces:**
- Consumes: `Hy3Settings.from_env()`, `load_default_dotenv()`, `Hy3Client`, `review_patch_with_client(...)`, and `suggest_tests_with_client(...)` from `mcp_servers/code_review/src/hy3_code_review_mcp`.
- Produces: `app: FastAPI`, `get_hy3_client() -> Hy3Client`, `GET /api/status`, `POST /api/review`, and `POST /api/tests`.

- [ ] **Step 1: Add dependencies and write failing endpoint tests**

Create `requirements.txt` with:

```text
-e ../../mcp_servers/code_review
fastapi>=0.115,<1
pydantic>=2.7,<3
uvicorn[standard]>=0.30,<1
httpx>=0.27,<1
pytest>=8,<9
```

Write tests using a fake client and dependency override:

```python
from fastapi.testclient import TestClient

from apps.review_workbench.app import app, get_hy3_client


class FakeHy3Client:
    def complete(self, prompt: str) -> str:
        assert "+ risky_change()" in prompt
        return "## Summary\nHy3 result"


def client() -> TestClient:
    app.dependency_overrides[get_hy3_client] = lambda: FakeHy3Client()
    return TestClient(app)


def test_review_calls_hy3_and_returns_metadata():
    response = client().post(
        "/api/review",
        json={
            "patch_text": "+ risky_change()",
            "language": "python",
            "focus": "security",
            "context": "Payment service",
        },
    )
    assert response.status_code == 200
    assert response.json()["content"] == "## Summary\nHy3 result"
    assert response.json()["metadata"]["language"] == "python"


def test_test_plan_calls_hy3():
    response = client().post(
        "/api/tests",
        json={
            "diff_text": "+ risky_change()",
            "test_framework": "pytest",
            "risk_level": "high",
        },
    )
    assert response.status_code == 200
    assert response.json()["content"].startswith("## Summary")


def test_empty_and_oversized_diffs_are_rejected():
    test_client = client()
    assert test_client.post("/api/review", json={"patch_text": "   "}).status_code == 422
    response = test_client.post("/api/review", json={"patch_text": "+" * 24001})
    assert response.status_code == 422


def test_status_never_exposes_api_key(monkeypatch):
    monkeypatch.setenv("HY3_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("HY3_API_KEY", "super-secret")
    monkeypatch.setenv("HY3_MODEL", "hy3")
    response = client().get("/api/status")
    assert response.status_code == 200
    assert response.json() == {
        "ready": True,
        "model": "hy3",
        "endpoint": "gateway.example",
    }
    assert "super-secret" not in response.text
```

- [ ] **Step 2: Run tests and verify the module is missing**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q apps/review_workbench/tests/test_app.py
```

Expected: collection fails with `ModuleNotFoundError: No module named 'apps.review_workbench.app'`.

- [ ] **Step 3: Implement validated schemas and API routes**

Define constrained requests in `schemas.py`:

```python
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_DIFF_CHARS = 24_000


class ReviewPayload(BaseModel):
    patch_text: str = Field(max_length=MAX_DIFF_CHARS)
    language: str = Field(default="python", max_length=40)
    focus: str = Field(default="correctness, security, reliability, and tests", max_length=240)
    context: str = Field(default="", max_length=1000)

    @field_validator("patch_text")
    @classmethod
    def patch_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("patch_text must not be blank")
        return value


class TestPlanPayload(BaseModel):
    diff_text: str = Field(max_length=MAX_DIFF_CHARS)
    test_framework: str = Field(default="pytest", max_length=40)
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"

    @field_validator("diff_text")
    @classmethod
    def diff_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("diff_text must not be blank")
        return value


class Hy3Response(BaseModel):
    content: str
    metadata: dict[str, Any]


class StatusResponse(BaseModel):
    ready: bool
    model: str
    endpoint: str
```

In `app.py`, load `.env`, build the dependency, use `run_in_threadpool` for the synchronous client, and map response keys. `get_hy3_client()` must reject an external endpoint with an empty or `EMPTY` API key using `HTTPException(status_code=503, detail="Hy3 API is not configured. Add credentials to .env and retry.")`; localhost and `127.0.0.1` endpoints may use `EMPTY`:

```python
async def review(payload: ReviewPayload, client: Hy3Client = Depends(get_hy3_client)) -> Hy3Response:
    started = perf_counter()
    try:
        result = await run_in_threadpool(
            review_patch_with_client,
            payload.patch_text,
            client,
            payload.language,
            payload.focus,
            payload.context,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Hy3 request timed out. Try again.") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Hy3 request failed. Check the endpoint and try again.") from exc
    metadata = {**result["metadata"], "duration_ms": round((perf_counter() - started) * 1000)}
    return Hy3Response(content=result["review"], metadata=metadata)
```

Implement `/api/tests` identically around `suggest_tests_with_client`, using `result["test_suggestions"]`. Implement `/api/status` with `urlparse(settings.base_url).hostname`, and mark localhost endpoints ready when their API key is `EMPTY`; external endpoints require a non-empty, non-`EMPTY` key.

- [ ] **Step 4: Add upstream failure tests and make all endpoint tests pass**

Add:

```python
class FailingHy3Client:
    def complete(self, prompt: str) -> str:
        raise RuntimeError("secret upstream details")


def test_upstream_errors_are_sanitized():
    app.dependency_overrides[get_hy3_client] = lambda: FailingHy3Client()
    response = TestClient(app).post("/api/review", json={"patch_text": "+ change"})
    assert response.status_code == 502
    assert response.json()["detail"] == "Hy3 request failed. Check the endpoint and try again."
    assert "secret upstream details" not in response.text
```

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q apps/review_workbench/tests/test_app.py
```

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit backend API**

```bash
git add apps/__init__.py apps/review_workbench/__init__.py apps/review_workbench/app.py apps/review_workbench/schemas.py apps/review_workbench/requirements.txt apps/review_workbench/tests/test_app.py
git commit -m "feat: add Hy3 review workbench API"
```

---

### Task 2: Built-In Demo Examples

**Files:**
- Create: `apps/review_workbench/examples.py`
- Modify: `apps/review_workbench/app.py`
- Modify: `apps/review_workbench/schemas.py`
- Modify: `apps/review_workbench/tests/test_app.py`

**Interfaces:**
- Consumes: FastAPI `app` and public Pydantic models from Task 1.
- Produces: `EXAMPLES: tuple[DemoExample, ...]` and `GET /api/examples` returning `id`, `title`, `description`, `mode`, `language`, `framework`, `risk_level`, `context`, and `diff_text`.

- [ ] **Step 1: Write a failing examples contract test**

```python
def test_examples_support_both_demo_flows():
    response = client().get("/api/examples")
    assert response.status_code == 200
    examples = response.json()
    assert [item["id"] for item in examples] == ["payment-security", "retry-reliability"]
    assert {item["mode"] for item in examples} == {"review", "tests"}
    assert all(item["diff_text"].startswith("diff --git") for item in examples)
```

- [ ] **Step 2: Run the test and verify a 404**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q apps/review_workbench/tests/test_app.py::test_examples_support_both_demo_flows
```

Expected: FAIL because `/api/examples` returns 404.

- [ ] **Step 3: Implement deterministic examples and route**

Define a frozen `DemoExample` dataclass and two full unified diffs. The payment diff must add token logging and unbounded recursive retries. The retry diff must add a loop that retries every exception without backoff and returns `None` after exhaustion. Return public dictionaries from:

```python
@app.get("/api/examples", response_model=list[DemoExampleResponse])
def examples() -> list[dict[str, str]]:
    return [asdict(example) for example in EXAMPLES]
```

Use literal modes `review` and `tests`, language `python`, framework `pytest`, and risk levels `critical` and `high`.

- [ ] **Step 4: Run examples and complete API tests**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q apps/review_workbench/tests/test_app.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit examples**

```bash
git add apps/review_workbench/examples.py apps/review_workbench/app.py apps/review_workbench/schemas.py apps/review_workbench/tests/test_app.py
git commit -m "feat: add repeatable review demos"
```

---

### Task 3: Interactive Responsive Frontend

**Files:**
- Create: `apps/review_workbench/static/index.html`
- Create: `apps/review_workbench/static/styles.css`
- Create: `apps/review_workbench/static/app.js`
- Modify: `apps/review_workbench/app.py`
- Modify: `apps/review_workbench/tests/test_app.py`

**Interfaces:**
- Consumes: `/api/status`, `/api/examples`, `/api/review`, and `/api/tests` from Tasks 1-2.
- Produces: `GET /`, `GET /static/styles.css`, and `GET /static/app.js`; browser functions `setMode(mode)`, `loadExample(id)`, `submitAnalysis()`, `renderMarkdown(text)`, and `copyResult()`.

- [ ] **Step 1: Write failing static application tests**

```python
def test_root_serves_workbench_without_secrets(monkeypatch):
    monkeypatch.setenv("HY3_API_KEY", "never-render-this")
    response = client().get("/")
    assert response.status_code == 200
    assert "Hy3 Review Workbench" in response.text
    assert 'id="diff-input"' in response.text
    assert 'id="run-button"' in response.text
    assert "never-render-this" not in response.text


def test_static_assets_are_served():
    test_client = client()
    assert test_client.get("/static/styles.css").status_code == 200
    script = test_client.get("/static/app.js")
    assert script.status_code == 200
    assert "submitAnalysis" in script.text
```

- [ ] **Step 2: Run static tests and verify the root route is absent**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q apps/review_workbench/tests/test_app.py -k 'root or static'
```

Expected: failures for missing root content and static assets.

- [ ] **Step 3: Build the semantic workbench markup**

Create a compact header with product name, connection indicator, and model label. Build a `main` with `section.input-panel` and `section.output-panel`. Include:

```html
<div class="mode-switch" role="tablist" aria-label="Analysis mode">
  <button class="mode-button is-active" data-mode="review" role="tab" aria-selected="true">Code review</button>
  <button class="mode-button" data-mode="tests" role="tab" aria-selected="false">Test plan</button>
</div>
<select id="example-select" aria-label="Load demo example"></select>
<textarea id="diff-input" spellcheck="false" maxlength="24000" aria-label="Code diff"></textarea>
<button id="run-button" type="button">Run Hy3 review</button>
<article id="result" aria-live="polite"></article>
```

Include editable language/framework, focus/risk, and context fields whose visibility follows the current mode. Load only local CSS and JavaScript files.

- [ ] **Step 4: Implement stable responsive styles**

Use a neutral near-white canvas, charcoal text, white tool surfaces, emerald success, amber warning, and red error accents. Keep cards at `8px` radius or less, use fixed control heights, zero letter spacing, a two-column `minmax(0, 1fr)` grid above 900px, and a single column below 900px. Ensure the textarea and result have `min-height: 420px` on desktop and 300px on mobile; never hide overflow that contains user output.

- [ ] **Step 5: Implement browser state and safe output rendering**

Fetch status and examples on `DOMContentLoaded`. The submit function chooses endpoint and payload by mode:

```javascript
async function submitAnalysis() {
  const diff = elements.diffInput.value.trim();
  if (!diff) return showError("Paste a diff or load an example first.");
  setLoading(true);
  try {
    const isReview = state.mode === "review";
    const response = await fetch(isReview ? "/api/review" : "/api/tests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(isReview ? reviewPayload(diff) : testPayload(diff)),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(errorMessage(body));
    state.lastResult = body.content;
    renderResult(body.content, body.metadata);
  } catch (error) {
    showError(error.message || "The request failed. Try again.");
  } finally {
    setLoading(false);
  }
}
```

`renderMarkdown` must first replace `&`, `<`, `>`, `"`, and `'` with HTML entities, then support fenced code blocks, headings, unordered/ordered list lines, inline code, and bold text. Never inject unescaped model text into `innerHTML`. Copy with `navigator.clipboard.writeText(state.lastResult)` and show a temporary `Copied` label without resizing the button.

- [ ] **Step 6: Mount assets and make tests pass**

In `app.py`:

```python
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
```

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q apps/review_workbench/tests/test_app.py
node --check apps/review_workbench/static/app.js
```

Expected: all tests pass and Node reports no syntax errors.

- [ ] **Step 7: Commit frontend**

```bash
git add apps/review_workbench/app.py apps/review_workbench/static apps/review_workbench/tests/test_app.py
git commit -m "feat: add interactive Hy3 review UI"
```

---

### Task 4: Documentation, Demo Script, And Full Verification

**Files:**
- Create: `apps/review_workbench/README.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `apps/review_workbench/tests/test_app.py`

**Interfaces:**
- Consumes: launch target `apps.review_workbench.app:app` and both built-in demo IDs.
- Produces: reproducible install/launch instructions, two sub-two-minute demo scripts, Hy3 role statement, and CodeBuddy collaboration disclosure.

- [ ] **Step 1: Add a failing documentation completeness test**

```python
from pathlib import Path


def test_app_readme_documents_required_submission_details():
    readme = Path("apps/review_workbench/README.md").read_text(encoding="utf-8")
    required = [
        "Hy3's role",
        "Demo 1",
        "Demo 2",
        "CodeBuddy collaboration",
        "uvicorn apps.review_workbench.app:app",
    ]
    assert all(item in readme for item in required)
```

- [ ] **Step 2: Run the test and verify README is missing**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q apps/review_workbench/tests/test_app.py::test_app_readme_documents_required_submission_details
```

Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Write application and root documentation**

Document these exact commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r apps/review_workbench/requirements.txt
cp .env.example .env
uvicorn apps.review_workbench.app:app --reload --port 8008
```

Explain that Hy3 receives the diff, reasons about code risk, produces prioritized findings, and generates tests; FastAPI only validates and transports the request. Include Demo 1 steps (`payment-security` -> Review -> Run) and Demo 2 steps (`retry-reliability` -> Test plan -> Run), each with expected output themes and a recording checklist. List the files and functional blocks created through CodeBuddy collaboration. Add a short Workbench section and relative link in both root READMEs.

- [ ] **Step 4: Run all automated checks**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q apps/review_workbench/tests mcp_servers/code_review/tests
python -m py_compile apps/review_workbench/*.py mcp_servers/code_review/src/hy3_code_review_mcp/*.py
node --check apps/review_workbench/static/app.js
git diff --check
```

Expected: all tests pass, compilation and JavaScript syntax checks are silent, and `git diff --check` reports no errors.

- [ ] **Step 5: Start and visually smoke-test the application**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. uvicorn apps.review_workbench.app:app --host 127.0.0.1 --port 8008
```

Verify at `http://127.0.0.1:8008` on 1440x900 and 390x844 viewports: no overlap or horizontal page scroll; both examples populate all relevant controls; mode switching is stable; unconfigured status is understandable; review/test requests show loading, success, and sanitized error states; copy state does not shift layout.

- [ ] **Step 6: Commit documentation and final verification changes**

```bash
git add README.md README_CN.md apps/review_workbench/README.md apps/review_workbench/tests/test_app.py
git commit -m "docs: add Hy3 workbench demo guide"
git status --short
```

Expected: commit succeeds and status is clean.
