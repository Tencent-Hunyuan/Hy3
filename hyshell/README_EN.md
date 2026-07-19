# hyshell — a Hy3-powered terminal command assistant

> **Speak naturally, get commands; danger is reviewed before you hit Enter.**
> `hyshell` = **Hy**3 + **shell**: natural language → shell command, a two-layer safety engine grades the danger first, and failed commands are diagnosed and repaired by Hy3 itself.

English | [中文](README.md)

Entry for the 2026 Rhino-Bird open-source program, [Hy3 issue #4 "Build a vibe-coded application powered by Hy3"](https://github.com/Tencent-Hunyuan/Hy3/issues/4). Built entirely via AI pair-programming (vibe coding). Hy3 is used **only through its OpenAI-compatible API** — no training, no finetuning, no local inference deployment.

---

## End-to-end demos (two flows, offline-reproducible)

**Demo 1 · Daily flow**: natural language → Hy3 plans a command (Chinese explanation + risk grade) → confirmation gate → real execution

![Demo 1: natural language to command execution](assets/demo-1-daily.gif)

**Demo 2 · Safety guard + self-healing**: `rm -rf` is intercepted by both the model grade and the local rule engine → the user presses `a` and Hy3 proposes a safer alternative (list old logs read-only, delete nothing) → then `head` on a missing file fails → Hy3 reads exit code / stderr / directory listing, diagnoses "you meant report.md" → retry succeeds

![Demo 2: danger interception and error self-healing](assets/demo-2-guard-fix.gif)

> Both GIFs are **real terminal runs** of this repository's code in offline demo mode (clearly labeled **OFFLINE DEMO MODE (fake Hy3 backend)** at the top), rendered frame-by-frame by `demo/record_gifs.py`, byte-level reproducible. See [Re-recording](#re-recording--using-a-real-key) for real-key recordings.

## 30-second start (zero config, zero API key)

```bash
cd hyshell
pip install -e .
hyshell demo daily        # watch an end-to-end flow immediately (offline fake backend)
hyshell                   # interactive REPL (auto offline mode without a key)
hyshell doctor --ping     # environment check + backend connectivity test
```

Without installing: `PYTHONPATH=src python -m hyshell demo daily`.

## Hy3's role in the system (hard requirement of the issue)

Hy3 is hyshell's **only brain**. It appears at 4 points, all via the OpenAI-compatible `chat.completions` API (single model gateway in code: `src/hyshell/llm.py :: Hy3Client`):

| # | Call site | TASK envelope | Hy3 output (strict single-JSON contract) |
|---|---|---|---|
| 1 | **Command planning** | `## TASK: plan` | `{command, explanation, risk, risk_reasons, notes}` |
| 2 | **Danger explanation** | (returned with plan) | `risk ∈ {safe, caution, dangerous}` + reasons |
| 3 | **Safer alternative** | `## TASK: alt` | after the user rejects a dangerous command: a "read-only first, human decides" alternative |
| 4 | **Error diagnosis & repair** | `## TASK: fix` | given exit code + stderr tail + dir listing → `{diagnosis, command, confidence}` |

**Why this scenario fits Hy3** (each maps to a strength advertised in the Hy3 README):

- *Output-format stability* ("Stability of tool calls and output formats … output constraints") → hyshell's entire interaction is built on a strict "exactly one JSON object" contract;
- *Anti-hallucination* (hallucination rate 12.5% → 5.4%) → risk reasons and diagnoses must stick to the evidence; the `fix` envelope only carries the real stderr and directory listing;
- *Agentic error recovery* → the fail → diagnose → repair → retry loop is the minimal closed-loop showcase of this capability;
- *256K context* → long stderr and large directory listings fit into repair requests untruncated.

**Explicit statement**: no training, no finetuning, no local inference in this project; the model is only called via API (issue requirement #1).

## Architecture

```
natural language ─▶ ① plan ────── Hy3 API (strict JSON contract) ──▶ CommandPlan
                                      │
              ② two-layer safety: final = max(model risk, local rule engine)
                 └ 21 local rules (rm -rf / find -delete / shred / dd / mkfs / fork bomb / curl|sh / …);
                   the model can NEVER downgrade a local finding (test-locked)
                                      │
              ③ confirmation gate (graded interaction)
                 safe: Enter          caution: y/N (default N)     dangerous: type RUN verbatim
                 (with --yes, dangerous is still refused)
                                      │
              ④ executor (bash -c, timeout kills the process group, output truncation)
                                      │ exit ≠ 0
              ⑤ fix loop ── Hy3 API (command + exit + stderr + dir listing) ──▶ FixSuggestion
                 └ repaired commands pass the SAME assessment + gate; ≤ 2 retries
                                      │
              ⑥ JSONL history (~/.hyshell/history.jsonl) + session summary table
```

Modules: `config` (env-driven backend switch) · `llm` (Hy3 client + prompts) · `fake_backend` (deterministic offline fake) · `safety` (local rule engine) · `executor` · `fixloop` · `app` (state machine) · `tui` (rich rendering + input abstraction) · `history` · `demo_flows` (scripted demos) · `demo/` (GIF pipeline).

## Install & configure

Only 4 common dependencies: `openai` `rich` `httpx` `pydantic` (Python ≥ 3.10).

```bash
pip install -e .          # or: pip install -e '.[demo]'   (adds pillow for GIF recording)
```

Backend selection is **purely environment-driven** (zero hardcoded secrets):

| Variable | Default | Meaning |
|---|---|---|
| `HY3_API_KEY` | (empty) | empty = offline demo mode; set it to switch to the real backend |
| `HY3_API_BASE` | `http://127.0.0.1:8000/v1` | self-hosted vLLM/SGLang default; Tencent Cloud endpoint below |
| `HY3_MODEL` | `hy3` | model name (vLLM `--served-model-name hy3`) |
| `HY3_TEMPERATURE` / `HY3_TOP_P` | `0.9` / `1.0` | follows the Hy3 repo README recommendations |
| `HY3_REASONING_EFFORT` | (not sent) | only sent when explicitly set, via `extra_body.chat_template_kwargs` (`no_think`/`low`/`high`) |
| `HY3_TIMEOUT` | `60` | per-request timeout (seconds) |
| `HYSHELL_OFFLINE` | (empty) | `1` = force offline even with a key |
| `HYSHELL_MAX_FIX_RETRIES` | `2` | fix-loop retry cap |
| `HYSHELL_HOME` | `~/.hyshell` | history directory |

Three real-backend setups (template: [.env.example](.env.example)):

```bash
# A. Tencent Cloud Hunyuan OpenAI-compatible endpoint (see Tencent Cloud console docs)
export HY3_API_BASE=https://api.hunyuan.cloud.tencent.com/v1
export HY3_API_KEY=<your key>

# B. Self-hosted vLLM (command from the Hy3 repo README)
vllm serve tencent/Hy3 --served-model-name hy3 &
export HY3_API_BASE=http://127.0.0.1:8000/v1
export HY3_API_KEY=EMPTY

# C. Self-hosted SGLang: same, just point HY3_API_BASE at its port
```

Then check: `hyshell doctor --ping` (table shows mode/endpoint/model/masked key and sends one minimal request).

## Usage

```
hyshell                          # interactive REPL (default); exit to quit; history for last 10
hyshell ask "delete the logs" [--yes]
hyshell demo daily|guard_fix     # scripted demos (--backend real to replay against real Hy3)
hyshell history [--last N]
hyshell doctor [--ping]
common flags: --offline  --yes  --version
```

Confirmation gate grades (**core safety design**):

| Final risk | Interactive | `--yes` non-interactive |
|---|---|---|
| safe | Enter to run · `e` edit · `s` skip | run |
| caution | `y/N` (default N) · `e` edit · `s` skip | run + warning |
| dangerous | **type `RUN` verbatim** · `a` ask Hy3 for a safer alternative · `s` skip | **refused** |

- final risk = max(model grade, local rule engine) — a model "safe" cannot override a local `rm -rf` hit;
- user-edited commands are re-assessed by the local engine and re-gated;
- fix-loop suggestions pass the **same** assessment and gate (a dangerous "fix" still requires `RUN`).

## What is the offline demo mode (fake Hy3 backend)?

Without `HY3_API_KEY`, hyshell runs in offline demo mode, prominently labeled **OFFLINE DEMO MODE (fake Hy3 backend)**.

- **What it is**: an `httpx.MockTransport` injected into the genuine openai SDK — real prompt construction, real request serialization, real response parsing all execute; only the HTTP layer is replaced by an in-process deterministic rule table (`src/hyshell/fake_backend.py`);
- **What it guarantees**: no random source, same input → same bytes → demo transcripts, GIFs and all 132 tests are reproducible;
- **What it covers**: task envelopes (`## TASK: plan|fix|alt`), JSON contract parsing, two-layer safety merge, confirmation gates, fix loop, history persistence — the entire product path;
- **What it cannot do**: answer requests outside its rule table (it honestly returns a no-op placeholder saying so), or prove real Hy3 output quality — verify that with a real key (next section).

## Re-recording / using a real key

```bash
# offline re-record (byte-identical to the GIFs in this repo)
python demo/record_gifs.py --flow all

# real backend replay/re-record (needs a key; real model output is non-deterministic,
# frames will differ, and scripted inputs may diverge → the flow ends early by design)
export HY3_API_KEY=...; export HY3_API_BASE=...
hyshell demo daily --backend real
python demo/record_gifs.py --flow all --backend real
```

Recording extras: `pip install -e '.[demo]'`; the first recording auto-downloads a CJK mono font into `~/.cache/hyshell-fonts/` (~16MB, recording only, never committed). Narrow-glyph rendering needs a monospace TTF on the system — common Debian/Fedora/Arch/macOS paths (DejaVu/Menlo) are probed automatically; if none is found it falls back to PIL's built-in bitmap font with a printed warning (GIFs still render, with degraded quality). GIFs come from a self-contained renderer: rich ANSI capture → SGR-subset parser → Pillow per-cell drawing (`demo/ansi2gif.py`).

## Tests & quality

```bash
pip install -e '.[dev]'       # dev/test extras: pytest + pillow
python -m pytest tests -q     # 132 passed, ~5s; fully offline, zero network, deterministic
```

(Without pillow the GIF-pipeline tests skip themselves; the core suite is unaffected.)

- backend-switch matrix, fake-backend determinism (same prompt → same bytes), tolerant JSON extraction (fences/prose/nested braces);
- safety engine: 47 table-driven cases (28 dangerous + 7 caution positives, 12 safe negatives) + merge invariant (model cannot downgrade local findings);
- e2e: both demo flows run in-process + **transcripts byte-equal across two runs** + "no RUN typed → dangerous command never executes" (executor spy) + `--yes` still refuses dangerous;
- GIF pipeline: SGR parsing, wide-char two-cell layout, mini-GIF generation, and validation of the shipped GIFs (frames/size/duration: <2MB, ≤2min).

**Honesty boundary — verified here vs. what you should verify locally**:

| Item | Status |
|---|---|
| All 132 tests, both offline demos, both GIF recordings | ✅ actually run and verified on the dev machine (no GPU, no external key) |
| Real Hy3 backend connectivity & output quality | ⚠ no `HY3_API_KEY` on the dev machine — untested; smoke-test with `hyshell doctor --ping`, then `hyshell demo daily --backend real` |
| Fallback when the real model violates the JSON contract | code path tested (tolerant extraction + `ModelOutputError` with a raw snippet); real-world trigger rate not measured — see FAQ |

## AI pair-programming log (CodeBuddy collaboration record)

Per the issue's request, this project was built by **vibe coding (AI pair-programming)**: the human owned topic choice, architecture trade-offs and acceptance review; the AI pair produced code and tests; everything was human-reviewed before commit. Per-module log (the "CodeBuddy session" column is reserved for the author to attach session links/screenshots):

| Module | AI contribution | Human review points | CodeBuddy session |
|---|---|---|---|
| Architecture & scenario choice | scenario comparison table, two-layer safety proposal | picked scenario (a); confirmed "model can never downgrade local findings" | (tbd) |
| `llm.py` + prompt contract | JSON envelope design, tolerant extractor | reviewed prompt wording & risk rubric | (tbd) |
| `fake_backend.py` | MockTransport approach, deterministic rule tables | cross-checked rules against demo scripts | (tbd) |
| `safety.py` (21 rules) | regex/matcher drafts with Chinese reasons | verified positives/negatives (47 test cases) | (tbd) |
| `app.py`/`fixloop.py` state machine | gate interaction & fix loop | walked dangerous paths: --yes refusal, verbatim RUN | (tbd) |
| Test suite (132 cases) | case generation, spy fixtures | strengthened assertions; zero-execution invariant | (tbd) |
| GIF pipeline `demo/` | SGR parser, per-cell renderer | frame-by-frame inspection (CJK alignment, colors) | (tbd) |
| Bilingual README | drafts & structure | fact check (env table, honesty boundary) | (tbd) |

## FAQ

- **Why is dangerous still refused under `--yes`?** In non-interactive contexts (scripts/CI) nobody reads warnings; "a human must type RUN" is the last human latch — better to abort than to mass-delete.
- **Why temperature 0.9 by default?** It follows the Hy3 repo README's recommended inference parameters (`temperature=0.9, top_p=1.0`); lower it for more conservative JSON output.
- **What if the real model emits invalid JSON?** The extractor tolerates fences/prose/nesting; if it still fails, a `ModelOutputError` with a raw snippet is raised and the turn ends safely without executing anything. Try `HY3_REASONING_EFFORT=low` or a lower temperature.
- **Windows?** The executor needs `/bin/bash`; native Windows is unsupported, WSL works fine.
- **Why is duration in the history but never on screen?** Screen transcripts must be byte-deterministic (shared by demos/GIFs/tests); durations go only to `history.jsonl`.

## License

Same as the upstream repository: Apache-2.0. Every source file carries an SPDX header; no hardcoded secrets (enforced by a scanning test).
