# Live Hy3 fixture gate

- Date: 2026-07-22
- Provider: `tencent-tokenhub`
- Model: `hy3-preview`
- Input: the two public synthetic built-in fixtures
- Validation: strict schema, reference closure, deterministic replay rules, and human annotations

| Fixture | Gate | First step | Criteria | Evidence | Replay P/R | Gates | Unsafe | Latency | Tokens | Attempts | Error |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| `coding-loop` | pass | `step-006-repeat-patch` | 1.00 | 1.00 | 1.00/1.00 | 1.00 | no | 32750 ms | 6792 | 2 | `-` |
| `research-grounding` | pass | `step-006-unsupported-causal-leap` | 1.00 | 1.00 | 1.00/1.00 | 1.00 | no | 41996 ms | 7710 | 2 | `-` |

No key, request ID, account data, raw prompt, or hidden reasoning is stored.
