# Demo 1: Reasoning-mode change impact

[Back to Hy3 Repo Scout](../../README.md) | [中文说明](../../README_CN.md)

This demo asks Hy3 to trace a cross-cutting default change through the English and Chinese
documentation, API examples, deployment guidance, and tests. It is designed to demonstrate
multi-file investigation, tool selection, evidence gathering, and locally validated citations.

## Built-in prompt

The `--demo impact` option uses this prompt:

```text
调查：如果把仓库示例中的默认 reasoning_effort 从 no_think 改为 high，哪些中英文文档、
API 示例、部署说明和测试需要同步？请给出影响清单、兼容性风险和可执行的验证计划。
验证命令必须与仓库现有 README、pyproject 和测试运行器一致，不要假设未声明的 pytest。
不要修改任何文件。
```

## Run

Prepare the environment as described in the main README, then run from
`examples/hy3-repo-scout`:

```bash
hy3-repo-scout --repo ../.. --demo impact \
  --output demos/artifacts/change-impact.md
```

The same flow is available in the REPL:

```text
/demo impact
```

## Review criteria

A successful recording should show all of the following without assuming a particular model
answer in advance:

- Hy3 makes live Chat Completions requests and selects one or more read-only repository tools.
- The final report contains `Executive Summary`, `Evidence`, `Findings`,
  `Risks and Unknowns`, and `Verification Plan`, in that order.
- Repository-specific claims use canonical citations such as
  `[README.md:L128-L136]`, and local citation validation passes.
- The analysis considers both language variants and distinguishes facts, inferences, risks,
  and recommendations.
- The target repository is not modified. Only the explicitly requested report path may be
  written.

Exit status `0` is part of the acceptance check: it requires finish reason `stop`, an
unexhausted run budget, and successful local citation validation. Human review is still
required to judge whether each citation actually supports its claim.

## Artifact status

- Live report: [change-impact.md](../artifacts/change-impact.md).
- Combined 37.98-second terminal recording:
  [hy3-repo-scout-live-demos.gif](../media/hy3-repo-scout-live-demos.gif).
- Provider, model, timestamps, non-secret settings, outcomes, and hashes:
  [live run notes](../artifacts/RUN.md).
- Recorded outcome: exit `0`, finish reason `stop`, no exhausted budget, 58 verified citations.
