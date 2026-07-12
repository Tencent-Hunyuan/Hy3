# Hy3 Incident Agent Design

## Goal

Build a standalone web application that demonstrates Hy3 solving an engineering incident through iterative planning, tool selection, evidence gathering, and a grounded final report. The implementation must remain small enough to complete and polish in one day.

## Scope

The application accepts an incident description and trusted text files, then lets Hy3 investigate them with a fixed local tool set. It includes two deterministic demo incidents and streams the investigation trace to the browser.

The application does not provide arbitrary shell access, persistent storage, authentication, repository hosting integrations, autonomous code modification, training, fine-tuning, or local model inference.

## Architecture

Add an independent package under `apps/incident_agent/`. Its FastAPI server owns upload validation, temporary workspace creation, safe tool execution, the Hy3 tool-calling loop, and an NDJSON streaming endpoint. A dependency-free HTML/CSS/JavaScript frontend renders the task form, live tool trace, and final report.

The Agent uses the same environment variables and `.env` loading behavior as the existing code-review applications. Hy3 is called through the configured OpenAI-compatible API and decides which tools to invoke. Local code validates each tool request, executes only an allowed operation, and returns bounded observations to Hy3.

The Incident Agent remains separate from `apps/review_workbench/`; the two applications share configuration conventions but no frontend state or routes.

## Components

- `app.py`: FastAPI application, static routes, demo metadata, multipart upload validation, and streaming response.
- `agent.py`: Hy3 chat-completions tool loop, event protocol, round limit, final synthesis, and upstream error translation.
- `tools.py`: workspace path validation and implementations for `list_files`, `search_files`, `read_file`, and `run_checks`.
- `workspace.py`: upload limits, filename normalization, UTF-8 validation, temporary directory lifecycle, and demo material creation.
- `demos.py`: two deterministic incident descriptions and their source, test, log, and configuration files.
- `schemas.py`: demo metadata and stream-event contracts.
- `static/index.html`: incident input, demo selection, file picker, execution trace, and report regions.
- `static/styles.css`: responsive operational-tool layout.
- `static/app.js`: multipart submission, NDJSON parsing, event rendering, cancellation, and copy action.

## Tool Contract

Hy3 can request four tools:

1. `list_files`: list normalized relative file paths and byte sizes in the current workspace.
2. `search_files`: search UTF-8 files for a literal query with optional extension filtering; return at most 80 matches and 12,000 characters.
3. `read_file`: read a normalized relative path using one-based start/end lines; return at most 300 lines and 12,000 characters.
4. `run_checks`: execute either `pytest` or `py_compile` using fixed argument arrays, a sanitized environment, a 20-second timeout, and 12,000-character output limit.

Tool arguments are parsed from JSON and validated before execution. Unknown tools, malformed JSON, missing files, invalid paths, unsupported checks, timeouts, and nonzero check exits become structured observations rather than server crashes.

`run_checks` is intended only for trusted uploaded code. The UI and README state that tests can execute project code. No command string is passed to a shell.

## Agent Loop

The system prompt instructs Hy3 to establish a short plan, gather evidence before conclusions, cite filenames and line numbers, and use only provided tools. The initial user message contains the incident description and file manifest, not the full contents of every file.

For each round, the server calls Hy3 with tool definitions. If Hy3 returns tool calls, the server emits a `tool_call` event, executes each valid call, emits a bounded `tool_result` event, and appends the observation to the conversation. If Hy3 returns content without tool calls, the server emits it as the final `report` event and ends.

After eight rounds, the server makes one final no-tools request asking Hy3 to synthesize the available evidence. The complete stream uses newline-delimited JSON with these event types: `started`, `plan`, `tool_call`, `tool_result`, `report`, `error`, and `done`.

## Upload And Workspace Lifecycle

Each request accepts a required incident description, an optional `demo_id`, and up to eight files. Supported extensions are `.py`, `.txt`, `.log`, `.json`, `.yaml`, `.yml`, `.toml`, and `.md`. A file is limited to 512 KiB and total input to 2 MiB.

Filenames are reduced to safe relative basenames and must remain unique. NUL bytes and invalid UTF-8 are rejected. User uploads cannot contain directories or archive files.

The server creates one temporary workspace per request. A streaming generator owns that workspace and removes it in a `finally` block after success, failure, timeout, cancellation, or client disconnect.

## User Experience

The first screen is the functional Agent workspace. The left pane contains the incident prompt, demo selector, file picker, file list, and primary run/cancel action. The right pane contains a stable investigation timeline and final report.

Each tool card shows the tool name, concise arguments, execution status, and collapsible observation. The final report is visually distinct and includes root cause, evidence, remediation, and verification sections. Desktop uses a two-column layout; mobile stacks the input above the trace without horizontal overflow.

The browser reads the response stream incrementally, preserving all completed events when a later error occurs. Model output is escaped before limited Markdown formatting. API keys and local absolute paths never enter browser-visible payloads.

## Built-In Demos

### Demo 1: Retry Regression

A small Python client and pytest file reproduce a retry-count regression. Hy3 is expected to inspect the tests and implementation, run pytest, identify the off-by-one attempt behavior, and recommend a targeted fix and regression coverage.

### Demo 2: Worker Startup Failure

A startup log, Python configuration loader, `.env.example`-style text file, and deployment snippet contain inconsistent environment variable names. Hy3 is expected to search for both names, compare the evidence, and identify the deployment/configuration mismatch without executing arbitrary commands.

## Error Handling

Upload validation failures return normal JSON `4xx` responses before streaming begins. Once streaming starts, Agent, Hy3, and tool failures use sanitized `error` events followed by `done`; earlier trace events remain visible.

Hy3 timeout, connection, and status errors do not include credentials or raw provider responses. Tool output never exceeds configured limits. Server logs do not include API keys, complete uploaded files, or the full conversation.

## Testing

Backend tests use fake Hy3 responses to cover a complete multi-round tool loop, final synthesis at the round limit, malformed tool calls, and sanitized upstream errors. Workspace tests cover extension, count, size, encoding, duplicate filename, and cleanup behavior. Tool tests cover valid reads/searches, path traversal, output truncation, both allowlisted checks, unsupported commands, nonzero exits, and timeout handling.

Streaming API tests verify event order, both built-in demos, upload validation before streaming, and cleanup after success and failure. Static tests verify the page and local assets. Existing Review Workbench and MCP test suites continue to run.

## Documentation

`apps/incident_agent/README.md` is written in English and documents setup, Hy3's role, architecture, all four tools, the trusted-code warning, both demo flows, and CodeBuddy collaboration. Root English and Chinese READMEs link to the Agent. A recording checklist keeps the two flows under two minutes.

## Acceptance Criteria

- All work remains on `feat/hy3-review-workbench` unless the user explicitly chooses integration later.
- A user can launch the Incident Agent with one documented command and use its Web UI.
- Hy3 performs planning and tool selection through the configured API.
- The browser displays streamed tool calls, observations, errors, and the final report.
- Only the four documented tools can execute, with path, time, and output limits enforced.
- Two built-in incidents run without manual file preparation.
- Temporary files are cleaned after every terminal path.
- Incident Agent, Review Workbench, and MCP automated tests pass.
- Documentation explains Hy3's role, tool safety, both demos, and CodeBuddy collaboration.
