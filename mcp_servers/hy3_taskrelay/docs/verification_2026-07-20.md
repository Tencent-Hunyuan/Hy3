# Verification record (2026-07-20)

All package commands ran from `mcp_servers/hy3_taskrelay`. Default tests and evaluations were
offline. The live and client calls use separately recorded, sanitized evidence.

| Check | Result |
|---|---|
| `uv lock --offline --check` | Pass; 70 packages resolved from the lock |
| `ruff format --check .` | Pass; 25 Python files |
| `ruff check .` | Pass |
| `pytest -q` | Pass; 99 tests, including security, MCP protocol, artifact linkage, and demo bounds |
| `python evals/run.py` | Pass; 14/14 independent cases |
| `python -m build` | Pass; wheel and sdist created from the final source |
| `python -m twine check dist/*` | Pass; both artifacts |
| package license contents | Pass; wheel has `dist-info/licenses/LICENSE` and sdist has `LICENSE` |
| clean wheel install on Python 3.13.5 | Pass; 32 packages installed offline |
| clean sdist install on Python 3.13.5 | Pass; 32 packages installed offline |
| wheel and sdist `scripts/stdio_smoke.py` | Pass; protocol `2025-11-25`, exactly three tools, clean exit |
| wheel/source parity | Pass; `security.py`, `server.py`, and `schemas.py` match the final source |
| MCP Inspector CLI `tools/list` | Pass against the clean-wheel console entry point; see [record](inspector_2026-07-20.json) |
| real Hy3 three-operation smoke | Pass; see [sanitized record](live_smoke_2026-07-20.json) |
| CodeBuddy Code 2.124.0 real MCP call | Pass; created `cp_b3067b1cc7f4a430` |
| Codex CLI 0.144.6 real MCP calls | Pass; audit `clean`/0 findings; created `resume_bff690737dece30f` |
| cross-client demo | Pass; 1280×720, six frames, 13.2 seconds; see [demo](demo) |
| local Markdown links | Pass; seven repository/package Markdown files |
| config and sensitive-data scan | Pass; mirrored configs match; 67 text files contain neither the configured key nor a personal absolute path |
| `git diff --check` and staged diff check | Pass |

The committed client records retain only versions, exact tool names, stable IDs, statuses, counts,
and bounded security metadata. Schema-valid artifacts are stored in
[`client_artifacts`](client_artifacts). The Chinese actual-call panels, summary cards, and GIF are
deterministically rendered from these real records; raw provider events are not committed.
