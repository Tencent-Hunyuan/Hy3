# Hy3 Incident Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Web Agent that lets Hy3 investigate trusted incident files by planning, calling four bounded local tools, and streaming a grounded root-cause report.

**Architecture:** FastAPI validates multipart input and owns a per-request temporary workspace. A testable Hy3 chat client drives an eight-round tool-calling loop over `list_files`, `search_files`, `read_file`, and `run_checks`; an NDJSON stream exposes progress to a dependency-free browser UI.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic 2, OpenAI Python SDK, python-multipart, pytest, vanilla HTML/CSS/JavaScript.

## Global Constraints

- Keep all changes on `feat/hy3-review-workbench` and preserve unrelated user modifications.
- Use Hy3 only through the configured OpenAI-compatible API; no training, fine-tuning, or local inference.
- Accept at most 8 UTF-8 text files, 512 KiB each and 2 MiB total.
- Accept only `.py`, `.txt`, `.log`, `.json`, `.yaml`, `.yml`, `.toml`, and `.md`.
- Allow only `list_files`, `search_files`, `read_file`, and `run_checks`; never invoke a shell command string.
- Limit the Agent to 8 tool rounds, each check to 20 seconds, and each observation to 12,000 characters.
- Treat uploaded executable code as trusted input and state this boundary in the UI and README.
- Remove the temporary workspace on success, error, timeout, or stream cancellation.

---

## File Map

- `apps/incident_agent/__init__.py`: package marker.
- `apps/incident_agent/demos.py`: immutable demo incidents and text files.
- `apps/incident_agent/workspace.py`: upload validation and temporary workspace lifecycle.
- `apps/incident_agent/tools.py`: safe path resolution, four tool implementations, dispatcher, and OpenAI tool definitions.
- `apps/incident_agent/agent.py`: Hy3 client adapter and streaming investigation loop.
- `apps/incident_agent/schemas.py`: public demo/status models.
- `apps/incident_agent/app.py`: FastAPI routes, multipart handling, static serving, and NDJSON encoding.
- `apps/incident_agent/static/index.html`: Agent workspace markup.
- `apps/incident_agent/static/styles.css`: responsive operational UI.
- `apps/incident_agent/static/app.js`: demo loading, uploads, NDJSON parsing, trace rendering, cancellation, and copy.
- `apps/incident_agent/requirements.txt`: runtime and test dependencies.
- `apps/incident_agent/tests/test_workspace.py`: validation and cleanup tests.
- `apps/incident_agent/tests/test_tools.py`: tool boundary and subprocess tests.
- `apps/incident_agent/tests/test_agent.py`: multi-round orchestration tests.
- `apps/incident_agent/tests/test_app.py`: HTTP, stream, demo, and static tests.
- `apps/incident_agent/README.md`: English setup, architecture, safety, demos, and collaboration record.
- `README.md`, `README_CN.md`: links to the Incident Agent.

---

### Task 1: Temporary Workspace And Demo Incidents

**Files:**
- Create: `apps/incident_agent/__init__.py`
- Create: `apps/incident_agent/demos.py`
- Create: `apps/incident_agent/workspace.py`
- Create: `apps/incident_agent/requirements.txt`
- Create: `apps/incident_agent/tests/test_workspace.py`

**Interfaces:**
- Produces: `DemoIncident`, `DEMOS`, `get_demo(demo_id)`, `validate_files(files)`, and `incident_workspace(files)`.
- `files` is `Sequence[tuple[str, bytes]]`, preserving duplicate names for validation; the workspace context yields a `pathlib.Path`.

- [ ] **Step 1: Write failing workspace and demo tests**

