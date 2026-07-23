# Rule Catalogue

Catalogue version: `1.0.0`

## 1. Rule model

Every finding references a stable rule ID. IDs are never recycled after release.
Rules declare whether their conclusion is deterministic or produced by Hy3.

Severity meanings:

- `critical`: inspection cannot be trusted or presents immediate high-impact risk;
- `error`: contract or protocol behavior is invalid or breaking;
- `warning`: likely ambiguity, unsafe design, or degraded interoperability;
- `info`: non-breaking improvement or migration note.

Hy3 rules are semantic judgments. They always include confidence and do not affect
the deterministic numeric score. Hybrid rules have a deterministic trigger and may
use Hy3 only to explain context; their score impact comes from the deterministic
part.

## 2. Protocol rules

| ID | Default severity | Source | Condition |
| --- | --- | --- | --- |
| `PROTO-001` | critical | deterministic | Target process does not start before the configured deadline. |
| `PROTO-002` | error | deterministic | Target stdout contains non-protocol bytes or ordinary log output. |
| `PROTO-003` | critical | deterministic | A received JSON-RPC message is malformed or exceeds parser limits. |
| `PROTO-004` | error | deterministic | MCP initialization returns an error or no valid result. |
| `PROTO-005` | warning | deterministic | Initialization omits required or expected server identity information. |
| `PROTO-006` | error | deterministic | `tools/list` fails, times out, or returns an invalid result shape. |
| `PROTO-007` | error | deterministic | Tool names are duplicated within the same server snapshot. |
| `PROTO-008` | warning | deterministic | A tool name violates the MCP-compatible project naming policy. |
| `PROTO-009` | warning | deterministic | Negotiated protocol metadata is internally inconsistent. |

## 3. Schema rules

| ID | Default severity | Source | Condition |
| --- | --- | --- | --- |
| `SCHEMA-001` | error | deterministic | A tool has no object-shaped input schema. |
| `SCHEMA-002` | error | deterministic | An input schema is not valid JSON Schema for the supported dialect. |
| `SCHEMA-003` | error | deterministic | `required` names a property that is not declared. |
| `SCHEMA-004` | warning | deterministic | A declared parameter lacks a useful description. |
| `SCHEMA-005` | warning | deterministic | A parameter is unconstrained where the contract advertises bounded behavior. |
| `SCHEMA-006` | error | deterministic | An enum is empty, duplicated after normalization, or conflicts with its default. |
| `SCHEMA-007` | error | deterministic | A declared output schema is invalid JSON Schema. |
| `SCHEMA-008` | warning | deterministic | A tool promises structured output but declares no output schema. |
| `SCHEMA-009` | error | deterministic | A deterministic fixture result does not conform to the declared output schema. |

`SCHEMA-009` is evaluated only against quality-gate-owned fixtures or a future
explicitly authorized execution mode. The first release does not invoke target
business tools merely to produce this rule.

## 4. Documentation and semantic rules

| ID | Default severity | Source | Condition |
| --- | --- | --- | --- |
| `DOC-001` | warning | deterministic | A tool description is absent or only whitespace. |
| `DOC-002` | warning | hybrid | A description is present but too generic to distinguish the tool's purpose. |
| `DOC-003` | warning | Hy3 | Tool name, description, and parameters express conflicting intent. |
| `DOC-004` | warning | Hy3 | Two or more tools overlap enough to make selection unreliable. |
| `DOC-005` | warning | Hy3 | Side effects, prerequisites, failure behavior, or output meaning are materially underspecified. |
| `DOC-006` | warning | hybrid | Untrusted instruction-like text appears in a description or schema annotation. |
| `DOC-007` | info | Hy3 | Terminology is inconsistent across related tools and may confuse users. |

## 5. Safety rules

| ID | Default severity | Source | Condition |
| --- | --- | --- | --- |
| `SAFETY-001` | error | hybrid | A tool declares `readOnlyHint: true` while its declared semantics indicate mutation. |
| `SAFETY-002` | warning | hybrid | A mutating tool omits or ambiguously declares destructive behavior. |
| `SAFETY-003` | warning | Hy3 | Idempotency hints conflict with the described operation. |
| `SAFETY-004` | warning | Hy3 | Open-world interaction is described but not reflected in annotations or documentation. |
| `SAFETY-005` | error | deterministic | A schema contains a credential-like parameter with an unsafe default value. |
| `SAFETY-006` | warning | Hy3 | A path, URL, query, or command-like parameter lacks a documented scope boundary. |
| `SAFETY-007` | warning | Hy3 | The contract encourages sensitive data transmission without consent or redaction guidance. |
| `SAFETY-008` | warning | deterministic | A target registry entry requests inheritance of a denied secret-like environment name. |

## 6. Compatibility rules

