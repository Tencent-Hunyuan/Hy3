# Architecture and Tool Contracts

## 1. Status

This document is the Stage 1 design contract for Hy3 MCP Quality Gate. Later
implementation changes may clarify details, but any incompatible change to the
security invariants or public tool contracts requires an explicit design update.

## 2. Goals

The first release must:

1. expose four clearly documented MCP tools over local stdio;
2. inspect pre-registered local MCP servers without accepting arbitrary commands;
3. distinguish deterministic findings from Hy3 semantic findings;
4. attach actionable evidence to every finding;
5. compare two declared MCP contracts for compatibility risk;
6. generate, but not execute, safe probe cases;
7. return both human-readable content and schema-valid structured content;
8. remain installable and verifiable without a live Hy3 key by using injected test
   doubles in automated tests.

## 3. Non-goals

The first release does not:

- execute arbitrary shell text;
- discover every MCP process on the host;
- call a target server's business tools;
- prove that tool annotations are truthful;
- modify a target repository or configuration;
- provide an HTTP transport or public deployment;
- use Hy3 output as the sole basis for protocol pass/fail or numeric scoring;
- expose hidden reasoning or request it as part of the response contract.

## 4. Trust model

| Input | Trust level | Treatment |
| --- | --- | --- |
| Quality gate source and packaged rule definitions | Trusted | Versioned and tested. |
| Target registry | Locally trusted configuration | Parsed and validated at startup; never accepted through a tool argument. |
| Target stdout/stderr, tool names, descriptions, and schemas | Untrusted | Bounded, parsed defensively, and delimited before any Hy3 request. |
| MCP annotations | Untrusted hints | Compared with declared semantics but never treated as proof. |
| Hy3 response | Untrusted generated data | Validated against a strict schema; one bounded repair attempt at most. |
| Environment variables | Sensitive configuration | Allowlisted, never returned, and redacted from diagnostics. |
| Tool caller arguments | Untrusted | Validated before registry access or model invocation. |

## 5. Components

```text
server.ts
  |
  +-- tool handlers
  |     +-- inspect
  |     +-- audit
  |     +-- compare
  |     `-- probes
  |
  +-- target registry ------ trusted targets.json
  +-- process runner ------- bounded child process, no shell
  +-- protocol inspector --- initialize, tools/list, shutdown
  +-- deterministic rules -- protocol/schema/safety/compatibility facts
  +-- Hy3 client ----------- semantic review with validated output
  `-- report composer ------ MCP text content + structuredContent
```

The inspector normalizes all discovered contracts before downstream use. Stable
normalization makes snapshots, hashes, comparisons, fixtures, and evaluation
results reproducible.

## 6. Shared data contracts

Registered target IDs must match `^[a-z][a-z0-9._-]{0,63}$`. Discovered MCP tool
names are evaluated against a project interoperability policy of 1 to 128 ASCII
letters, digits, underscores, hyphens, or dots. These checks do not rewrite names
unless mandatory credential or personal-path redaction applies; they otherwise emit
evidence-backed findings so the original contract remains inspectable.

### 6.1 Finding

Every issue uses the same representation:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `rule_id` | string | yes | Stable ID from the rule catalogue. |
| `severity` | `info \| warning \| error \| critical` | yes | User impact, not model confidence. |
| `source` | `deterministic \| hy3` | yes | Origin of the conclusion. |
| `message` | string | yes | Concise explanation of the problem. |
| `suggestion` | string | yes | Concrete remediation. |
| `target_id` | string | yes | Registered target under review. |
| `tool_name` | string or null | yes | Affected tool when applicable. |
| `evidence_path` | string | yes | JSON Pointer or protocol-event path. |
| `evidence_excerpt` | string or null | yes | Bounded and redacted evidence. |
| `confidence` | number or null | yes | `null` for deterministic rules; `0..1` for Hy3. |

Invariants:

- deterministic findings use `confidence: null`;
- Hy3 findings use a finite confidence between 0 and 1;
- evidence excerpts are optional, bounded, and redacted;
- a score cannot be changed by an Hy3-only finding;
- unknown rule IDs are rejected.

### 6.2 Scorecard

| Field | Type | Meaning |
| --- | --- | --- |
| `overall` | integer `0..100` | Weighted deterministic score. |
| `protocol` | integer `0..25` | Lifecycle and JSON-RPC behavior. |
| `schema` | integer `0..20` | Declared input/output contract validity. |
| `contract_clarity` | integer `0..20` | Deterministic documentation coverage only. |
| `safety` | integer `0..20` | Deterministic annotation and exposure checks. |
| `robustness` | integer `0..15` | Bounds, timeout, and process behavior. |
| `hy3_reviewed` | boolean | Whether semantic review completed successfully. |

The score weights are public and versioned. Reports also include raw findings so a
consumer never has to rely on a single aggregate number.

### 6.3 Target snapshot

A normalized snapshot contains:

- registry `target_id`;
- negotiated protocol version;
- redacted `serverInfo`;
- normalized, name-sorted tool contracts;
- capture timestamp as report metadata;
- a content hash calculated without timestamps or local absolute paths.

Snapshots never contain environment values, credentials, raw personal paths, or
unbounded stderr.

## 7. Public MCP tool contracts

### 7.1 `mcpq_inspect_server`

Starts a registered target, performs MCP initialization and `tools/list`, validates
the declared schemas, and returns a normalized snapshot.

Input:

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `target_id` | string | yes | Must match the registered-target pattern and exist in the startup registry. |
| `include_schemas` | boolean | no | Default `true`; controls report verbosity, not validation. |
| `timeout_ms` | integer | no | `500..30000`; capped by the registry maximum. |

