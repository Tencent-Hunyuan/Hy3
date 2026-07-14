"""导出服务。

- 生成 UTF-8 JSON（符合 AnalysisBundle 结构）；
- 生成结构清晰的 Markdown 报告；
- 文件名安全化，避免路径穿越；
- 不访问网络，不写入密钥。
"""

from __future__ import annotations

import os
import re
from datetime import datetime

from ..models import AnalysisBundle, CitationStatus

_DISCLAIMER = (
    "本报告由 RuleLens（规则透镜）基于 Hy3 自动生成，仅供理解参考，"
    "不构成法律、合规或专业意见。引用核验仅验证原文一致性，不保证规则解释无误。"
)


def safe_filename(name: str) -> str:
    """去除路径分隔符与不安全字符，仅保留基础文件名。"""
    base = os.path.basename(name)
    # 去掉目录、控制字符，空格替换为下划线
    cleaned = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", base, flags=re.UNICODE)
    cleaned = cleaned.strip("._")
    return cleaned or "document"


def build_export_filename(original: str, ext: str) -> str:
    """rulelens_<原文件名>_<YYYYMMDD_HHMM>.{md,json}"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    base = safe_filename(original)
    return f"rulelens_{base}_{stamp}.{ext}"


def to_json(bundle: AnalysisBundle) -> str:
    return bundle.model_dump_json(indent=2, ensure_ascii=False)


def to_markdown(bundle: AnalysisBundle) -> str:
    lines: list[str] = []
    lines.append("# RuleLens 规则分析报告")
    lines.append("")
    lines.append("> 把规则文档变成可验证的边界案例。")
    lines.append("")
    lines.append("## 元信息")
    lines.append("")
    lines.append(f"- 文档名称：{bundle.file_name}")
    lines.append(f"- 文件 SHA-256：`{bundle.file_sha256}`")
    lines.append(f"- 分析时间：{bundle.analyzed_at.isoformat()}")
    lines.append(f"- 模型名称：{bundle.model_name}")
    lines.append("")

    # 引用核验通过率
    lines.append("## 概览")
    lines.append("")
    lines.append(f"- 识别规则：{len(bundle.rule_result.rules)} 条")
    lines.append(f"- 生成情景：{len(bundle.scenario_set.scenarios)} 个")
    lines.append(f"- 潜在问题：{len(bundle.ambiguity_report.issues)} 个")
    lines.append(f"- 已答题数：{len(bundle.attempts)} 题")
    verified, total = _citation_stats(bundle)
    rate = (verified / total * 100) if total else 0.0
    lines.append(f"- 引用核验通过率：{rate:.0f}%（{verified}/{total}）")
    lines.append("")

    # 规则地图
    lines.append("## 规则地图")
    lines.append("")
    topics = _group_by_topic(bundle)
    for topic, rules in topics.items():
        lines.append(f"### {topic}")
        lines.append("")
        for rule in rules:
            lines.append(f"**{rule.rule_id} · {rule.title}** （{rule.rule_type.value}）")
            lines.append("")
            lines.append(f"- 规范化陈述：{rule.normalized_statement}")
            if rule.conditions:
                lines.append(f"- 条件：{'；'.join(rule.conditions)}")
            if rule.exceptions:
                lines.append(f"- 例外：{'；'.join(rule.exceptions)}")
            if rule.consequences:
                lines.append(f"- 后果：{'；'.join(rule.consequences)}")
            cit_text = "；".join(_citation_str(c) for c in rule.citations)
            lines.append(f"- 引用：{cit_text}")
            lines.append("")
    lines.append("")

    # 情景与裁决
    lines.append("## 情景闯关与裁决")
    lines.append("")
    attempts_by_scenario = {a.scenario_id: a for a in bundle.attempts}
    for sc in bundle.scenario_set.scenarios:
        lines.append(f"### {sc.scenario_id} · {sc.title}")
        lines.append("")
        lines.append(f"- 边界类型：{sc.boundary_type} ｜ 难度：{sc.difficulty}")
        lines.append(f"- 描述：{sc.description}")
        attempt = attempts_by_scenario.get(sc.scenario_id)
        if attempt:
            j = attempt.judgment
            mark = "✅ 回答正确" if attempt.is_correct else "❌ 回答有误"
            lines.append(f"- 你的判断：{attempt.user_verdict.value} ｜ {mark}")
            lines.append(f"- 正确结论：{j.verdict.value}")
            lines.append(f"- 判断摘要：{j.rationale_summary}")
            if j.applied_rule_ids:
                lines.append(f"- 适用规则：{', '.join(j.applied_rule_ids)}")
            if j.missing_information:
                lines.append(f"- 缺失信息：{'；'.join(j.missing_information)}")
            cit_text = "；".join(_citation_str(c) for c in j.citations)
            lines.append(f"- 原文证据：{cit_text}")
        else:
            lines.append("- （尚未作答）")
        lines.append("")

    # 歧义雷达
    lines.append("## 歧义与冲突雷达")
    lines.append("")
    if not bundle.ambiguity_report.issues:
        lines.append("未检测到明显歧义或冲突。")
    else:
        for issue in bundle.ambiguity_report.issues:
            lines.append(
                f"### {issue.issue_id} · {issue.title} （{issue.issue_type.value} / {issue.severity}）"
            )
            lines.append("")
            lines.append(f"- 说明：{issue.description}")
            lines.append(f"- 影响：{issue.impact}")
            lines.append(f"- 建议：{issue.suggestion}")
            if issue.citations:
                cit_text = "；".join(_citation_str(c) for c in issue.citations)
                lines.append(f"- 涉及来源：{cit_text}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"**免责声明**：_{_DISCLAIMER}_")
    lines.append("")
    return "\n".join(lines)


def _citation_str(c) -> str:
    status = c.status.value if c.status else "N/A"
    label = {
        "VERIFIED": "原文已核验",
        "SOURCE_ONLY": "来源存在未核验",
        "FAILED": "引用需人工复核",
    }.get(status, status)
    quote = c.evidence_quote or "（无短引文）"
    return f"[{c.source_id}｜{status}] {label}：{quote}"


def _group_by_topic(bundle: AnalysisBundle) -> dict:
    topics: dict[str, list] = {}
    for rule in bundle.rule_result.rules:
        topics.setdefault(rule.topic or "未分类", []).append(rule)
    return topics


def _citation_stats(bundle: AnalysisBundle) -> tuple[int, int]:
    verified = 0
    total = 0
    for rule in bundle.rule_result.rules:
        for c in rule.citations:
            total += 1
            if c.status == CitationStatus.VERIFIED:
                verified += 1
    for issue in bundle.ambiguity_report.issues:
        for c in issue.citations:
            total += 1
            if c.status == CitationStatus.VERIFIED:
                verified += 1
    for attempt in bundle.attempts:
        for c in attempt.judgment.citations:
            total += 1
            if c.status == CitationStatus.VERIFIED:
                verified += 1
    return verified, total
