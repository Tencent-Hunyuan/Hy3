# Live Hy3 fixture gate

- Date: 2026-07-22
- Provider: `tencent-tokenhub`
- Model: `hy3`
- Gate version: `legacy-first-divergence-v1`
- Input: the two public synthetic built-in fixtures
- Validation: strict schema, reference closure, deterministic replay rules, and exact annotated first-divergence match

| Fixture | Gate | First step | Latency | Tokens | Attempts | Error |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `coding-loop` | pass | `step-006-repeat-patch` | 12062 ms | 2348 | 1 | `-` |
| `research-grounding` | pass | `step-006-unsupported-causal-leap` | 72893 ms | 2460 | 2 | `-` |

No key, request ID, account data, raw prompt, or hidden reasoning is stored.

This historical artifact predates the full-annotation fixture gate. It does not contain the model drafts needed to reconstruct required-evidence, replay precision/recall, validation-gate coverage, or dangerous-suggestion scores. A `pass` here means the v1 structural and first-divergence checks passed.
