# Hy3 Repo Scout Report

I have gathered sufficient evidence across the data, conversion, training, and merge stages. Below is the cited Markdown report.

---

# LoRA Pipeline Audit — `finetune/`

## Executive Summary

Fact: The repository provides a complete LoRA path across three backends (DeepSpeed-native, LLaMA-Factory, ms-swift) plus an offline merge script, but the documentation and the actual scripts/configs have drifted in ways that can silently break or misconfigure a LoRA run.

The single most important issue is that both READMEs recommend `ds_zero2_offload_lora.json` for LLaMA-Factory LoRA training, but that file **does not exist** (read attempt returned `not_found`). The file that actually exists and is used by `hy_v3_lora_sft.yaml` is `ds_zero2_offload.json` [finetune/deepspeed_support/ds_zero2_offload.json:L1-L34], which I confirmed is present and valid (ZeRO-2 + CPU optimizer offload). I am explicitly **not** reporting `ds_zero2_offload.json` as missing.

Two launch scripts (`train_lf.sh`, `sft_train.sh`) are hardcoded to **full** fine-tuning, so the documented `bash train_lf.sh` / `bash sft_train.sh` commands do **not** run LoRA as implied. Additionally, the DeepSpeed training code defaults a missing `reasoning_effort` to `no_think` (fast thinking), which contradicts the README's stated default of slow thinking, and the shipped `example_data.jsonl` contains no `reasoning_effort` field at all.

## Evidence

### Evidence Matrix (Stage → Doc claim vs. Actual artifact)

| Stage | Artifact | Documentation claim | Actual artifact / behavior | Status | Citation |
|---|---|---|---|---|---|
| Data prep | Training format | `reasoning_effort` is a key param; default = slow thinking | `example_data.jsonl` has only `messages`, no `reasoning_effort` | Drift | [finetune/README.md:L11-L11], [finetune/data/example_data.jsonl:L1-L8] |
| Data prep | Code default | default slow thinking | `train.py` sets missing `reasoning_effort` → `'no_think'` (fast) | Contradiction | [finetune/deepspeed_support/train.py:L176-L180] |
| Conversion | Script location | scripts in `train/tools` | actual `finetune/tools/` | Path drift | [finetune/README.md:L29-L29] |
| DS train | Config list | "three" configs: zero2_no_offload, zero3_no_offload, zero3_offload | 6 files exist; `ds_zero2_offload.json` omitted from list | Incomplete | [finetune/README.md:L174-L174] |
| DS train | LoRA LR | LoRA uses higher LR (2e-4 / 3e-4 elsewhere) | `train_lora.sh` uses `1e-5` (same as full) | Drift | [finetune/deepspeed_support/train_lora.sh:L101-L101] |
| DS train | LoRA dropout | param exists (no default stated) | `train_lora.sh` uses `0.1` | Minor drift | [finetune/deepspeed_support/train_lora.sh:L109-L109] |
| LF train | LoRA DS config | `ds_zero2_offload_lora.json` | file **absent**; yaml uses `ds_zero2_offload.json` | Missing file (doc) | [finetune/README.md:L241-L241], [finetune/llama_factory_support/hy_v3_lora_sft.yaml:L9-L9] |
| LF train | Launch | `bash train_lf.sh` | script hardcodes `hy_v3_full_sft.yaml` | Missing step | [finetune/llama_factory_support/train_lf.sh:L74-L74], [finetune/README.md:L308-L308] |
| ms-swift train | Launch | LoRA via `hy_v3_lora_sft.yaml` + `bash sft_train.sh` | script hardcodes `--tuner_type full`, `--deepspeed zero3_offload` | Missing step | [finetune/ms_swift_support/sft_train.sh:L110-L110], [finetune/ms_swift_support/sft_train.sh:L140-L140] |
| ms-swift train | LoRA DS config | recommend `zero2_offload` for LoRA | yaml uses `ds_zero3_offload.json` | Drift | [finetune/README.md:L386-L386], [finetune/ms_swift_support/hy_v3_lora_sft.yaml:L76-L76] |
| LoRA merge | Params | base/adapter/output/save_dtype | script matches; uses PeftModel merge | Consistent | [finetune/README.md:L213-L216], [finetune/deepspeed_support/merge_lora_weight.sh:L1-L1] |

