"""Reporter: final long-form report generation via Hy3."""

from __future__ import annotations

from hy3research.client import call_hy3

REPORT_SYSTEM_PROMPT = """你是一个资深研究报告撰写专家。用户会提供：
1. 报告主题和标题
2. 报告大纲
3. 每个章节的综合分析材料（含引用标注 [1][2]...）
4. 引用来源列表

请基于以上材料，撰写一份完整、结构化的深度研究报告。要求：
- 使用Markdown格式
- 包含摘要、各章节正文、结论
- 保留所有引用标注 [1][2]
- 文末包含完整的参考文献列表（统一编号）
- 语言专业、客观、准确
- 总字数不少于2000字

直接输出Markdown报告全文，不需要包裹在JSON中。"""


def generate_report(
    title: str,
    outline: list[str],
    syntheses: list[dict],
    sources: list[dict],
    mock: bool = False,
) -> str:
    """Generate final research report.

    Args:
        title: Report title.
        outline: Report chapter outline from planner.
        syntheses: List of {subtopic, synthesized_text, cited_sources} from synthesizer.
        sources: All source metadata with indices.
        mock: Use mock client.

    Returns:
        Complete Markdown report string.
    """
    # Build synthesis context
    synthesis_text = "\n\n".join(
        f"### {s['subtopic']['query']}\n{s['synthesized_text']}"
        for s in syntheses
    )

    # Build reference list
    ref_lines = []
    for s in sorted(sources, key=lambda x: x.get("index", 0)):
        idx = s.get("index", 0)
        url = s.get("url", "")
        title = s.get("title", "")
        ref_lines.append(f"[{idx}] **{title}**\n    {url}")

    ref_text = "\n\n".join(ref_lines) if ref_lines else "暂无引用来源"

    outline_text = "\n".join(outline)

    user_prompt = (
        f"报告标题：{title}\n\n"
        f"报告大纲：\n{outline_text}\n\n"
        f"各章节综合材料：\n{synthesis_text}\n\n"
        f"引用来源列表：\n{ref_text}\n\n"
        f"请基于以上材料撰写完整的研究报告。"
    )

    messages = [
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    report = call_hy3(messages, max_tokens=16384, temperature=0.3, mock=mock)

    # Ensure report has reference section if missing
    if "参考" not in report:
        report += "\n\n---\n\n## 参考文献\n\n" + ref_text

    return report


def save_report(
    report_md: str,
    output_dir: str,
    title: str,
    plan: dict,
    sources: list[dict],
    report_html: str = "",
) -> str:
    """Save report and metadata to output directory.

    Args:
        report_md: Markdown report content.
        output_dir: Output directory path.
        title: Report title.
        plan: Research plan dict.
        sources: All source metadata.
        report_html: Optional HTML report content.

    Returns:
        Output directory path.
    """
    import os
    import json

    os.makedirs(output_dir, exist_ok=True)

    # Save markdown report
    md_path = os.path.join(output_dir, "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    # Save sources
    sources_path = os.path.join(output_dir, "sources.json")
    with open(sources_path, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

    # Save plan
    plan_path = os.path.join(output_dir, "research_plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    # Save HTML if provided
    if report_html:
        html_path = os.path.join(output_dir, "report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(report_html)

    return output_dir
