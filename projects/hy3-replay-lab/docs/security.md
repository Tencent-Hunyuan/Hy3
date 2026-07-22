# Security model

ReplayLab treats the task bundle as hostile text and limits both what enters the model boundary and what can leave it. This document describes the MVP controls, not a claim of production multi-tenant isolation.

## Assets and trust boundaries

Protected assets are the Hy3 credential, local files outside the selected import, provider request metadata, private trace text, and the integrity of the accepted replay report. Trust boundaries are the local file picker, browser-to-local-API request, backend-to-Hosted-API request, and model-output validator.

The frontend contains no credential input. `GET /api/health` returns only a boolean configuration flag. The backend reads a key through `SecretStr` from `HY3_API_KEY`; the base URL and model are read only from `HY3_BASE_URL` and `HY3_MODEL`. A base URL with embedded credentials, query, or fragment is rejected.

## Input controls

- Accepted extensions are `.json`, `.md`, and `.txt`; accepted MIME types must match.
- A filename must be safe ASCII, contain no path separator or `..`, and not use a Windows reserved device name.
- NUL/binary input, archives, and multiple/ambiguous Markdown payloads are rejected.
- The file text limit is 128,000 bytes. The normalized aggregate limit is 256,000 bytes, with explicit per-field, criteria, step, evidence, and reference-list limits.
- IDs, sequences, and references must be unique, ordered, and closed over the supplied bundle. Extra schema fields are forbidden.
- Built-in fixture reads use an allowlist plus resolved-path containment and byte limits.

No imported content is executed. ReplayLab does not invoke a shell, run code, browse a supplied URL, inspect a repository, expand an archive, resolve a user path, or write an imported task to disk.

## Prompt-injection and evidence controls

Trace steps, tool outputs, evidence, filenames, URLs, and prior model text are explicitly labeled untrusted data. The system instruction prohibits following instructions found there, inventing evidence, browsing, execution, or unknown IDs. It also prohibits exposing hidden chain-of-thought and asks only for concise evidence-grounded explanations.

Model instructions are not the security boundary. Deterministic validation rejects:

- missing, duplicate, unknown, or out-of-order references;
- coverage that does not exactly match criterion order;
- a divergence that is not a supplied step;
- finding evidence created after the claimed first divergence, and impact steps at or before it;
- a preserved set that is not the exact prefix before the divergence;
- a replay set that is not chronologically ordered;
- findings, actions, validation gates, stop conditions, or prohibited actions without valid evidence;
- unsafe or semantically inconsistent no-divergence forms.

## Credential and error hygiene

Credential-like assignments, authorization values, cookies, connection strings, and explicit secret values are redacted before provider submission and again before report assembly. The controlled-repair context is redacted and truncated to 20,000 characters.

Errors surfaced to the UI are fixed, bounded categories. They do not include authorization material, upstream bodies, raw prompts, complete input, account data, request IDs, or connection strings. Evaluation artifacts store only non-sensitive configuration, aggregate usage, validation outcomes, and bounded error codes.

Repository hygiene checks scan tracked deliverables for credential patterns and personal absolute paths. The `.env` file, virtual environments, caches, build products, browser traces, and logs are ignored. `.env.example` contains names and public defaults only.

## Availability controls

- HTTPX connect timeout: 10 seconds.
- HTTP request timeout: 60 seconds.
- Provider output: 256,000 bytes maximum.
- Attempts: at most three by default; a cancellation received by the provider coroutine is never retried.
- Retry set: transport failures and HTTP 429/502/503/504 only.
- `Retry-After`: accepted as bounded seconds from 0 through 30; otherwise bounded exponential backoff is used.
- HTTP 400/401/403 and other permanent statuses fail immediately.
- The broad live evaluation uses concurrency two and a 90-second per-case outer ceiling.

These controls bound one request but are not a global rate limiter or tenant quota system.
The browser's stop-wait control aborts its own response handling. It does not promise that an already accepted server request has been cancelled; server work remains subject to the limits above.

## Known limitations

- The app is for trusted local operation and has no authentication, TLS termination, tenant separation, persistence policy, or deployment hardening.
- Redaction is defense in depth, not a universal data-loss-prevention engine. Do not import secrets or private traces unless their disclosure to the configured provider is authorized.
- Evidence closure proves that a citation exists in the imported bundle, not that its real-world content is true.
- Hy3 explanations remain probabilistic. Deterministic invariants constrain structure and provenance but cannot guarantee causal correctness.
- Live and offline UI recordings are stored separately with visible mode labels. The earlier bounded `hy3` allocation failure, current 2/2 `hy3-preview` fixture gate, and live browser evidence are all retained without relabeling results.

Security regression coverage is listed in [verification.md](verification.md), and the execution boundary is illustrated in [architecture.md](architecture.md).
