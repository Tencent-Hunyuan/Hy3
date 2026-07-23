# Security Model

## 1. Scope

Hy3 MCP Quality Gate is a local stdio MCP server that launches other configured
local MCP servers for inspection. A child server runs with the quality gate's OS
identity, so process launch, environment handling, output parsing, and model prompts
are security boundaries.

This document defines mandatory controls for the first release. A feature that
cannot preserve these controls must be deferred or require an explicit design
revision.

## 2. Security invariants

1. MCP callers select a `target_id`; they never provide a command, executable path,
   argument vector, cwd, or environment value.
2. Targets are loaded from one validated registry at startup. The registry is not
   writable through MCP.
3. Child processes are spawned directly from an argument vector with no shell.
4. A target receives only explicitly inherited environment names plus fixed
   non-secret values from its registry entry.
5. Every child process has startup, request, output-size, and total-lifetime limits.
6. Timeout or cancellation terminates the complete child process group.
7. Target stdout is treated only as protocol data; quality-gate diagnostics use
   stderr.
8. Target text and Hy3 output are untrusted data and cannot alter system policy.
9. Secrets and personal absolute paths are redacted before storage, display, or
   model transmission.
10. The first release does not invoke target business tools or execute generated
    probes.
11. MCP annotations are advisory and cannot grant execution permission.
12. No credential value is committed in source, examples, fixtures, recordings, or
    evaluation artifacts.

## 3. Threats and controls

| Threat | Example | Required control | Residual risk |
| --- | --- | --- | --- |
| Arbitrary command execution | Caller supplies `sh -c ...` as a tool argument. | Tool schemas expose only registered target IDs; registry is startup-only; spawn without shell. | A malicious locally edited registry remains trusted configuration. |
| Argument injection | Target ID is interpreted as part of a command line. | Exact map lookup; registry command and args remain separate values. | The configured executable itself can be malicious. |
| Path traversal | Caller references a registry or snapshot outside the workspace. | No caller-controlled registry/snapshot path; normalize and validate configured cwd against allowed roots. | Symlink state can change after validation; process startup must minimize the race window. |
| Environment leakage | Child receives `HY3_API_KEY`, cloud tokens, or SSH variables. | Start from a minimal environment and inherit only named variables. | A permitted executable can read other same-user resources outside this process boundary. |
| Output denial of service | Child emits infinite stdout/stderr. | Independent byte caps, bounded buffers, deadlines, and process-group termination. | OS-level resource exhaustion before limits is possible without an external sandbox. |
| Orphan processes | Timeout kills only the parent. | Create and terminate an isolated child process group; test grandchildren. | Platform-specific process semantics require separate tests. |
| stdout protocol pollution | Target logs banners to stdout. | Incremental JSON-RPC framing and a dedicated deterministic finding; never silently discard pollution. | Recovery may be impossible for severely malformed streams. |
| Malformed protocol data | Deep JSON or invalid message IDs. | Bounded parser, structural validation, and safe error reporting. | Parser dependency vulnerabilities remain possible. |
| Prompt injection | Tool description says to ignore policy or reveal keys. | Delimit untrusted data, state its role, minimize prompt context, and validate model output. | A model can still produce a poor semantic judgment; it cannot change deterministic results. |
| Secret disclosure to Hy3 | Schema defaults or stderr contain tokens. | Redact before prompt assembly; omit raw stderr by default; add preflight secret scanning. | Heuristic redaction cannot guarantee discovery of every novel secret form. |
| Secret disclosure in reports | Provider errors echo request headers. | Map exceptions to stable public codes and sanitized messages; keep bounded diagnostics on stderr. | Operators may enable external debug tooling outside this project's control. |
| Misleading annotations | Destructive tool claims `readOnlyHint: true`. | Treat annotations as hints, apply semantic contradiction rules, never use them alone to authorize execution. | Static semantics cannot prove runtime behavior. |
| Generated harmful probes | Hy3 generates destructive paths or commands. | Generate only; never execute; validate against schemas; attach safety notes; reject disallowed patterns. | A user may manually execute exported cases elsewhere. |
| Supply-chain compromise | Installed dependency runs a malicious lifecycle script. | Lock dependencies, minimize dependency set, review package contents, and test a clean packed install. | Package manager and registry trust remain external. |
| Sensitive local metadata | Reports include `/Users/name/project`. | Replace allowed-root prefixes and user directories with stable placeholders. | File contents may still reveal identity and require redaction. |