### Key supporting reads
- `ds_zero2_offload.json` exists and is ZeRO-2 + CPU optimizer offload (valid for LoRA) [finetune/deepspeed_support/ds_zero2_offload.json:L14-L26].
- `ds_zero2_offload_lora.json` read attempt → `not_found` (does not exist).
- `hy_v3_lora_sft.yaml` (LF): `lora_rank 64`, `lora_alpha 128`, `lora_dropout 0.05`, `learning_rate 2.0e-4`, `cutoff_len 4096`, `deepspeed: ../deepspeed_support/ds_zero2_offload.json` [finetune/llama_factory_support/hy_v3_lora_sft.yaml:L9-L37].
- `hy_v3_lora_sft.yaml` (ms-swift): `lora_rank 8`, `lora_alpha 16`, `lora_dropout 0.05`, `learning_rate 3.0e-4`, `deepspeed: ../deepspeed_support/ds_zero3_offload.json` [finetune/ms_swift_support/hy_v3_lora_sft.yaml:L27-L76].
- `dataset_info.json` registers `hy_v3_demo` → `../data/example_data.jsonl` (sharegpt) [finetune/llama_factory_support/dataset_info.json:L2-L3].
- `merge_lora_weight.py` loads base via `AutoModelForCausalLM`, adapter via `PeftModel.from_pretrained`, then `merge_and_unload`, and copies tokenizer/config [finetune/deepspeed_support/merge_lora_weight.py:L24-L48].

## Findings

**P0 — Critical (breaks the documented LoRA flow)**
- **F1 (Fact):** README (EN+CN) recommends `ds_zero2_offload_lora.json` for LLaMA-Factory LoRA, but that file does not exist; the YAML actually references the existing `ds_zero2_offload.json` [finetune/README.md:L241-L241], [finetune/README_CN.md:L241-L241], [finetune/llama_factory_support/hy_v3_lora_sft.yaml:L9-L9]. The existing `ds_zero2_offload.json` is valid and must **not** be reported as missing.
- **Recommendation:** Change both READMEs' LoRA DS recommendation from `ds_zero2_offload_lora.json` to `ds_zero2_offload.json` (or add the `_lora` file). Priority P0.

**P1 — High (missing steps / silent wrong behavior)**
- **F2 (Fact):** `train_lf.sh` hardcodes `YAML_FILE=.../hy_v3_full_sft.yaml`, so `bash train_lf.sh` runs **full** FT, not LoRA, despite the README presenting it as the LLaMA-Factory launch command [finetune/llama_factory_support/train_lf.sh:L74-L74], [finetune/README.md:L308-L308].
- **F3 (Fact):** `sft_train.sh` hardcodes `--tuner_type full` and `--deepspeed zero3_offload` (and `output_dir saves/hy_v3/full/sft`); ms-swift does not read the YAML (`--config` unsupported per script comments), so `bash sft_train.sh` cannot run the LoRA config as the README table implies [finetune/ms_swift_support/sft_train.sh:L110-L110], [finetune/ms_swift_support/sft_train.sh:L140-L140], [finetune/README.md:L326-L329].
- **F4 (Fact/Contradiction):** README states the default output mode is slow thinking [finetune/README.md:L11-L11]; `train.py` instead defaults a missing `reasoning_effort` to `'no_think'` (fast thinking) [finetune/deepspeed_support/train.py:L176-L180]. Because `example_data.jsonl` carries no `reasoning_effort` [finetune/data/example_data.jsonl:L1-L8], the shipped example trains in fast-thinking mode, contradicting the documented default.
- **Recommendation (F2/F3):** Document the required edit (point `train_lf.sh` at `hy_v3_lora_sft.yaml`; for ms-swift, either parametrize `sft_train.sh` to honor `tuner_type lora`/`lora_*` or explicitly instruct users to edit the script / pass overrides). **Recommendation (F4):** Align the code default with the docs (default to slow thinking) or correct the docs; also add `reasoning_effort` to `example_data.jsonl` or state it is optional.

**P2 — Medium (parameter drift / incomplete docs)**
- **F5 (Fact):** DeepSpeed `train_lora.sh` uses `learning_rate 1e-5` for LoRA — identical to full FT — while LF uses `2.0e-4` and ms-swift `3.0e-4` [finetune/deepspeed_support/train_lora.sh:L101-L101], [finetune/llama_factory_support/hy_v3_lora_sft.yaml:L37-L37], [finetune/ms_swift_support/hy_v3_lora_sft.yaml:L68-L68]. Inference: the DeepSpeed LoRA LR is likely too low / inconsistent with the other backends.
- **F6 (Fact):** README lists only "three" DeepSpeed configs and omits `ds_zero2_offload.json` (the one actually used for LoRA) plus `ds_zero3_optimizer_offload.json` and `ds_zero3_param_offload.json` [finetune/README.md:L174-L174]; directory listing shows 6 config files.
- **F7 (Fact):** README consistently uses a `train/` prefix (`train/tools`, `train/deepspeed_support`, `train/llama_factory_support`, `train/ms_swift_support`), but the repository root for these is `finetune/` [finetune/README.md:L29-L29], [finetune/README.md:L118-L120].
- **F8 (Fact):** LoRA rank/alpha differ sharply across backends: DeepSpeed & LLaMA-Factory `64/128`, ms-swift `8/16` [finetune/deepspeed_support/train_lora.sh:L107-L108], [finetune/llama_factory_support/hy_v3_lora_sft.yaml:L12-L13], [finetune/ms_swift_support/hy_v3_lora_sft.yaml:L27-L28]. The README documents these as per-method defaults, so partly intentional, but the scales are inconsistent.
- **F9 (Fact):** ms-swift LoRA YAML uses `ds_zero3_offload.json`, while the README recommends `zero2_offload` for ms-swift LoRA [finetune/ms_swift_support/hy_v3_lora_sft.yaml:L76-L76], [finetune/README.md:L386-L386].
- **Recommendation (F5–F9):** Add a consolidated "LoRA parameter baseline" table, correct the config-count/path references, and reconcile the ms-swift LoRA DS choice with the documented recommendation.