```python
from pathlib import Path

import pytest

from apps.incident_agent.demos import DEMOS, get_demo
from apps.incident_agent.workspace import WorkspaceError, incident_workspace, validate_files


def test_two_demos_cover_retry_and_worker_incidents():
    assert [demo.id for demo in DEMOS] == ["retry-regression", "worker-startup"]
    assert "test_client.py" in get_demo("retry-regression").files
    assert "startup.log" in get_demo("worker-startup").files


def test_workspace_writes_utf8_files_and_cleans_up():
    with incident_workspace([("service.py", b"value = 1\n")]) as root:
        saved_root = root
        assert (root / "service.py").read_text() == "value = 1\n"
    assert not saved_root.exists()


@pytest.mark.parametrize("name", ["../secret.py", "nested/file.py", "binary.exe"])
def test_invalid_names_are_rejected(name):
    with pytest.raises(WorkspaceError):
        validate_files([(name, b"text")])


def test_binary_and_limits_are_rejected():
    with pytest.raises(WorkspaceError):
        validate_files([("bad.txt", b"\x00binary")])
    with pytest.raises(WorkspaceError):
        validate_files([(f"{index}.txt", b"x") for index in range(9)])
    with pytest.raises(WorkspaceError):
        validate_files([("large.txt", b"x" * (512 * 1024 + 1))])
    with pytest.raises(WorkspaceError):
        validate_files([("same.txt", b"one"), ("same.txt", b"two")])
```

- [ ] **Step 2: Run tests and verify imports fail**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests/test_workspace.py
```

Expected: collection fails because `apps.incident_agent` does not exist.

- [ ] **Step 3: Implement immutable demos**

Create `DemoIncident(id, title, summary, task, files)` as a frozen dataclass. The retry demo contains `client.py`, `test_client.py`, and `incident.log`; its client performs `retries + 1` attempts while the test expects exactly `retries`. The worker demo contains `config.py` reading `WORKER_QUEUE`, `deployment.toml` and `environment.txt` setting `WORKER_QUEUE_NAME`, and `startup.log` showing `KeyError: WORKER_QUEUE`.

`get_demo` must return a matching demo or raise `KeyError("Unknown demo: <id>")`.

Create `requirements.txt` with:

```text
-e ../../mcp_servers/code_review
fastapi>=0.115,<1
pydantic>=2.7,<3
python-multipart>=0.0.9,<1
uvicorn[standard]>=0.30,<1
httpx>=0.27,<1
pytest>=8,<10
```

- [ ] **Step 4: Implement bounded workspace validation**

```python
ALLOWED_EXTENSIONS = {".py", ".txt", ".log", ".json", ".yaml", ".yml", ".toml", ".md"}
MAX_FILES = 8
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024


def validate_files(files: Sequence[tuple[str, bytes]]) -> dict[str, str]:
    if not files or len(files) > MAX_FILES:
        raise WorkspaceError("Provide between 1 and 8 files.")
    decoded = {}
    total = 0
    for raw_name, content in files:
        name = Path(raw_name).name
        if name != raw_name or not name or Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise WorkspaceError(f"Unsupported filename: {raw_name}")
        if name in decoded:
            raise WorkspaceError(f"Duplicate filename: {name}")
        if len(content) > MAX_FILE_BYTES:
            raise WorkspaceError(f"File is larger than 512 KiB: {name}")
        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise WorkspaceError("Files exceed the 2 MiB total limit.")
        if b"\x00" in content:
            raise WorkspaceError(f"Binary content is not supported: {name}")
        try:
            decoded[name] = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError(f"File is not valid UTF-8: {name}") from exc
    return decoded
```

Use `TemporaryDirectory(prefix="hy3-incident-")` in a context manager, write validated text with UTF-8, yield its path, and rely on the context manager for every cleanup path.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests/test_workspace.py
git add apps/incident_agent/__init__.py apps/incident_agent/demos.py apps/incident_agent/workspace.py apps/incident_agent/requirements.txt apps/incident_agent/tests/test_workspace.py
git commit -m "feat: add incident demo workspaces"
```

Expected: all Task 1 tests pass.

---

### Task 2: Bounded Investigation Tools

**Files:**
- Create: `apps/incident_agent/tools.py`
- Create: `apps/incident_agent/tests/test_tools.py`

**Interfaces:**
- Consumes: a temporary workspace `Path` from Task 1.
- Produces: `ToolResult(ok: bool, content: str)`, `TOOL_DEFINITIONS`, `execute_tool(root, name, arguments)`, and the four tool functions.

- [ ] **Step 1: Write failing tool tests**