## 4. Target registry policy

The registry is trusted local configuration, not user input. The planned structure
is demonstrated in [`../examples/targets.example.json`](../examples/targets.example.json).

Each target entry may define:

- a stable ID used by MCP tools;
- a human-readable description;
- an executable and argument array;
- a cwd relative to an approved root;
- a small map of fixed, non-secret environment values;
- a list of environment variable names allowed to be inherited;
- stricter timeout and output caps.

Target IDs must match `^[a-z][a-z0-9._-]{0,63}$`; they are opaque identifiers and
are never interpolated into commands, paths, logs, or environment names.

The registry must reject:

- unknown fields when strict validation is enabled;
- an empty executable or target ID;
- duplicate target IDs;
- shell metacharacters only when they are being used to imply shell evaluation;
- cwd values that resolve outside an allowed root;
- secret-looking fixed environment names or values;
- limits that exceed global hard caps.

The command is still trusted code. Registry validation reduces accidental exposure;
it is not an OS sandbox and must not be described as one.

## 5. Environment policy

Quality-gate configuration uses environment variables such as `HY3_API_KEY`, but a
target does not inherit the complete quality-gate environment. A child environment
is constructed from:

1. minimal platform variables needed for process startup;
2. names explicitly listed in `inherit_env`;
3. fixed non-secret values declared in the registry.

The following categories are denied by default:

- variables containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, or `CREDENTIAL`;
- cloud-provider credential variables;
- SSH and signing-agent variables;
- the quality gate's Hy3 credentials;
- CI job tokens.

An operator must not be able to bypass this policy from an MCP tool call.

## 6. Data flow to Hy3

Only the minimum normalized contract needed for semantic review is sent to Hy3.
Before transmission:

1. remove environment values, absolute cwd, raw stderr, and process metadata;
2. redact credential-like text and personal path prefixes;
3. cap tools, fields, descriptions, and total serialized characters;
4. wrap target content as untrusted data with a variable-length delimiter;
5. request a strict structured result without hidden reasoning;
6. validate locally and permit at most one bounded repair attempt.

Provider responses never override deterministic findings, scoring, process policy,
or execution permissions.

## 7. Logging and artifacts

- stdout is reserved for MCP JSON-RPC.
- operational logs go to stderr and are redacted.
- API request headers and environment dumps are never logged.
- fixtures contain synthetic values only.
- demo transcripts are sanitized before commit.
- evaluation outputs store normalized target IDs instead of absolute paths.
- generated tarballs, local registries, `.env` files, and raw recordings are ignored.

## 8. Safe degradation

Hy3 is optional for deterministic inspection. If its credentials are absent, the
provider is unavailable, or its output fails validation:

- `mcpq_inspect_server` remains fully deterministic;
- `mcpq_audit_contracts` returns `partial` with deterministic findings when those
  checks pass; a deterministic error remains `fail` even if Hy3 is unavailable;
- `mcpq_compare_contracts` preserves deterministic compatibility findings and an
  empty migration plan;
- `mcpq_generate_probe_suite` fails safely because generation is its core operation;
- no fallback fabricates an Hy3 result.

## 9. Explicitly deferred capabilities

The following require a new threat-model review:

- executing target tools;
- accepting target commands or registry paths from a caller;
- automatic patch application;
- network or HTTP transport;
- remote target discovery;
- persistent report databases;
- CI credentials or repository write access;
- probe execution in containers or OS sandboxes.
