# Hy3 MCP Quality Gate

> Work in progress: the TypeScript stdio server and four-tool surface are runnable;
> protocol inspection and semantic stages are tracked below.

Hy3 MCP Quality Gate is a planned local stdio MCP server that inspects other
pre-registered MCP servers. It combines deterministic protocol and JSON Schema
checks with Hy3 semantic review to produce evidence-backed findings, compatibility
reports, and safe test cases.

The Stage 1 product contract remains authoritative for the implementation. Current
runtime status is stated explicitly in the delivery roadmap so incomplete tools are
not presented as operational.

## Problem

MCP servers can be syntactically valid while remaining difficult or unsafe for an
agent to use. Common problems include ambiguous tool descriptions, incomplete
parameter documentation, incompatible contract changes, misleading safety hints,
stdout protocol pollution, and unbounded startup behavior. These problems are hard
to catch with a single kind of test:

- deterministic checks are reliable for protocol and schema facts;
- semantic checks are needed for descriptions, intent, overlap, and migration impact.

The quality gate keeps those two sources separate. It never presents a Hy3 opinion
as a protocol fact.

## Planned MCP tools

| Tool | Purpose | Hy3 role |
| --- | --- | --- |
| `mcpq_inspect_server` | Start a registered target, negotiate MCP, list tools, and validate its declared contracts. | Summarize impact only; pass/fail remains deterministic. |
| `mcpq_audit_contracts` | Produce deterministic and semantic findings with evidence paths and a scorecard. | Review ambiguity, overlap, misleading descriptions, and annotation semantics. |
| `mcpq_compare_contracts` | Compare two registered server versions and identify compatibility changes. | Explain semantic changes and propose a migration plan. |
| `mcpq_generate_probe_suite` | Generate schema-valid normal, boundary, error, and adversarial probe cases without executing them. | Generate scenario-aware cases and expected behavior. |

The complete inputs, outputs, invariants, and error behavior are defined in
[`docs/design.md`](docs/design.md).

## Design principles

1. **Facts and judgments stay separate.** Every finding declares whether it came
   from deterministic code or Hy3.
2. **Evidence is mandatory.** A finding points to a protocol event, JSON Pointer,
   tool name, or version change.
3. **Commands are configuration, not tool input.** Callers select a trusted
   `target_id`; they cannot supply a shell command through an MCP call.
4. **Inspection is non-invasive by default.** The first release performs
   initialization and discovery but does not invoke target business tools.
5. **Untrusted text remains data.** Target descriptions, schemas, stderr, and model
   output cannot redefine the quality gate's instructions.
6. **Scores remain reproducible.** Only deterministic findings change the numeric
   conformance score; Hy3 findings are reported separately with confidence.

## Planned architecture

```text
MCP client
    |
    | stdio tools/call
    v
Hy3 MCP Quality Gate
    |-- target registry (trusted local configuration)
    |-- bounded stdio inspector
    |-- deterministic rule engine
    |-- Hy3 semantic auditor
    `-- structured report composer
             |
             v
       findings + scorecard + evidence
```

Targets are declared before startup. See
[`examples/targets.example.json`](examples/targets.example.json) for the planned
configuration shape.

## Security boundary

The quality gate launches configured local processes, so its security boundary is
part of the product rather than an implementation detail. The first release will:

- resolve only known target IDs from a local registry;
- spawn processes without a shell;
- use an explicit environment allowlist;
- bound startup time, request time, stdout, stderr, and total process lifetime;
- terminate the complete child process group on timeout;
- redact credential-like values before logs, reports, or Hy3 requests;
- reserve stdout for MCP JSON-RPC and write diagnostics to stderr;
- treat MCP annotations as untrusted hints;
- avoid calling target business tools.

See [`docs/security.md`](docs/security.md) for threats, controls, and residual risks.

## Rule catalogue

Stable rule IDs are grouped into protocol, schema, documentation, safety,
compatibility, and robustness families. See
[`docs/rule-catalog.md`](docs/rule-catalog.md).

## Delivery roadmap

- **Stage 1 — design baseline:** product scope, tool contracts, threat model, rule
  catalogue, and target registry example.
- **Stage 2 — runnable server:** TypeScript package, stdio server, four registered
  tools, build, lint, and test commands.
- **Stage 3 — protocol inspector:** safe target process management and
  `mcpq_inspect_server`.
- **Stage 4 — deterministic audit:** evidence model, rules, and reproducible score.
- **Stage 5 — Hy3 audit:** validated structured semantic findings.
- **Stage 6 — compatibility and probes:** contract diff and safe test generation.
- **Stage 7 — evaluation:** intentionally broken fixture servers and generated
  metrics.
- **Stage 8 — delivery:** package verification, CodeBuddy and Cursor recordings,
  bilingual documentation, and demo GIF.

## Non-goals for the first release

- a web dashboard or hosted service;
- automatic source-code modification;
- accepting arbitrary commands from MCP tool arguments;
- executing generated probes or destructive target tools;
- claiming that MCP annotations prove actual target behavior;
- replacing official MCP SDK or Inspector testing;
- grading general code quality unrelated to the exposed MCP contract.

## Configuration policy

Hy3 credentials will be provided only through environment variables:

```text
HY3_API_KEY
HY3_BASE_URL
HY3_MODEL
HY3_REASONING_EFFORT
HY3_TIMEOUT_MS
```

No credential value may be stored in a target registry, fixture, transcript,
evaluation result, or committed client configuration.

## Documentation

- [Architecture and tool contracts](docs/design.md)
- [Security model](docs/security.md)
- [Rule catalogue](docs/rule-catalog.md)
- [Target registry example](examples/targets.example.json)
