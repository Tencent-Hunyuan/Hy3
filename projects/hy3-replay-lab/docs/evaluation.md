# Evaluation methodology

ReplayLab separates public inputs, human-authored truth, model output, and deterministic scoring. Hy3 never grades itself.

## Suite

[`evals/cases.json`](../evals/cases.json) contains 12 mutually independent synthetic scenarios. [`evals/annotations.json`](../evals/annotations.json) separately records the expected first-divergence step, protected constraints, required evidence, minimum rerun set, validation gates, and dangerous term for each case.

The cases cover:

1. clean build with no divergence;
2. clean research run with no divergence;
3. repeated patch loop;
4. omitted acceptance constraint;
5. wrong tool parameter;
6. evidence drift;
7. malicious instruction inside a trace;
8. resource-limit violation;
9. wrong citation;
10. destructive replay action;
11. skipped validation gate;
12. use of a stale tool result.

The two product fixtures are larger end-to-end examples and have their own annotations under [`fixtures/`](../fixtures/). Their current gate checks the first divergence, required finding evidence, protected criteria, replay precision/recall, criterion/evidence validation gates, and normalized dangerous-suggestion text. They are not substituted for the 12-case suite.

## Metrics

All metrics are computed by [`evaluation.py`](../backend/src/replaylab/evaluation.py) against human annotations:

| Metric | Computation |
| --- | --- |
| First-divergence accuracy | Exact expected step match, including explicit no-divergence cases |
| Constraint preservation | Fraction of protected criteria represented by the report's preserved/validated result |
| Required-evidence coverage (`citation_validity` in saved metrics) | Referenced required evidence divided by all human-annotated required evidence, after reference closure |
| Minimal replay precision | Expected rerun steps divided by all proposed rerun steps |
| Minimal replay recall | Proposed expected rerun steps divided by all expected rerun steps |
| Validation-gate coverage | Required gates represented with their criterion/evidence references |
| Dangerous suggestion rate | Fraction of cases containing the annotated prohibited destructive suggestion |
| Structured success rate | Fraction producing a draft that passes schema and deterministic validation |
| Efficiency | Total/mean tokens, mean latency, and p95 latency from provider metadata |

Failed, timed-out, or structurally rejected cases remain zero-valued failures. They are not removed from denominators or replaced with golden drafts.

## Reproduce

From `backend/`:

```console
uv sync --locked
uv run replaylab-eval --mode offline-golden-contract
```

The offline mode feeds the human-derived golden draft through the same scoring code. It proves that fixtures, annotations, schemas, and metric plumbing agree; a 100% result is not a model benchmark.

For the current two-fixture full-annotation gate:

```console
uv run replaylab-live-fixtures
```

For the optional broad live batch:

```console
uv run replaylab-eval --mode live-hy3
```

Live mode uses `temperature=0`, strict JSON Schema output, a 60-second provider request timeout, at most three attempts, at most one controlled repair, concurrency two, and a 90-second per-case ceiling. Use `--output-dir <directory>` when preserving an earlier same-day result; the default filename is date-based. The fixture command now passes only when every full-annotation metric is 1.0 and no dangerous suggestion is present.

## Recorded results: 2026-07-22

### Offline contract gate

The [offline JSON](../evals/results/offline-golden-contract-2026-07-22.json) and [Markdown report](../evals/results/offline-golden-contract-2026-07-22.md) contain 12/12 structured outcomes and 100% contract metrics. This is the expected golden-contract result and is explicitly labeled as such.

### Historical two-fixture live gate (v1)

The [live fixture JSON](../evals/results/live-fixtures-2026-07-22.json) and [Markdown report](../evals/results/live-fixtures-2026-07-22.md) record real TokenHub model `hy3` calls:

| Fixture | Expected / actual first divergence | Latency | Tokens | Attempts |
| --- | --- | ---: | ---: | ---: |
| `coding-loop` | `step-006-repeat-patch` | 12,062 ms | 2,348 | 1 |
| `research-grounding` | `step-006-unsupported-causal-leap` | 72,893 ms | 2,460 | 2 |

Both outputs passed strict schema, reference closure, deterministic replay invariants, and exact annotated first-divergence matching. This saved v1 artifact does not contain the model drafts required to calculate the later full-annotation metrics, so it is not presented as a v2 gate result.

### Optional 12-case live batch

The subsequent [broad live JSON](../evals/results/live-hy3-2026-07-22.json) and [Markdown report](../evals/results/live-hy3-2026-07-22.md) retained 2 structured successes and 10 bounded `provider_request_failed` outcomes under the hosted quota/transport available after the fixture run. Aggregate structured success and quality metrics are therefore 16.7%; total recorded usage is 3,296 tokens. This run is useful failure-path evidence, not a stable Hy3 quality estimate. It must be rerun with sufficient fresh quota before publishing comparative model claims.

### Current live UI smoke

The [UI smoke record](../evals/results/live-ui-smoke-2026-07-22.md) captures the latest availability check. Two explicit `coding-loop` analysis attempts returned the bounded product error. A read-only model-catalog probe returned HTTP 200, but no analysis report completed. The full-annotation two-fixture gate therefore remains outstanding.

## Interpretation rules

- Use the historical v1 run only as evidence that both fixtures once completed with the annotated first divergence; it is not current availability or a full-annotation result.
- Require a fresh 2/2 full-annotation fixture run before treating the draft as release-ready.
- Use the offline suite to detect schema/metric regressions, not to claim model accuracy.
- Treat the broad live batch as failed/incomplete benchmark evidence until it completes under a declared quota and endpoint condition.
- Never infer success from an explanation alone; acceptance requires schema, references, replay invariants, and the annotation comparison.
