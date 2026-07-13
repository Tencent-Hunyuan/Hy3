# Demo 2: LoRA pipeline consistency audit

[Back to Hy3 Repo Scout](../../README.md) | [中文说明](../../README_CN.md)

This demo asks Hy3 to reconstruct the LoRA lifecycle across prose, Shell, YAML, and Python,
then look for drift between those sources. It is designed to demonstrate long-context planning,
targeted reads, cross-format evidence synthesis, and locally validated citations.

## Built-in prompt

The `--demo pipeline` option uses this prompt:

```text
从 finetune/ 下的中英文 README、Shell、YAML 与 Python 文件还原 LoRA 从数据准备、训练到
权重合并的完整流程，并检查文档、脚本和配置之间是否存在参数漂移或缺失步骤。输出证据矩阵
和优先级明确的修复建议。必须实际读取 finetune/README.md、finetune/README_CN.md、
finetune/data/example_data.jsonl 和 finetune/deepspeed_support/ds_zero2_offload.json；区分
该现有文件与文档引用的 ds_zero2_offload_lora.json，不得把存在的文件误报为缺失。
不要修改任何文件。
```

## Run

Prepare the environment as described in the main README, then run from
`examples/hy3-repo-scout`:

```bash
hy3-repo-scout --repo ../.. --demo pipeline \
  --output demos/artifacts/lora-pipeline-audit.md
```

The same flow is available in the REPL:

```text
/demo pipeline
```

## Review criteria

A successful recording should show all of the following without pre-writing the audit result:

- Hy3 makes live Chat Completions requests and investigates multiple files below `finetune/`
  with the local read-only tools.
- The report reconstructs data preparation, training, and weight merging, while explicitly
  marking any evidence gap as unknown.
- The final report contains `Executive Summary`, `Evidence`, `Findings`,
  `Risks and Unknowns`, and `Verification Plan`, in that order.
- Repository-specific claims use canonical `file:line` citations and local citation validation
  passes.
- Any evidence matrix or prioritized recommendation is grounded in cited README, Shell, YAML,
  or Python content rather than a canned expected answer.
- The target repository is not modified. Only the explicitly requested report path may be
  written.

Exit status `0` is part of the acceptance check: it requires finish reason `stop`, an
unexhausted run budget, and successful local citation validation. Citation validation checks
location and bounds, not the semantic quality of the audit, so human review remains necessary.

## Artifact status

- Live report: [lora-pipeline-audit.md](../artifacts/lora-pipeline-audit.md).
- Combined 37.98-second terminal recording:
  [hy3-repo-scout-live-demos.gif](../media/hy3-repo-scout-live-demos.gif).
- Provider, model, timestamps, non-secret settings, outcomes, and hashes:
  [live run notes](../artifacts/RUN.md).
- Recorded outcome: exit `0`, finish reason `stop`, no exhausted budget, 51 verified citations.
