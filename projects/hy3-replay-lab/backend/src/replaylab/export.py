# ruff: noqa: RUF001
from __future__ import annotations

import json

from replaylab.schemas import ReplayReport

_COVERAGE_LABELS = {
    "covered": "已通过",
    "violated": "未满足",
    "unknown": "待确认",
}
_STEP_KIND_LABELS = {
    "observation": "观察",
    "decision": "决策",
    "tool_call": "工具调用",
    "tool_result": "工具结果",
    "action": "操作",
    "validation": "验证",
    "claim": "结论",
}
_STEP_STATUS_LABELS = {
    "ok": "正常",
    "warning": "警告",
    "failed": "失败",
    "unknown": "未知",
}
_SEVERITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "critical": "严重",
}
_CATEGORY_LABELS = {
    "constraint_omission": "约束遗漏",
    "repeated_loop": "重复循环",
    "tool_misuse": "工具误用",
    "evidence_gap": "证据缺口",
    "citation_error": "引用错误",
    "unsafe_action": "不安全操作",
    "resource_limit": "资源限制",
    "no_divergence": "未发现偏航",
    "other": "其他",
}


def export_report_json(report: ReplayReport) -> str:
    return (
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def export_report_markdown(report: ReplayReport) -> str:
    finding = report.finding
    replay = report.replay_plan
    lines = [
        f"# 轨迹复盘报告：{report.task.title}",
        "",
        f"- 报告编号：`{report.report_id}`",
        f"- 分析提供方：`{report.metadata.provider}` / `{report.metadata.model}`",
        f"- 首个偏航点：`{finding.first_divergence_step_id or '无'}`",
        "",
        "## 任务",
        "",
        report.task.description,
        "",
        "## 验收覆盖",
        "",
        "| 验收条件 | 状态 | 步骤 | 证据 | 说明 |",
        "|---|---|---|---|---|",
    ]
    for item in report.coverage:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item.criterion_id}`",
                    _COVERAGE_LABELS[item.status],
                    _ids(item.supporting_step_ids),
                    _ids(item.evidence_ids),
                    _escape_cell(item.explanation),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 标准化时间线",
            "",
            "| 序号 | 步骤 | 类型 | 状态 | 摘要 | 证据 |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for step in report.timeline:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(step.sequence),
                    f"`{step.step_id}`",
                    _STEP_KIND_LABELS[step.kind],
                    _STEP_STATUS_LABELS[step.status],
                    _escape_cell(step.summary),
                    _ids(step.evidence_ids),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 偏航结论",
            "",
            f"- 风险等级：**{_SEVERITY_LABELS[finding.severity]}**",
            f"- 类型：`{_CATEGORY_LABELS.get(finding.category, finding.category)}`",
            f"- 首个偏航步骤：`{finding.first_divergence_step_id or '无'}`",
            f"- 影响步骤：{_ids(finding.impact_step_ids)}",
            f"- 关联证据：{_ids(finding.evidence_ids)}",
            "",
            finding.explanation,
        ]
    )
    if finding.hypotheses:
        lines.extend(["", "仍需证据验证的假设："])
        lines.extend(f"- {item}" for item in finding.hypotheses)

    lines.extend(
        [
            "",
            "## 最小重放计划",
            "",
            f"- 保留步骤：{_ids(replay.preserved_step_ids)}",
            f"- 重放起点：`{replay.rerun_from_step_id or '无'}`",
            f"- 替换步骤：{_ids(replay.rerun_step_ids)}",
            "",
            "### 有序操作",
            "",
        ]
    )
    for action in replay.actions:
        lines.extend(
            [
                f"{action.order}. {action.action}",
                f"   - 证据：{_ids(action.evidence_ids)}",
                f"   - 验证闸门：{action.validation_gate.description}",
                f"   - 闸门条件：{_ids(action.validation_gate.criterion_ids)}",
                f"   - 闸门证据：{_ids(action.validation_gate.evidence_ids)}",
            ]
        )

    lines.extend(["", "### 停止条件", ""])
    for gate in replay.stop_conditions:
        lines.append(
            f"- {gate.description} 条件：{_ids(gate.criterion_ids)}；"
            f"证据：{_ids(gate.evidence_ids)}"
        )

    lines.extend(["", "### 禁止操作", ""])
    for item in replay.prohibited_actions:
        lines.append(
            f"- **禁止：** {item.action} 原因：{item.reason} 证据：{_ids(item.evidence_ids)}"
        )

    lines.extend(["", "## 证据目录", ""])
    for item in report.evidence:
        lines.extend(
            [
                f"### `{item.evidence_id}` — {item.source_label}",
                "",
                f"关联步骤：`{item.step_id}` · 类型：`{item.kind}`",
                "",
                item.content,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _ids(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) or "无"


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
