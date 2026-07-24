# Evaluation Method

## 1. Purpose

The Stage 7 evaluation suite measures whether the quality gate classifies known
MCP contract and lifecycle defects without regressing the conforming control
fixture. It is a deterministic regression benchmark, not a claim that the system
detects every possible MCP defect or that generated semantic judgments are always
correct.

The suite requires no live Hy3 credential. Deterministic inspection, audit, and
comparison cases run against local fixture servers. Probe validation uses one
committed synthetic model response through the same strict local generator path
used in production.

## 2. Reproduce the baseline

From `mcp_servers/mcp_quality_gate`:

```bash
npm ci
npm run evaluate
```

The command:

1. builds the TypeScript package;
2. validates `evaluation/manifest.json`;
3. loads only targets from `evaluation/targets.json`;
4. runs every case through production inspection, audit, comparison, or probe
   code;
5. calculates metrics from actual and expected rule sets;
6. enforces the committed minimums;
7. compares the complete report with `evaluation/baseline.json`.

It exits nonzero if a threshold fails, the report changes, a fixture cannot run,
or any evaluation artifact violates its strict schema.

## 3. Cases

The committed manifest contains ten cases:

| Area | Cases | What they prove |
| --- | ---: | --- |
| Inspection | 5 | Clean control, stdout pollution, malformed JSON-RPC, output limit, and early exit classification. |
| Audit | 2 | Exact schema/documentation/safety rule set and contract-size limit behavior. |
| Comparison | 2 | Compatible additions versus known breaking changes across `COMPAT-001` through `COMPAT-007`. |
| Probe policy | 1 | One safe candidate is retained while unsafe path, schema-invalid, and invalid-evidence candidates are rejected. |

Fixture text and recorded responses use synthetic values only. The report stores
stable target IDs and rule IDs, not timestamps, process IDs, durations, absolute
paths, environment values, provider responses, or credentials.

## 4. Metrics

Rule labels are namespaced by case before aggregation, so the same rule in two
cases counts as two independently expected classifications.

| Metric | Definition |
| --- | --- |
| `status_accuracy` | Fraction of cases whose final status exactly matches the manifest. |
| `exact_rule_set_accuracy` | Fraction of cases whose unique rule-ID set has no missing or extra item. |
| `rule_precision` | True-positive rule labels divided by all emitted rule labels. |
| `rule_recall` | True-positive rule labels divided by all expected rule labels. |
| `rule_f1` | Harmonic mean of rule precision and recall. |
| `probe_policy_accuracy` | Fraction of recorded probe cases whose status and accepted/rejected counts match exactly. |

The baseline currently contains 24 true-positive rule labels, zero false-positive
labels, and zero false-negative labels. All six normalized metrics are `1`.

This perfect score applies only to the committed synthetic regression set. New
fixtures should be added when a real defect escapes detection; the metric should
not be generalized to arbitrary third-party MCP servers.

## 5. Changing the baseline

A baseline change should be reviewed like a public contract change:

1. add or modify a synthetic fixture;
2. declare the intended status and exact rule set in the manifest;
3. run `npm run evaluate -- --no-baseline` to inspect the candidate report;
4. verify every difference has an intentional rule or policy explanation;
5. update `baseline.json`;
6. run `npm run evaluate` and the full test suite.

Do not lower a minimum or delete an expected rule merely to make the command pass.
If a rule is intentionally replaced, document the catalogue and compatibility
impact in the same change.
