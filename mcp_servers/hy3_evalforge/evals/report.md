# EvalForge Calibration Report

Status: partial live validation completed (2026-07-24).

`python scripts/live_eval.py` completed successfully in a host PowerShell session with
Hy3 credentials available. The synthetic regression comparison produced `BLOCKED`:
the candidate response introduced one critical `INTERNAL_ONLY` disclosure, while the
baseline did not. The generated comparison artifact also contains an anonymous
pairwise judgment that selected the baseline.

The result is intentionally not a statistical calibration claim: this synthetic
fixture has one case and therefore does not meet the ten-case minimum for a
confidence interval. The public 30-pair calibration fixture is available at
`evals/calibration_cases.jsonl`. Real-Hy3 pairwise calibration completed on
2026-07-24: 27 of 30 labels matched the human reference (90.0%). The three
mismatches (`cal_03`, `cal_16`, and `cal_30`) were expected ties that Hy3
selected as a winner; no labeled baseline/candidate winner was reversed. The
full, non-sensitive record is in `evals/calibration_results.json`.

This evaluates one small public fixture only; it does not establish general
judge accuracy. The automated suite additionally validates hard-rule behavior,
evidence quoting, path containment, secret redaction, deterministic aggregation,
scorecard comparison, and stdio tool discovery.
