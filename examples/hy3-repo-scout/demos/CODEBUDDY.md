# CodeBuddy CLI development record

[Back to Hy3 Repo Scout](../README.md) | [中文说明](../README_CN.md)

This document records the limited, development-time use of CodeBuddy for Hy3 Repo Scout. It
separates accepted CodeBuddy work from subsequent human review and from Hy3's runtime role.

## Environment

- Product: CodeBuddy Code CLI, Chinese-site distribution.
- Installed version: `2.119.2`.
- Session state: installed and authenticated locally; `acceptEdits` mode.
- Task shape: one development task with an explicit two-file edit boundary.
- Runtime dependency: none. The shipped application calls Hy3 through the OpenAI-compatible
  API and does not invoke CodeBuddy.

Sanitized command summary:

```text
codebuddy --version
2.119.2

# An authenticated CLI session was started with acceptEdits enabled.
# The task was restricted to prompts.py and test_prompts.py.
```

Login URLs, login state values, session identifiers, tokens, and credentials are intentionally
not recorded. The comments above summarize the session; they are not presented as a verbatim
transcript.

## Task boundary

The task allowed CodeBuddy to edit only:

- `src/hy3_repo_scout/prompts.py`
- `tests/test_prompts.py`

The sanitized task was to harden the repository-investigation prompt and expand prompt-level
tests while preserving read-only behavior, evidence citations, bounded tool use, and a stable
report structure.

CodeBuddy was **not** asked to implement or rewrite `agent.py`, `client.py`, `config.py`,
`tools.py`, `citations.py`, `cli.py`, `report.py`, package metadata, demos, or documentation.
No broader implementation credit is claimed.

## Accepted CodeBuddy changes

Within the two-file boundary, CodeBuddy:

- rewrote `SYSTEM_PROMPT` to treat repository content as untrusted evidence and explicitly
  resist prompt injection embedded in files;
- required explicit `Fact`, `Inference`, `Risk`, and `Recommendation` statement types;
- added budget-awareness instructions and a fixed five-section final report order;
- expanded prompt-focused coverage from 2 tests to 12 tests; and
- reviewed both built-in demo prompts and `build_user_prompt`, which were retained at that
  checkpoint and later tightened during human live-run review as described below.

These accepted edits concern development-time prompt quality only. Hy3 remains the model that
plans investigations, calls tools, and writes reports when the application runs.

## Human corrections

The accepted output and subsequent live runs required four concrete human corrections before
final verification:

1. CodeBuddy referred to generalized `search`, `read`, `glob`, and `grep` capabilities. Those
   names did not match the application. The prompt was corrected to the exact runtime allowlist:
   `list_files`, `search_text`, `read_file`, and `git_diff`.
2. CodeBuddy used `[src/app.py:42-42]` as a single-line citation example. The parser requires
   both `L` markers, so the example was corrected to `[src/app.py:L42-L42]`.
3. Live report review showed that directory listings could be misread as proof of absence. The
   prompt was tightened to require an exact-path `read_file` attempt, treat failed lookups as
   uncitable, and keep unverified absence claims under `Unknown` rather than `Fact`.
4. Live output initially suggested an undeclared test runner and later misidentified an existing
   DeepSpeed config. Human review grounded verification commands in repository metadata and
   tightened both demo prompts to read the relevant test configuration and exact finetune paths.

The final prompt and tests were then reviewed against the implementation rather than accepted
solely because the assistant produced them.

## Verification

After the manual corrections, the full project verification was run:

```bash
cd examples/hy3-repo-scout
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python -m ruff check src tests
```

Result at the CodeBuddy/manual-review checkpoint: 43 unit tests passed, and Ruff reported no
errors. The suite later grew to 80 tests, which also pass at the time of this documentation
update. These are offline implementation checks with fake model responses; they are not
evidence of a completed live Hy3 demo. The separate [live run record](artifacts/RUN.md) contains
the two completed Hy3 reports and terminal GIF; it does not change the limited CodeBuddy scope
documented here.