```python
def test_list_search_and_read_are_relative(tmp_path):
    (tmp_path / "service.py").write_text("alpha = 1\nneedle = alpha\n")
    assert "service.py" in list_files(tmp_path).content
    assert "service.py:2" in search_files(tmp_path, "needle").content
    assert "2: needle = alpha" in read_file(tmp_path, "service.py", 2, 2).content


def test_path_traversal_and_unknown_tools_are_rejected(tmp_path):
    assert not read_file(tmp_path, "../secret.txt").ok
    assert not execute_tool(tmp_path, "shell", {"command": "rm -rf /"}).ok


def test_pytest_check_returns_bounded_failure_output(tmp_path):
    (tmp_path / "test_failure.py").write_text("def test_failure():\n    assert False\n")
    result = run_checks(tmp_path, "pytest")
    assert not result.ok
    assert "1 failed" in result.content


def test_py_compile_and_unsupported_check(tmp_path):
    (tmp_path / "valid.py").write_text("value = 1\n")
    assert run_checks(tmp_path, "py_compile").ok
    assert not run_checks(tmp_path, "bash").ok


def test_check_timeout_is_reported(tmp_path, monkeypatch):
    def expire(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 20)
    monkeypatch.setattr(subprocess, "run", expire)
    result = run_checks(tmp_path, "pytest")
    assert not result.ok
    assert "timed out after 20 seconds" in result.content
```

- [ ] **Step 2: Run tests and verify the tools module is missing**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests/test_tools.py
```

Expected: collection fails for `apps.incident_agent.tools`.

- [ ] **Step 3: Implement path-safe file tools**

Resolve requested paths with `(root / relative).resolve()` and require `resolved.is_relative_to(root.resolve())`. List only files, sorted by relative path. Search case-insensitively with literal substring matching and emit `path:line: text`. Read one-based line ranges with defaults `1..200`, reject reversed/out-of-range values, and prefix each returned line with its number.

All observations pass through `bounded(text, limit=12_000)`, which appends `\n...[output truncated]` when needed.

- [ ] **Step 4: Implement allowlisted checks and dispatcher**

```python
CHECK_COMMANDS = {
    "pytest": lambda root: [sys.executable, "-m", "pytest", "-q"],
    "py_compile": lambda root: [
        sys.executable,
        "-m",
        "py_compile",
        *sorted(str(path.relative_to(root)) for path in root.rglob("*.py")),
    ],
}


