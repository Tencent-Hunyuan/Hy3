# Hy3 EvalForge

Local stdio MCP server for evidence-backed AI-output evaluation with Hy3.

```bash
pip install .
hy3-evalforge
```

Configure environment variables from `.env.example`. For TokenHub, set
`HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1`. The server exposes four tools:
`evalforge_design_spec`, `evalforge_generate_cases`, `evalforge_score_run`, and
`evalforge_compare_runs`. All files stay below `EVALFORGE_ALLOWED_ROOT`; EvalForge never runs
the target agent, commands, or URLs. Critical hard-rule failures never cancel against semantic scores.
Candidate output is treated as untrusted data and secrets are redacted before it is sent to Hy3.

Statistical comparisons with fewer than ten cases are `INCONCLUSIVE` unless a newly introduced
critical hard-rule failure makes the result `BLOCKED`. This project is an evaluation aid, not a
claim that an LLM judge establishes objective truth.