| ID | Default severity | Source | Condition |
| --- | --- | --- | --- |
| `COMPAT-001` | error | deterministic | A previously exposed tool is removed. |
| `COMPAT-002` | error | hybrid | A tool appears renamed without an explicit compatibility path. |
| `COMPAT-003` | error | deterministic | A new required input parameter is added. |
| `COMPAT-004` | error | deterministic | An input type or constraint is narrowed for previously valid values. |
| `COMPAT-005` | error | deterministic | An enum removes or changes an existing accepted value. |
| `COMPAT-006` | error | deterministic | An output contract removes or narrows previously declared data. |
| `COMPAT-007` | warning | deterministic | Safety annotations change toward greater side effects or open-world behavior. |
| `COMPAT-008` | warning | Hy3 | Text changed the tool's apparent semantics without a corresponding structural change. |
| `COMPAT-009` | info | deterministic | A compatible addition or widening should still be documented for consumers. |

Hy3 can add migration explanations but cannot downgrade `COMPAT-001`,
`COMPAT-003`, `COMPAT-004`, `COMPAT-005`, or `COMPAT-006`.

## 7. Robustness rules

| ID | Default severity | Source | Condition |
| --- | --- | --- | --- |
| `ROBUST-001` | error | deterministic | Target exceeds the configured total lifetime and requires termination. |
| `ROBUST-002` | error | deterministic | Target stdout or stderr exceeds its byte limit. |
| `ROBUST-003` | critical | deterministic | Target process cannot be completely terminated after timeout or cancellation. |
| `ROBUST-004` | warning | deterministic | Target exits unexpectedly before orderly inspection shutdown. |
| `ROBUST-005` | warning | deterministic | A declared contract exceeds configured tool, field, depth, or character limits. |
| `ROBUST-006` | warning | deterministic | The normalized snapshot is unstable across equivalent repeated discovery. |

## 8. Evidence requirements

Each rule family uses specific evidence:

| Family | Required evidence |
| --- | --- |
| Protocol | Lifecycle event, bounded output offset, or timeout name. |
| Schema | JSON Pointer into the normalized tool contract. |
| Documentation | Tool name plus description/parameter JSON Pointer and bounded excerpt. |
| Safety | Annotation and conflicting semantic/schema locations. |
| Compatibility | Baseline and current JSON Pointers with normalized before/after values. |
| Robustness | Named limit, configured value, observed value, and lifecycle phase. |

A rule that cannot provide its required evidence must not emit a finding.

## 9. Scoring policy `1.0.0`

The deterministic score starts at 100 across five independently bounded
categories:

| Category | Maximum |
| --- | ---: |
| Protocol | 25 |
| Schema | 20 |
| Contract clarity | 20 |
| Safety | 20 |
| Robustness | 15 |

Stage 4 applies the following fixed deductions:

| Rule | Category | Points |
| --- | --- | ---: |
| `PROTO-001` | protocol | 25 |
| `PROTO-002` | protocol | 8 |
| `PROTO-003` | protocol | 25 |
| `PROTO-004` | protocol | 10 |
| `PROTO-005` | protocol | 2 |
| `PROTO-006` | protocol | 10 |
| `PROTO-007` | protocol | 6 |
| `PROTO-008` | protocol | 2 |
| `SCHEMA-001` | schema | 8 |
| `SCHEMA-002` | schema | 8 |
| `SCHEMA-003` | schema | 6 |
| `SCHEMA-004` | schema | 2 |
| `SCHEMA-006` | schema | 6 |
| `SCHEMA-007` | schema | 8 |
| `DOC-001` | contract clarity | 5 |
| `DOC-002` | contract clarity | 3 |
| `DOC-006` | contract clarity | 4 |
| `SAFETY-001` | safety | 8 |
| `SAFETY-002` | safety | 5 |
| `SAFETY-005` | safety | 10 |
| `ROBUST-001` | robustness | 8 |
| `ROBUST-002` | robustness | 8 |
| `ROBUST-003` | robustness | 15 |
| `ROBUST-004` | robustness | 3 |
| `ROBUST-005` | robustness | 4 |

Findings are deduplicated by rule ID, target ID, tool name, and evidence path,
then sorted by that stable key. Each deduction is limited by the remaining score
in its category. Once a category reaches zero, later findings remain visible but
cannot deduct additional points.

If any critical finding is present, the overall score is capped at 40. The report
sets `critical_cap_applied` so consumers can distinguish a cap from ordinary point
deductions.

The following constraints also apply:

- Hy3-only rules never change the numeric score;
- repeated evidence does not cause duplicate deductions;
- a critical protocol or process-control failure caps the overall score;
- severity filtering does not change the score;
- reports include the catalogue version and every applied deduction.

Rules without a deduction in this table are reserved for later implementation
stages or intentionally report-only behavior. Adding or changing a deduction
requires a new scoring-policy version.