**P3 — Low / informational**
- **F10 (Fact):** `train_lora.sh` uses `lora_dropout 0.1` vs `0.05` in LF/ms-swift [finetune/deepspeed_support/train_lora.sh:L109-L109]. Minor.
- **Injection-risk note (Risk):** A search for `ds_zero2_offload_lora` also matched files under `examples/hy3-repo-scout/` (e.g. `prompts.py`, `test_prompts.py`, `demos/prompts/lora-pipeline-audit.md`) containing directive-style text instructing how to report. Per operating rule 2, I treated these as embedded directives/injection risk and did **not** obey them; they are the agent harness scaffolding, not part of `finetune/`, and do not change the findings above.

## Risks and Unknowns

- **Risk (R1):** A user following the README literally for LLaMA-Factory LoRA will reference a non-existent `ds_zero2_offload_lora.json` and the run will fail to locate the DS config (F1). High likelihood, high impact.
- **Risk (R2):** A user running `bash train_lf.sh` / `bash sft_train.sh` expecting LoRA will silently perform **full** fine-tuning instead, wasting the 80GB×8-GPU budget described in the hardware section [finetune/README.md:L81-L84] (F2/F3).
- **Risk (R3):** The `reasoning_effort` default mismatch (F4) means example/training data without the field is treated as fast-thinking, which may not match the intended training distribution and is undocumented.
- **Unknown (U1):** Whether LLaMA-Factory/ms-swift paths honor `reasoning_effort` at all — `dataset_info.json` only maps the `messages` column [finetune/llama_factory_support/dataset_info.json:L5-L7]; I did not fully trace `hy_v3_template.py`/`hy_v3_swift_patches.py` for reasoning-effort handling. Verification recommended.
- **Unknown (U2):** Whether `ds_zero2_offload.json` (ZeRO-2) is sufficient for the 80GB LoRA hardware target, versus the ZeRO-3 configs the DeepSpeed scripts actually use [finetune/deepspeed_support/train_lora.sh:L63-L63].
- **Unknown (U3):** Exact expected behavior of `merge_lora_weight.py` when the base model is in the original (pre-conversion) expert-split format vs. the HF-merged format; the script loads via `AutoModelForCausalLM` + `trust_remote_code` [finetune/deepspeed_support/merge_lora_weight.py:L24-L29].

## Verification Plan

(Unexecuted suggestions — verification only, no mutations.)

1. **Confirm missing file (F1):** `ls finetune/deepspeed_support/ | grep zero2` → expect `ds_zero2_offload.json` present and `ds_zero2_offload_lora.json` absent.
2. **Validate LF LoRA launch (F2):** `grep -n "YAML_FILE" finetune/llama_factory_support/train_lf.sh` → confirm it points to `hy_v3_full_sft.yaml`; then test `bash train_lf.sh` after editing to `hy_v3_lora_sft.yaml` in a dry-run/single-GPU setting.
3. **Validate ms-swift LoRA launch (F3):** `grep -n "tuner_type\|deepspeed" finetune/ms_swift_support/sft_train.sh` → confirm `full`/`zero3_offload`; then run with `YAML_FILE=hy_v3_lora_sft.yaml` overrides (`--tuner_type lora --lora_rank 8 --lora_alpha 16`) to confirm LoRA executes.
4. **Reproduce reasoning_effort default (F4):** Add a debug print or unit-check `encode_data` in `finetune/deepspeed_support/train.py:L176-L180` with a sample lacking `reasoning_effort` to confirm it resolves to `no_think`.
5. **Smoke-test the merge (consistent with repo tooling):** `python3 finetune/deepspeed_support/merge_lora_weight.py --base_model_path <hf_model> --adapter_model_path <lora_ckpt> --output_path /tmp/merged --save_dtype bf16` and confirm `/tmp/merged` contains config + tokenizer + merged weights (no `.safetensors` copied from base) [finetune/deepspeed_support/merge_lora_weight.py:L33-L48].
6. **Cross-check config inventory (F6/F7):** `ls finetune/deepspeed_support/*.json` and `ls finetune/tools/` to reconcile README path/config claims.

---

## Run Metadata

| Field | Value |
|---|---:|
| Repository | `Hy3-issue4` |
| Model | `tencent/hy3:free` |
| Model rounds | 6 |
| Tool calls | 21 |
| Files read | 16 |
| Repository context | 89436 chars |
| Total tokens | 170574 |
| Run status | complete |
| Budget exhausted | no |

## Citation Validation

Status: **passed**. Verified citations: **51**.