def run_checks(root: Path, check: str) -> ToolResult:
    factory = CHECK_COMMANDS.get(check)
    if factory is None:
        return ToolResult(False, f"Unsupported check: {check}")
    command = factory(root)
    if check == "py_compile" and len(command) == 3:
        return ToolResult(False, "No Python files were provided.")
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            env=safe_environment(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(False, "Check timed out after 20 seconds.")
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    return ToolResult(completed.returncode == 0, bounded(output or "Check completed with no output."))
```

`execute_tool` accepts already-parsed dictionaries, validates expected scalar types, dispatches the four exact names, catches validation exceptions, and returns an unsuccessful `ToolResult` rather than raising.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests/test_tools.py
git add apps/incident_agent/tools.py apps/incident_agent/tests/test_tools.py
git commit -m "feat: add bounded incident tools"
```

Expected: all Task 2 tests pass.

---

### Task 3: Hy3 Tool-Calling Loop

**Files:**
- Create: `apps/incident_agent/agent.py`
- Create: `apps/incident_agent/tests/test_agent.py`

**Interfaces:**
- Consumes: `TOOL_DEFINITIONS` and `execute_tool` from Task 2, plus existing `Hy3Settings` and `.env` loading.
- Produces: `AgentToolCall`, `AgentMessage`, `AgentChatClient`, `OpenAIHy3AgentClient`, `get_agent_client()`, and `investigate(task, root, client, max_rounds=8)` yielding event dictionaries.

- [ ] **Step 1: Write failing multi-round Agent tests**

Use a fake client returning these messages in order:

```python
AgentMessage("I will inspect the files first.", [
    AgentToolCall("call-1", "list_files", "{}")
])
AgentMessage(None, [
    AgentToolCall("call-2", "read_file", '{"path":"service.py","start_line":1,"end_line":20}')
])
AgentMessage("## Root cause\nThe evidence is in `service.py:1`.", [])
```

Assert event types are `started`, `plan`, `tool_call`, `tool_result`, `tool_call`, `tool_result`, `report`, `done`; assert tool messages are added to subsequent fake-client calls. Add tests for malformed JSON becoming an unsuccessful tool result and max-round synthesis calling the client once more with no tools.

- [ ] **Step 2: Run tests and verify the Agent module is missing**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests/test_agent.py
```

Expected: collection fails for `apps.incident_agent.agent`.

- [ ] **Step 3: Implement the client adapter**

`OpenAIHy3AgentClient.complete(messages, tools)` calls `client.chat.completions.create` with model/settings, `temperature`, `top_p`, `max_tokens`, tool definitions when present, and the same reasoning body mapping as the existing client. Convert SDK tool calls into immutable `AgentToolCall(id, name, arguments)` values and return `AgentMessage(content, tool_calls)`.

- [ ] **Step 4: Implement deterministic event orchestration**

Start with a system message requiring evidence, filenames/lines, a short visible plan, and final sections `Root cause`, `Evidence`, `Remediation`, and `Verification`. Add a user message with task and output from `list_files`.

For each assistant message, append a serializable assistant message including tool calls. Emit the first nonempty content accompanying tool calls as `plan`. Parse each call's JSON object, emit `tool_call`, execute it, emit `tool_result` with `ok` and bounded content, then append a `role=tool` message. Content without calls is `report` and terminates. At the round limit, append a final synthesis instruction and call with `tools=None`. Catch client exceptions into a sanitized `error` event and always emit `done`.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests/test_agent.py apps/incident_agent/tests/test_tools.py
git add apps/incident_agent/agent.py apps/incident_agent/tests/test_agent.py
git commit -m "feat: add Hy3 incident investigation loop"
```

Expected: Agent and tool tests pass.

---

### Task 4: Streaming FastAPI Endpoint

**Files:**
- Create: `apps/incident_agent/schemas.py`
- Create: `apps/incident_agent/app.py`
- Create: `apps/incident_agent/tests/test_app.py`

**Interfaces:**
- Consumes: demos/workspace from Task 1 and `investigate`/`get_agent_client` from Task 3.
- Produces: `app`, `GET /api/status`, `GET /api/demos`, `POST /api/investigate`, and static root `/`.

- [ ] **Step 1: Write failing API and stream tests**

```python
def test_demos_are_public_without_file_contents():
    response = client().get("/api/demos")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["retry-regression", "worker-startup"]
    assert "files" not in response.text


def test_demo_investigation_streams_ndjson():
    response = client(FakeAgentClient()).post(
        "/api/investigate",
        data={"task": "Find the regression", "demo_id": "retry-regression"},
    )
    events = [json.loads(line) for line in response.text.splitlines()]
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert events[0]["type"] == "started"
    assert events[-1]["type"] == "done"


def test_upload_validation_happens_before_streaming():
    response = client().post(
        "/api/investigate",
        data={"task": "Inspect this"},
        files={"files": ("unsafe.exe", b"binary", "application/octet-stream")},
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
```

- [ ] **Step 2: Run tests and verify API module is missing**

Run:

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests/test_app.py
```

Expected: collection fails for `apps.incident_agent.app`.

- [ ] **Step 3: Implement public schemas and routes**

Create `DemoResponse(id, title, summary, task)` and the same sanitized status fields as Review Workbench. `GET /api/demos` returns metadata only.

`POST /api/investigate` accepts `task: Form`, optional `demo_id: Form`, and `files: list[UploadFile]`. Require a nonblank task of at most 2,000 characters. Reject simultaneous demo/files, unknown demos, missing files, unsupported uploads, and configured limits with `HTTPException(422, detail=<WorkspaceError message>)` before returning a stream.

- [ ] **Step 4: Implement workspace-owned NDJSON streaming**

```python
def event_stream(task: str, raw_files: Sequence[tuple[str, bytes]], client: AgentChatClient):
    with incident_workspace(raw_files) as root:
        for event in investigate(task, root, client):
            yield json.dumps(event, ensure_ascii=False) + "\n"


return StreamingResponse(
    event_stream(effective_task, raw_files, client),
    media_type="application/x-ndjson",
    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
)
```

Mount only the app's local static directory and serve its `index.html` at `/`.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests
git add apps/incident_agent/app.py apps/incident_agent/schemas.py apps/incident_agent/tests/test_app.py
git commit -m "feat: stream Hy3 incident investigations"
```

Expected: all Incident Agent backend tests pass.

---

### Task 5: Interactive UI, Documentation, And Full Verification

**Files:**
- Create: `apps/incident_agent/static/index.html`
- Create: `apps/incident_agent/static/styles.css`
- Create: `apps/incident_agent/static/app.js`
- Create: `apps/incident_agent/README.md`
- Modify: `apps/incident_agent/tests/test_app.py`
- Modify: `README.md`
- Modify: `README_CN.md`

**Interfaces:**
- Consumes: all Task 4 endpoints and NDJSON event types.
- Produces: a responsive Agent UI, English submission documentation, and root discovery links.

- [ ] **Step 1: Add failing static and documentation tests**

Assert `/` contains `Hy3 Incident Agent`, `id="task-input"`, `id="run-button"`, and `id="timeline"`; assert local CSS/JS return 200 and JavaScript contains `readEventStream`. Assert the README contains `Hy3's role`, `Trusted code warning`, both demo titles, `CodeBuddy collaboration`, and `uvicorn apps.incident_agent.app:app`.

- [ ] **Step 2: Run tests and verify missing assets**

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests/test_app.py -k 'static or readme'
```

Expected: failures for missing index/static files and README.

- [ ] **Step 3: Build the operational UI**

Create a compact Hy3-branded header, a left input panel, and a right timeline/report panel. Include a demo select, task textarea, multi-file input, selected-file list, trusted-code warning, stable run/cancel button, status indicator, empty/loading/error states, collapsible tool results, and copy-report action. Use a restrained neutral palette with emerald status, amber running, and red errors; cards use at most 8px radius. Use a two-column grid above 900px and one column below it with stable minimum heights and no horizontal page overflow.

- [ ] **Step 4: Implement streamed browser interaction**

Build `FormData`, call `/api/investigate` with an `AbortController`, and parse `response.body.getReader()` chunks by newline. `readEventStream` retains an incomplete trailing buffer. Render each event with DOM creation and `textContent`; format the final report only after escaping HTML. `tool_call` creates a pending timeline card, `tool_result` resolves the matching card, `error` preserves earlier cards, and `done` resets controls. Demo selection fills the task and disables uploads; selecting files clears the demo. Cancel aborts the request without clearing completed trace.

- [ ] **Step 5: Write English docs and root links**

Document setup, `.env`, `uvicorn apps.incident_agent.app:app --reload --port 8010`, Hy3's planning/tool-selection role, each tool, the trusted-code warning, both demos, a sub-two-minute recording script, tests, and CodeBuddy collaboration. Add a concise Incident Agent section to both root READMEs without changing unrelated content.

- [ ] **Step 6: Run full verification**

```bash
PYTHONPATH=mcp_servers/code_review/src:. python -m pytest -q apps/incident_agent/tests apps/review_workbench/tests mcp_servers/code_review/tests
python -m py_compile apps/incident_agent/*.py apps/review_workbench/*.py mcp_servers/code_review/src/hy3_code_review_mcp/*.py
node --check apps/incident_agent/static/app.js
node --check apps/review_workbench/static/app.js
git diff --check
```

Expected: all tests pass and syntax/diff checks are silent.

- [ ] **Step 7: Commit only Agent-owned and requested documentation files**

```bash
git add apps/incident_agent README.md README_CN.md apps/review_workbench/README.md apps/review_workbench/assets/demo.mp4
git commit -m "feat: add Hy3 incident agent application"
```

Before committing, inspect `git diff --cached --stat` and ensure user-deleted design/plan files and unrelated user modifications are not staged.
