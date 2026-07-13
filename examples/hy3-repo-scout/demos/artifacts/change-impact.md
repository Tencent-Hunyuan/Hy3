# Hy3 Repo Scout Report

# Investigation Report: Changing the Default `reasoning_effort` from `no_think` to `high`

## Executive Summary

**Fact:** The example application `examples/hy3-repo-scout` already defaults `reasoning_effort` to `high` in both its code and documentation, and its unit tests already assert `high` as the default [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L72-L72], [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L151-L151], [examples/hy3-repo-scout/.env.example:L7-L7], [examples/hy3-repo-scout/README.md:L73-L73], [examples/hy3-repo-scout/README_CN.md:L70-L70], [examples/hy3-repo-scout/tests/test_config.py:L27-L27], [examples/hy3-repo-scout/tests/test_client.py:L24-L24].

**Inference:** The investigation premise ("change the example default from `no_think` to `high`") is therefore already satisfied for the example app. The only remaining places that still present `no_think` as a *default* (rather than a valid option or a fast-thinking example) are the root `README.md` / `README_CN.md` API call examples and the finetune training-data fallback in `train.py`.

**Recommendation:** Synchronize the root README API examples and (optionally) the finetune training-data default to reflect `high`; no change is required inside the example app itself.

## Evidence

- Example app default is `high` in `Settings` dataclass and `from_env` [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L72-L72], [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L151-L151].
- Example `.env.example` sets `HY3_REASONING_EFFORT=high` [examples/hy3-repo-scout/.env.example:L7-L7].
- Example READMEs document the default as `high` [examples/hy3-repo-scout/README.md:L73-L73], [examples/hy3-repo-scout/README_CN.md:L70-L70].
- Example tests assert `high` default and validate `no_think`/`low`/`high` as allowed choices only [examples/hy3-repo-scout/tests/test_config.py:L27-L27], [examples/hy3-repo-scout/tests/test_config.py:L82-L82], [examples/hy3-repo-scout/tests/test_config.py:L91-L92], [examples/hy3-repo-scout/tests/test_client.py:L24-L28], [examples/hy3-repo-scout/tests/test_cli.py:L44-L44].
- Root `README.md` API example hardcodes `no_think` and labels it "(default, direct response)" [README.md:L135-L136], and the reasoning-mode note implies `no_think` is the default behavior [README.md:L143-L143].
- Root `README_CN.md` mirrors this [README_CN.md:L131-L132], [README_CN.md:L139-L139].
- Finetune docs state the model's native default output is slow thinking (`high`), and show `no_think` only as the "fast thinking pattern" example [finetune/README.md:L11-L11], [finetune/README.md:L17-L17], [finetune/README_CN.md:L11-L11], [finetune/README_CN.md:L17-L17].
- Finetune training script falls back to `no_think` when a data record omits `reasoning_effort` [finetune/deepspeed_support/train.py:L176-L178].
- Client maps `no_think`→OpenRouter `minimal`, otherwise passes `reasoning_effort` through (`high`/`low`) [examples/hy3-repo-scout/src/hy3_repo_scout/client.py:L42-L46].
- Validation accepts only `no_think`, `low`, `high` [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L132-L135].
- Declared test runner is `python -m unittest discover -s tests -v` plus `ruff`; `pyproject.toml` declares no test framework (only `ruff` in dev extras) [examples/hy3-repo-scout/README.md:L246-L251], [examples/hy3-repo-scout/pyproject.toml:L13-L19].

## Findings

### 1. Example application (`examples/hy3-repo-scout`) — already consistent, no change needed
**Fact:** Code, env example, docs, and tests all already use `high` as the default [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L72-L72], [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L151-L151], [examples/hy3-repo-scout/.env.example:L7-L7], [examples/hy3-repo-scout/README.md:L73-L73], [examples/hy3-repo-scout/README_CN.md:L70-L70], [examples/hy3-repo-scout/tests/test_config.py:L27-L27].
**Inference:** The requested default flip is already applied here; changing it again would be a no-op for this subtree.

### 2. Root README API examples (English + Chinese) — need sync
**Fact:** Both root READMEs embed a hardcoded `extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}` and call `no_think` the default [README.md:L135-L136], [README.md:L143-L143], [README_CN.md:L131-L132], [README_CN.md:L139-L139].
**Recommendation (unexecuted):** Update these snippets/comments to `high` (or remove the hardcoded override and note the new default) so the documented API example matches the example app's actual default.

