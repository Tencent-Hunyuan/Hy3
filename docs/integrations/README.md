# Hy3 integrations

Nine task-complete guides show how to use Hy3 from mainstream AI clients. Start with the tool you already use; shared TokenHub region, authentication, and safety details live in one place.

- [TokenHub cloud setup](tokenhub.md): region-matched endpoint, model access, authentication, model-list preflight, smoke test, and safety.
- [Local server setup](local-server.md): repository-documented vLLM/SGLang serving, protocol limits, and hardware feasibility.

Every version below is an exact **tested snapshot**, not a claimed minimum supported version or a statement about the current latest release. All client runs used model `hy3` and the Guangzhou / China-mainland TokenHub service. Singapore / global routing is documented but was not tested.

## Part A: integration verification matrix

| Tool | Tested snapshot | Test date | Protocol | Evidence | Result | Known limitation |
|:---|:---|:---|:---|:---|:---|:---|
| [Aider](aider.md) | `0.86.2` | 2026-07-09 | Chat Completions | [2 screenshots](aider.md#screenshots--gifs) | Client task completed | Repository map generated; local/tool-call/streaming paths unverified |
| [Cline](cline.md) | `4.0.6` | 2026-07-08 | Chat Completions | [2 screenshots](cline.md#screenshots--gif) | Client task completed | General-protocol tool calling unverified |
| [Codex CLI](codex-cli.md) | `0.142.5`; `0.144.1` compatibility check | 2026-07-09 | Responses | [4 screenshots](codex-cli.md#screenshots--gifs) | Exec and interactive tasks completed | Model-list and stream-delta warnings were visible |
| [Continue](continue.md) | `2.0.0` | 2026-07-08; secret check 2026-07-10 | Chat Completions | [2 screenshots](continue.md#screenshots--gifs) | Client task completed | Full VS Code restart required after secret changes |
| [Dify Cloud](dify.md) | provider `0.0.55` | 2026-07-10 | Chat Completions | [2 screenshots](dify.md#screenshots--gifs) | Workflow task completed | Pasted input only; no local repository access |
| [Roo Code](roo-code.md) | `3.54.0` | 2026-07-10 | Chat Completions | [2 screenshots](roo-code.md#screenshots--gif) | Client task completed | General tool calling and streaming unverified |
| [Kilo Code](kilo-code.md) | `7.4.1` | 2026-07-08 | Chat Completions | [2 screenshots](kilo-code.md#screenshots--gif) | Client task completed | Custom provider only; not Kilo Gateway |
| [OpenCode](opencode.md) | `1.17.15` | 2026-07-08 | OpenAI-compatible adapter | [2 screenshots](opencode.md#screenshots--gif) | CLI task completed | Local test configuration intentionally excluded |
| [CodeBuddy Code](codebuddy-code.md) | `2.117.2` | 2026-07-08 | Chat Completions | [2 screenshots](codebuddy-code.md#screenshots--gif) | Print-mode task completed | Tool-call flag not tested |

Screenshots prove the visible client result described by each guide; they are not endpoint-level request transcripts. Local self-hosting and any feature marked unverified were not silently inferred from those images. Existing media is retained as historical evidence even where a username, branch name, or working-tree noise remains visible.

## What each guide contains

Each guide preserves the issue-required workflow: installation and tested snapshot, exact base URL and model, authentication, protocol/provider selection, first chat, a real task, screenshots, and troubleshooting. Tool-specific differences stay in the guide; shared TokenHub facts stay in [tokenhub.md](tokenhub.md).

## Part B: Codex + Hy3 evidence-grounded spec diff reviewer

The reusable review engine is a standalone CLI. For issue #2, its primary documented workflow is invoked from Codex CLI after a developer stages a change.

Codex modifies code; the human chooses and stages the intended diff; the repository workflow invokes Hy3; local code validates the structured result and every cited spec/diff location; then Markdown and JSON are published with input hashes and execution provenance. The result is advisory and never edits code or Git state.

- Repository: [hy3-tokenhub-spec-diff-reviewer](https://github.com/Small-fish-QAQ/hy3-tokenhub-spec-diff-reviewer)
- Credential-free demo: `npm ci && npm run demo:offline` (always labelled `OFFLINE / FAKE`)
- Live preflight: `npm run check`
- Canonical Codex/staged command: `npm run review:staged -- --spec examples/spec.md --output reports/review.md`
- Browser console: `npm run serve`
- Architecture and Codex boundary: [Codex workflow guide](https://github.com/Small-fish-QAQ/hy3-tokenhub-spec-diff-reviewer/blob/main/docs/CODEX_WORKFLOW.md)
- Sanitized bounded live check: [2026-07-22 verification record](https://github.com/Small-fish-QAQ/hy3-tokenhub-spec-diff-reviewer/blob/main/docs/evidence/live-verification-2026-07-22.md)
- Existing ≤60-second evidence: [31-second live CLI-core recording, pinned to the historical implementation](https://github.com/Small-fish-QAQ/hy3-tokenhub-spec-diff-reviewer/blob/fecbbc49a4e3c21f2fe78b9ab3bcc9ee24ec156f/docs/assets/hy3-spec-to-diff-demo.mp4)

The current implementation adds a fixed JSON contract, one bounded repair attempt, locally verified evidence, official `GET /v1/models` preflight, bounded retry/backoff, deterministic offline fixtures/evaluation, provenance, and a thin local browser console. The pinned 31-second recording remains real live evidence for the CLI core but predates those additions; refreshed 50–55 second media must be recorded manually rather than simulated.

Limitations: local citation validation proves that quoted locations exist, not that a model conclusion is semantically correct. Prompt-injection risk is reduced, not eliminated. Live behavior still depends on TokenHub availability, model access, and the selected regional endpoint.
