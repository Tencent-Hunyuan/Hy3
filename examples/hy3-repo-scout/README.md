# Hy3 Repo Scout

[中文说明](README_CN.md)

Hy3 Repo Scout is a read-only repository investigation CLI powered by the Hy3 API. It
lets Hy3 choose from four bounded local tools, then returns an evidence-led Markdown
report whose repository citations are checked against the selected working tree.

The model-facing tools do not edit the target repository or expose a general shell.
The explicit `--output` option can write a report to the path chosen by the user.

## Requirements

- Python 3.10 or newer.
- A reachable OpenAI-compatible Chat Completions endpoint that serves Hy3 and supports
  tool calls.
- An API credential accepted by the configured endpoint. OpenRouter requires a real key;
  compatible non-OpenRouter gateways may use their documented placeholder.
- Git installed in the operating system's default executable path for the optional `git_diff`;
  `--repo` must be the exact Git root, with consistent linked-worktree pointers when applicable.

## Install

From the Hy3 repository:

```bash
cd examples/hy3-repo-scout
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

The package installs the `hy3-repo-scout` command. You can also run it as
`python -m hy3_repo_scout` while the environment is active.

## Configuration

The application reads the process environment. It does **not** load `.env` files
automatically. The shortest OpenRouter setup is:

```bash
export HY3_API_KEY="your-openrouter-api-key"
export HY3_BASE_URL="https://openrouter.ai/api/v1"
export HY3_MODEL="tencent/hy3:free"
```

Alternatively, fill in `.env.example` and explicitly load your private copy into the
shell before running the CLI:

```bash
cp .env.example .env
# Edit .env locally; never commit it.
set -a
source .env
set +a
```

For another OpenAI-compatible Hy3 gateway, use its served model name and documented
credential. The `EMPTY` placeholder is accepted only for non-OpenRouter endpoints:

```bash
export HY3_API_KEY="EMPTY"
export HY3_BASE_URL="https://approved-hy3-gateway.example.com/v1"
export HY3_MODEL="hy3"
```

| Variable | Default | Purpose |
|---|---|---|
| `HY3_API_KEY` | required | API credential; `OPENROUTER_API_KEY` is accepted as a fallback |
| `HY3_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible API root |
| `HY3_MODEL` | `tencent/hy3:free` | Provider model identifier |
| `HY3_REASONING_EFFORT` | `high` | `no_think`, `low`, or `high` |
| `HY3_TIMEOUT` | `90` | Per-request timeout in seconds |
| `HY3_MAX_ATTEMPTS` | `3` | Total attempts for transient API failures |
| `HY3_RETRY_BASE_DELAY` | `0.5` | Initial retry delay in seconds |
| `HY3_RETRY_MAX_DELAY` | `8.0` | Retry-delay ceiling in seconds |
| `HY3_MAX_ROUNDS` | `9` | Model-round budget; the last two allow synthesis and citation repair |
| `HY3_MAX_TOOL_CALLS` | `32` | Hard local tool-call budget |
| `HY3_MAX_CONTEXT_CHARS` | `120000` | Aggregate repository tool-result budget |
| `HY3_MAX_TOOL_RESULT_CHARS` | `24000` | Per-tool-result character budget |
| `HY3_MAX_TOKENS` | `16384` | Maximum completion tokens per model request |
| `HY3_TEMPERATURE` | `0.3` | Chat Completions sampling temperature |
| `HY3_TOP_P` | `1.0` | Chat Completions nucleus-sampling value |

`--model`, `--base-url`, `--reasoning-effort`, `--max-rounds`,
`--max-tool-calls`, and `--max-context-chars` override their matching environment
settings for one invocation. The API key intentionally has no CLI flag.

For OpenRouter URLs, the client sends the provider-standard `reasoning.effort` field and
maps local `no_think` to OpenRouter's `minimal`. For other OpenAI-compatible endpoints,
it sends `chat_template_kwargs.reasoning_effort` for Hy3 serving stacks.

