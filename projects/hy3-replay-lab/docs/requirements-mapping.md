# Requirements mapping

This table maps the Issue #4 and task-prompt requirements to reviewable implementation and evidence.

| Requirement | Implementation | Verification evidence | Status |
| --- | --- | --- | --- |
| Interactive application powered by Hy3 | [`App.tsx`](../frontend/src/App.tsx), [`main.py`](../backend/src/replaylab/main.py), [`hy3.py`](../backend/src/replaylab/hy3.py) | [current 2/2 live report](../evals/results/live-fixtures-hy3-preview-2026-07-22.md), [live browser record](../evals/results/live-ui-demo-2026-07-22.md) | pass |
| Hy3/deterministic responsibility boundary | strict structured provider plus local schemas, redaction, reference/ordering validation | [architecture](architecture.md), backend tests | pass |
| Stable timeline and acceptance coverage | [`schemas.py`](../backend/src/replaylab/schemas.py), [`Timeline.tsx`](../frontend/src/components/Timeline.tsx), [`CoverageMatrix.tsx`](../frontend/src/components/CoverageMatrix.tsx) | normalization and component tests | pass |
| Evidence-grounded first divergence | [`validation.py`](../backend/src/replaylab/validation.py), [`EvidenceDrawer.tsx`](../frontend/src/components/EvidenceDrawer.tsx) | historical live exact-step matches; reference-closure and evidence-timing tests | pass |
| Minimal verifiable replay plan | [`ReplayPlanPanel.tsx`](../frontend/src/components/ReplayPlanPanel.tsx), deterministic prefix/order/gate rules | provider-contract tests and both browser workflows | pass |
| Complete JSON and Markdown export | [`export.py`](../backend/src/replaylab/export.py), UI download actions | export tests and Playwright download assertions | pass |
| Two public synthetic fixtures with independent annotations | [`fixtures/coding-loop`](../fixtures/coding-loop), [`fixtures/research-grounding`](../fixtures/research-grounding) | offline browser E2E and real Hy3 fixture gate | pass |
| At least 12 independent evaluation cases | [`cases.json`](../evals/cases.json), [`annotations.json`](../evals/annotations.json) | [evaluation report](../evals/results/offline-golden-contract-2026-07-22.md) | pass |
| Required metric set and human truth | [`evaluation.py`](../backend/src/replaylab/evaluation.py), full-annotation fixture gate | metric-recall regression tests, [evaluation methodology](evaluation.md), offline/live reports | pass |
| Safe JSON/Markdown/TXT import | [`imports.py`](../backend/src/replaylab/imports.py), custom-import UI | import/API/frontend regression tests | pass |
| Key remains server-side | environment-only `Hy3Settings`; health returns boolean | no-key/health tests and [security model](security.md) | pass |
| Prompt injection, references, secrets, limits | provider instruction, redaction, strict models, deterministic closure | security/provider/import regression tests | pass |
| Bounded timeout/retry/repair and provider cancellation | HTTPX timeout, three attempts, `Retry-After`, one repair; cancelled provider tasks are not retried | provider tests and 429 UI test | pass |
| Loading/stop-wait/retry/rate-limit/mobile UI | React state machine and responsive CSS; stop-wait is explicitly browser-side | component tests; 390×844 Playwright test | pass |
| Simplified-Chinese product and polished visual system | Chinese UI/API/export copy, localized fixtures, graphite/ivory three-column dashboard | [ChatGPT Web reference](design/README.md), regenerated actual-UI frames, frontend/backend/E2E tests | pass |
| Two auditable CodeBuddy collaborations | one scoped accessibility edit and one read-only mobile/error audit | [collaboration record](codebuddy-collaboration.md) | pass |
| Real Hy3 E2E for both fixtures | `replaylab-live-fixtures` | current full-annotation `hy3-preview` [2/2 result](../evals/results/live-fixtures-hy3-preview-2026-07-22.md) | pass |
| Actual UI demo under two minutes | opt-in live Playwright capture and GIF builder; two live analyses in 64,719 ms and a 12-second recording | [demo provenance](demo/README.md), [browser record](../evals/results/live-ui-demo-2026-07-22.md) | pass |
| README English/Chinese, architecture, security, evaluation, verification | project documentation set | 108 local Markdown targets checked | pass |
| Build/test/clean-install/browser gates | locked Python/npm dependencies and reproducible commands | [verification ledger](verification.md) | pass; npm vulnerability endpoint separately noted as unavailable |
| Open source | repository Apache-2.0 license | [LICENSE](../../../LICENSE) | pass |

## Differentiation audit

ReplayLab does not reuse TaskRelay branding, fixtures, tools, or code and does not depend on PR #105. It does not implement general code review or incident RCA like neighboring submissions, project planning/self-review, repository investigation, or cross-session handoff/memory. The distinguishing contract is: **find the earliest evidence-backed divergence in an imported Agent decision trace, then produce the smallest evidence-gated ordered replay**.

The upstream Issue/PR collision search and branch baseline were rechecked on 2026-07-22 before and after implementation. The final GitHub comparison reported local base `8a12d9af87c6de173b7476daf3a53b92c683e9ec` identical to `rhinobird2026`, and the direct collision queries returned no matches. Recheck again immediately before any future commit/PR because the competition branch is active.
