# ScenarioForge verification ledger

Date: 2026-07-23 (Asia/Shanghai)

## Automated checks

| Check | Result |
|---|---|
| `python3 -m unittest discover -s tests -v` | 20/20 passed |
| `python3 -m compileall -q scenarioforge tests` | passed |
| `node --check scenarioforge/static/app.js` | passed |
| `ruff check .` | passed |
| `python3 -m build` | wheel and sdist built successfully |

The test suite covers environment parsing, secret-safe provider failures, OpenAI-compatible request
shape, fenced JSON parsing, input limits, output schemas, two-stage orchestration, CSP headers,
fixture integrity, edited-fixture rejection, and both complete HTTP flows.

## Browser run

Browser: Chromium controlled through Playwright CLI, viewport 1440 × 1000.

| Flow | API result | UI result |
|---|---|---|
| Rainy campus charity night market | `POST /api/rehearse` → 200 | conditional-go report rendered |
| Enterprise billing engine release | `POST /api/rehearse` → 200 | no-go report rendered |

Browser console after both runs: **0 errors, 0 warnings**.

Artifacts:

- `docs/demo/scenarioforge-demo.gif` — 54.67 seconds, 960 × 720, both flows.
- `docs/demo/scenarioforge-home.png` — input workspace.
- `docs/demo/scenarioforge-report.png` — rendered billing report.

## Live Hy3 status

The machine did not expose `HY3_API_KEY` and did not have a reachable self-hosted Hy3 endpoint.
Therefore, the two recorded browser flows used the explicitly labelled offline fixtures. The live
request path is covered by a protocol-level fake transport, but that is not equivalent to a real
Hy3 inference. No README text, UI metadata, or PR claim should describe the fixture output as live.

To produce live evidence, configure credentials and rerun both examples without
`SCENARIOFORGE_DEMO_MODE`; a valid result reports `mode: live`, `provider.name: Hy3`, `calls: 2`,
real model metadata, request IDs, and token usage when provided by the endpoint.