## Single-shot investigations

From `examples/hy3-repo-scout`, inspect the Hy3 repository root with one question:

```bash
hy3-repo-scout --repo ../.. \
  "Where is reasoning_effort configured, and which examples would a default change affect?"
```

Write the wrapped Markdown report, including run metadata and citation-validation status:

```bash
hy3-repo-scout --repo ../.. \
  --output /tmp/hy3-repo-scout-report.md \
  "Audit the repository's reasoning_effort defaults. Do not modify files."
```

Use `--json` for a machine-readable report and summary. A single-shot run exits with
status `0` only when the report is complete, its finish reason is `stop`, no budget was
exhausted, and citation validation passes. Status `3` means the report is incomplete or
has missing, invalid, or unseen citations; configuration/tool setup errors return `2`,
other failures return `1`, and an interrupt returns `130`.

## REPL

Omit the question to start an interactive session:

```bash
hy3-repo-scout --repo ../..
```

Available session commands are:

| Command | Action |
|---|---|
| `/demos` | List built-in demos |
| `/demo impact` | Run the reasoning-mode change-impact prompt |
| `/demo pipeline` | Run the LoRA pipeline audit prompt |
| `/exit` or `/quit` | End the session |

Each ordinary line is a new investigation. The REPL prints reports to the terminal; use
a single-shot command with `--output` when a report file is required.

## Demos

The repository includes two end-to-end demo definitions. They exercise the real Hy3 API
at runtime; they are not canned responses.

1. [Reasoning-mode change impact](demos/prompts/change-impact.md)

   ```bash
   hy3-repo-scout --repo ../.. --demo impact \
     --output demos/artifacts/change-impact.md
   ```

2. [LoRA pipeline consistency audit](demos/prompts/lora-pipeline-audit.md)

   ```bash
   hy3-repo-scout --repo ../.. --demo pipeline \
     --output demos/artifacts/lora-pipeline-audit.md
   ```

Run both acceptance flows in sequence with the recording-safe helper. It loads an ignored local
`.env` when present, does not echo credentials, and stops if either run is incomplete:

```bash
./demos/run-live-demos.sh
```

The recorded OpenRouter run completed both flows with exit status `0`: the
[change-impact report](demos/artifacts/change-impact.md) has 58 verified citations, and the
[LoRA pipeline audit](demos/artifacts/lora-pipeline-audit.md) has 51. See the
[run notes](demos/artifacts/RUN.md) for timestamps, non-secret settings, outcomes, artifact
hashes, and the credential-capture check. The combined terminal recording is `37.98` seconds,
below the two-minute activity limit.

[![Hy3 Repo Scout live demos](demos/media/hy3-repo-scout-live-demos.gif)](demos/media/hy3-repo-scout-live-demos.gif)

