# Verification ledger

This ledger records the commands and observed results for the 2026-07-22 working tree. It distinguishes deterministic checks, real Hy3 calls, and the offline UI recording.

## Automated gates

| Area | Command | Observed result |
| --- | --- | --- |
| Backend/script lint | `uv run ruff check . ../scripts` | pass |
| Backend tests | `uv run pytest -q` | 52 passed |
| Python artifacts | `uv build` | sdist and wheel built |
| Clean install | install the wheel into a new Python 3.13 virtual environment; list packaged fixtures, analyze `coding-loop` through `TestClient`, and run the installed offline evaluation CLI | pass; fixtures/evaluations are present and both entry paths run |
| Frontend lint | `npm run lint` | pass, zero warnings |
| TypeScript | `npm run typecheck` | pass |
| Component tests | `npm test -- --run` | 3 files, 7 tests passed |
| Production bundle | `npm run build` | pass; JS 209.89 kB raw / 65.82 kB gzip |
| Browser E2E | `npm run e2e -- --project=chromium` | 3 passed; optional capture spec skipped |
| Dependency integrity | `uv lock --check`, `uv tree --locked`, `npm ci`, `npm ls --omit=dev --all` | pass; locks resolve and production tree is valid |
| Markdown targets | `python scripts/check_markdown_links.py` | 108 local targets across 15 Markdown files; pass |
| Repository hygiene | `git diff --check` plus all-deliverable whitespace and secret/personal-path/request-value scans | 83 text files, zero whitespace or sensitive-value hits; pass |

The three functional browser tests cover the `coding-loop` report and JSON export, the `research-grounding` report and Markdown export, and the research evidence workflow at 390×844 with no horizontal overflow. The demo capture spec is opt-in and skipped during the ordinary suite so tests do not rewrite review artifacts.

The configured npm mirror does not implement the audit endpoint, and two attempts against the official npm audit endpoint ended in connection resets. Therefore this ledger does **not** claim a zero-vulnerability audit. The production tree contains only `react`, `react-dom`, and `scheduler` at their locked versions; rerun `npm audit --omit=dev` on a network where the official endpoint is reachable before release.

## TDD evidence

The implementation was grown through explicit red-to-green contracts for the first vertical slice, stable IDs, aggregate limits, provider repair, input/output redaction, export, API success/error paths, React workflow, Hy3 response/retry behavior, epistemic timing, rate-limit metadata, import safety, live-provider selection, custom imports, evidence-dialog focus/Escape behavior, evaluation report labeling, and the Simplified-Chinese product surface and export headings. Regression suites now exercise the combined behavior rather than relying on those historical failures.

Backend coverage includes invalid JSON, unknown references, bad ordering, controlled-repair success/failure, timeout/transport/retry/permanent errors, provider-coroutine cancellation, prompt injection, credential redaction, over-limit input/output, malicious filenames, wrong MIME, missing key, health state, 429 forwarding, and custom-import rules. Frontend coverage includes offline/live selection, no-key behavior, bad import, loading, browser-side stop-wait, explicit retry, 429, export, evidence accessibility, and coverage semantics.

## Real Hy3 evidence

The historical v1 two-fixture run used TokenHub provider `tencent-tokenhub`, model `hy3`, `temperature=0`, strict JSON Schema, at most three attempts, and at most one controlled repair:

| Fixture | Gate | First divergence | Latency | Tokens | Attempts |
| --- | --- | --- | ---: | ---: | ---: |
| `coding-loop` | pass | `step-006-repeat-patch` | 12,062 ms | 2,348 | 1 |
| `research-grounding` | pass | `step-006-unsupported-causal-leap` | 72,893 ms | 2,460 | 2 |

Evidence: [historical live fixture report](../evals/results/live-fixtures-2026-07-22.md). Its saved rows prove structural acceptance and exact annotated first-divergence matches. They predate the current full-annotation gate and do not include model drafts that could be rescored after the fact.

The optional 12-case live batch later returned 2 valid reports and 10 bounded provider failures. Those failures remain in the 16.7% aggregate and are not hidden. Evidence: [broad live report](../evals/results/live-hy3-2026-07-22.md). The evaluation interpretation is in [evaluation.md](evaluation.md).

In the latest running-UI check, two explicit `coding-loop` attempts ended with the bounded `Hy3 分析请求失败` message. A read-only model-catalog request returned HTTP 200 between attempts, but no analysis report completed. Evidence: [current UI smoke record](../evals/results/live-ui-smoke-2026-07-22.md). The full-annotation 2/2 command remains a draft-release gate.

## UI demo gate

[`replaylab-offline-demo.gif`](demo/replaylab-offline-demo.gif) is 628,448 bytes and 12 seconds. Its five source frames were captured from the running Simplified-Chinese Web UI through Playwright, not drawn as static mockups. The UI labels the analysis `离线演示`; the recording contains no desktop, notification, credential, account, personal path, request identifier, or private data. The preceding visual direction was generated through the logged-in ChatGPT Web image experience and is preserved as a [design reference](design/README.md); it is not used as a runtime screen.

The recording is not a live Hy3 demo. A current live analysis did not complete, so relabeling an offline response would be misleading. A successful full-annotation 2/2 run and a live UI capture remain outstanding. See [demo/README.md](demo/README.md).

## Reproduction sequence

```console
cd backend
uv sync --locked
uv run ruff check .
uv run pytest -q
uv build

cd ../frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
npm run e2e -- --project=chromium

cd ..
python scripts/check_markdown_links.py
```

Live commands require the server-side variables described in the [README](../README.md). They consume Hosted quota and are intentionally excluded from ordinary local test commands.