Structured output:

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | `pass \| fail` | Whether deterministic inspection completed and produced a snapshot without error-level findings. |
| `target_id` | string | Resolved registry target. |
| `protocol_version` | string or null | Negotiated version, if initialization succeeded. |
| `server_info` | object or null | Redacted MCP server information. |
| `tools` | array | Normalized discovered tool contracts. |
| `snapshot_hash` | string or null | Stable content hash when discovery succeeds. |
| `findings` | Finding[] | Deterministic findings only. |
| `duration_ms` | integer | Total bounded inspection duration. |

Expected failures such as timeout or invalid target output are returned as tool
results with structured findings. Invalid quality-gate arguments remain protocol
input errors.

### 7.2 `mcpq_audit_contracts`

Runs inspection, deterministic quality rules, and optional Hy3 semantic review.

Input:

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `target_id` | string | yes | Must resolve in the registry. |
| `reasoning_effort` | `no_think \| low \| high` | no | Default `high`. |
| `include_hy3` | boolean | no | Default `true`; false enables deterministic offline audit. |
| `minimum_severity` | `info \| warning \| error \| critical` | no | Default `info`; presentation filter only. |

Structured output:

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | `pass \| fail \| partial` | `partial` means deterministic audit succeeded but Hy3 did not. |
| `target_id` | string | Audited target. |
| `snapshot_hash` | string | Snapshot used for both audit paths. |
| `scorecard` | Scorecard | Reproducible deterministic score. |
| `deterministic_findings` | Finding[] | Rule-engine results. |
| `hy3_findings` | Finding[] | Validated semantic results. |
| `summary` | string | Concise report; states when Hy3 was skipped or unavailable. |
| `model_metadata` | object or null | Model name, effort, latency, and usage when available; no hidden reasoning. |

### 7.3 `mcpq_compare_contracts`

Compares two registered target versions. The baseline and current target must be
different registry entries; the tool never accepts executable commands or arbitrary
snapshot file paths.

Input:

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `baseline_target_id` | string | yes | Existing registry target. |
| `current_target_id` | string | yes | Existing registry target; different from baseline. |
| `include_non_breaking` | boolean | no | Default `true`. |
| `reasoning_effort` | `no_think \| low \| high` | no | Default `high`. |
| `include_hy3` | boolean | no | Default `true`. |

Structured output:

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | `compatible \| breaking \| partial` | Deterministic compatibility result or partial semantic review. |
| `baseline_hash` | string | Stable baseline snapshot hash. |
| `current_hash` | string | Stable current snapshot hash. |
| `changes` | array | Added, removed, narrowed, widened, or semantically changed items. |
| `findings` | Finding[] | Compatibility findings with before/after evidence paths. |
| `migration_plan` | array | Ordered, validated migration steps; empty when Hy3 is disabled. |
| `model_metadata` | object or null | Sanitized model call metadata. |

Structural compatibility is deterministic. Hy3 may identify semantic risk and
explain migration impact, but cannot downgrade a deterministic breaking change.

### 7.4 `mcpq_generate_probe_suite`

Generates safe, schema-valid test cases for one discovered tool. It does not execute
the cases.

Input:

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `target_id` | string | yes | Existing registry target. |
| `tool_name` | string | yes | Must exist in the discovered tool list. |
| `profile` | `normal \| boundary \| error \| adversarial \| balanced` | no | Default `balanced`. |
| `max_cases` | integer | no | `1..30`, default `12`. |
| `reasoning_effort` | `no_think \| low \| high` | no | Default `high`. |

Structured output:

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | `complete \| partial` | Whether all requested cases passed local validation. |
| `target_id` | string | Selected target. |
| `tool_name` | string | Selected tool. |
| `snapshot_hash` | string | Contract used for generation. |
| `cases` | ProbeCase[] | Generated but unexecuted cases. |
| `rejected_case_count` | integer | Cases dropped by local validation. |
| `warnings` | string[] | Bounded limitations or safety notes. |
| `model_metadata` | object | Sanitized model call metadata. |

Each ProbeCase contains a stable local ID, category, purpose, JSON arguments,
expected outcome class, safety note, and evidence explaining which contract element
motivated the case. The quality gate rejects cases that violate the target's input
schema unless their explicit purpose is schema-error testing.

## 8. Error model

Errors are divided into three groups:

1. **Caller errors:** invalid target ID, invalid enum, impossible limits. Returned as
   MCP input errors without starting a process or calling Hy3.
2. **Target findings:** timeout, malformed stdout, failed initialization, invalid
   schema. Returned as successful tool transport with structured `fail` status and
   evidence.
3. **Dependency degradation:** Hy3 unavailable or output invalid. Deterministic work
   remains available and the result becomes `partial` where the tool contract allows
   it.

No error includes secrets, full environment contents, unbounded target output, or
unsanitized local absolute paths.

## 9. Scoring invariants

- deterministic rules alone determine the numeric score;
- critical failures cap the overall score according to the versioned scoring policy;
- duplicate findings from multiple deterministic checks are deduplicated by rule ID,
  target, tool, and evidence path;
- filtering by severity changes presentation only, never the score;
- Hy3 failure cannot improve or reduce the deterministic score;
- the report records the rule-catalogue version used for scoring.

## 10. Acceptance gates for implementation stages

- **Protocol gate:** an official MCP SDK client can initialize the quality gate and
  list exactly four public tools.
- **Inspection gate:** good, timeout, malformed, and stdout-polluting fixtures are
  classified deterministically with no orphan child process.
- **Audit gate:** every implemented rule has a positive and negative fixture.
- **Hy3 gate:** semantic output validates against its schema and degrades cleanly on
  provider failure.
- **Compatibility gate:** known breaking changes cannot be downgraded by Hy3.
- **Delivery gate:** a clean package install works in CodeBuddy and Cursor and the
  committed verification record contains no credential or personal path.