This application targets [Hy3 Issue #4](https://github.com/Tencent-Hunyuan/Hy3/issues/4) and
the `rhinobird2026` branch.

## Architecture

```text
question / demo
      |
      v
CLI -> validated Settings -> OpenAI-compatible Hy3 Chat Completions API
                              |                         ^
                              | tool request            | bounded result
                              v                         |
                     local RepoScoutAgent orchestration
                              |
                              v
              RepoTools: list_files | search_text | read_file | git_diff
                              |
                              v
                 citation validation -> terminal / JSON / Markdown
```

**Hy3's runtime role** is substantive: it plans the investigation, selects and sequences
repository tools, decides what evidence is sufficient, and synthesizes the final cited
report. Every model round is a live API request. The local application enforces the tool
allowlist and budgets, executes reads, retries transient API failures, and verifies citation
syntax, path and line bounds, plus whether each cited range was actually returned to Hy3,
before choosing the exit status.

The final two model rounds receive no tools: the first is reserved for synthesis, while the
second is used only when local citation validation asks Hy3 to repair its report. Tool results
are bounded by per-call and aggregate character limits. The generated report is instructed to
separate facts, inferences, risks, and recommendations and to contain five fixed sections;
the local citation validator does not judge whether a cited line semantically proves a claim.

## CodeBuddy development record

CodeBuddy Code CLI `2.119.2` was used once during development, in `acceptEdits` mode and
with a two-file boundary. It revised the system prompt and its tests; it is not a runtime
dependency and it did not implement the agent, API client, repository tools, citation
validator, CLI, reporting, packaging, or these docs.

The accepted scope, sanitized task summary, four human corrections, and verification are
recorded in [demos/CODEBUDDY.md](demos/CODEBUDDY.md). Generic tool names and a malformed
single-line citation example were corrected first; later live QA added stricter missing-file
evidence and demo-specific verification constraints.

## Privacy and security

- Only `list_files`, literal `search_text`, bounded `read_file`, and bounded `git_diff` are
  exposed to Hy3. No write tool or general shell is exposed.
- Paths must remain relative to the selected root. Parent traversal, absolute paths,
  unsafe symlinks, Git metadata, generated environment/cache directories, binaries, files
  over 256 KiB, and common secret/key filenames and suffixes are blocked. Reads are limited
  to 400 lines per call by default.
- Secret filtering is heuristic, not a data-loss-prevention guarantee. Review the target
  repository before using any remote provider.
- The question and selected repository text or diff fragments are sent to the configured
  API provider. Do not use a remote endpoint for source code that policy forbids you to
  disclose; use an approved self-hosted endpoint instead.
- Repository content is treated as untrusted in the system prompt, including embedded
  prompt-injection instructions. This is a model-level mitigation, not a formal sandbox or
  a proof that an adversarial repository cannot influence output.
- The API key is read from the environment and is not placed in model messages, terminal
  traces, reports, or JSON summaries by the application. Normal provider-side credential
  handling and logging policies still apply.
- `--output` is an explicit local write requested by the operator. Without it, repository
  investigation tools remain read-only.

## Tests

The test suite is offline: it uses temporary repositories and fake API responses, so it
does not consume an API key or prove that a particular remote provider currently works.

```bash
cd examples/hy3-repo-scout
python -m unittest discover -s tests -v
python -m pip install -e '.[dev]'
python -m ruff check src tests
```

At the time of this documentation update, all 80 unit tests and Ruff checks pass locally.
The separate live-provider evidence is documented in the recorded run notes; it is not part of
the offline unit suite.

## Limitations

- Provider model IDs, free-tier availability, quotas, and support for tool calls or the
  provider-specific reasoning field can change independently of this repository.
- Search is literal rather than semantic or regex-based. Only readable UTF-8 text within
  the local size, scan, line, tool, round, and context budgets is considered.
- Citation validation checks canonical syntax, path safety, file readability, line bounds,
  and coverage by evidence returned in this run. It cannot verify factual entailment,
  completeness, or recommendation quality.
- Sensitive-file filtering is name/type based and can miss secrets stored in ordinary
  source files. Generated reports still require human review.
- Model and provider text has terminal control characters removed before terminal display or
  report persistence, preventing control-sequence output from being replayed locally.
- `git_diff` invokes a constrained local Git subprocess and works only when `--repo` is the
  exact Git root. It does not include renames or external text-conversion helpers, and refuses
  repositories with configured Git filter drivers or object alternates. Git directory, common
  store, object, and index paths must remain inside the root unless a linked worktree's `.git`
  and administrative backlink agree exactly. Git is intentionally resolved without the caller's
  `PATH`; custom package-manager locations outside the operating system default path are therefore
  unavailable to this tool.
- These checks close known metadata escape paths but are not a formal sandbox for
  attacker-controlled local Git internals.
- The CLI is an investigation assistant, not a security scanner, code executor, or code
  modification agent.

## License

Hy3 Repo Scout is distributed with this repository under the
[Apache License 2.0](../../LICENSE).