### 3. Finetune documentation — mostly already `high`, minor wording only
**Fact:** Finetune docs describe the model's default as slow thinking (`high`) and use `no_think` solely as a labeled fast-thinking example [finetune/README.md:L11-L11], [finetune/README.md:L17-L17], [finetune/README_CN.md:L11-L11], [finetune/README_CN.md:L17-L17].
**Inference:** These docs do not need a default flip; at most, clarify that `no_think` is opt-in.

### 4. Finetune training-data fallback (`train.py`) — separate concern
**Fact:** When a training record lacks `reasoning_effort`, `train.py` defaults to `no_think` [finetune/deepspeed_support/train.py:L176-L178].
**Inference:** This is a data-processing default for tokenization, independent of the app/API default. If repo-wide consistency is desired, this could be switched to `high`, but doing so changes how missing-field training samples are tokenized.

### 5. Tests — already aligned, no update required
**Fact:** Example unit tests assert `high` as the default and treat `no_think`/`low` only as valid overrides [examples/hy3-repo-scout/tests/test_config.py:L27-L27], [examples/hy3-repo-scout/tests/test_client.py:L24-L28], [examples/hy3-repo-scout/tests/test_cli.py:L44-L44].
**Inference:** No test edits are needed for the example app; the offline suite already encodes `high`.

## Risks and Unknowns

- **Risk (latency/cost):** Switching the effective default to `high` enables deep chain-of-thought, increasing token consumption and per-request latency. The example app's `max_tokens=16384` and `timeout=90.0` [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L61-L69] may need review for long `high`-effort runs, though this is already the example app's current behavior.
- **Risk (training-data semantics):** If `train.py`'s fallback is changed from `no_think` to `high`, training samples that omit the field will be tokenized as slow-thinking, altering dataset composition [finetune/deepspeed_support/train.py:L176-L178].
- **Risk (doc/code drift):** Leaving the root README API example at `no_think` while the example app defaults to `high` creates contradictory guidance for users copying the root snippet [README.md:L135-L136], [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L72-L72].
- **Compatibility (low):** The OpenRouter mapping already handles `high` correctly (`{"reasoning": {"effort": "high"}}`) and `high` passes validation, so no code-compatibility break is expected [examples/hy3-repo-scout/src/hy3_repo_scout/client.py:L42-L46], [examples/hy3-repo-scout/src/hy3_repo_scout/config.py:L132-L135].
- **Unknown:** Whether the root `README.md` API example is intended to reflect the example app's default or the model's serving-stack default independently. The root README does not reference the example app's env var, so its `no_think` may be a deliberate serving-stack illustration rather than a repo-default statement. This intent is not documented and should be confirmed before editing.
- **Unknown:** Whether any downstream CI or deployment manifest pins `no_think` via environment; no such file appeared in the searched `reasoning_effort` matches, but deployment orchestration files outside this repository are out of scope.

## Verification Plan

All commands below are grounded in the repository's own documentation and tooling; no undeclared `pytest` is assumed.

1. **Run the declared offline unit suite** (from `examples/hy3-repo-scout`), which already asserts the `high` default:
   - `cd examples/hy3-repo-scout && python -m unittest discover -s tests -v` [examples/hy3-repo-scout/README.md:L246-L251].
2. **Run the declared linter** to confirm no syntax/style regressions from any doc or code edits:
   - `python -m pip install -e '.[dev]' && python -m ruff check src tests` [examples/hy3-repo-scout/README.md:L249-L251].
3. **Manual consistency check (textual, not a test runner):** After any edits, confirm no remaining `no_think`-as-default language in the root READMEs and (if changed) `train.py` by searching the repository for `no_think` and reviewing each hit's context. This reuses the same evidence-gathering approach as the `search_text` step already performed; it is a documentation review step, not an automated test.
4. **(Optional, requires live credentials — out of offline scope):** The live demo script `demos/run-live-demos.sh` does not set `HY3_REASONING_EFFORT`, so it inherits the env default (`high`); running it would exercise the `high` path end-to-end, but it consumes API quota and is excluded from the offline unit suite [examples/hy3-repo-scout/demos/run-live-demos.sh:L9-L14], [examples/hy3-repo-scout/README.md:L243-L245].

**Recommendation:** Execute steps 1–2 before merging any documentation sync; treat step 3 as a required human review gate. Do not modify any files as part of this investigation (read-only scope honored).

---

## Run Metadata

| Field | Value |
|---|---:|
| Repository | `Hy3-issue4` |
| Model | `tencent/hy3:free` |
| Model rounds | 8 |
| Tool calls | 23 |
| Files read | 16 |
| Repository context | 58852 chars |
| Total tokens | 132379 |
| Run status | complete |
| Budget exhausted | no |

## Citation Validation

Status: **passed**. Verified citations: **58**.
