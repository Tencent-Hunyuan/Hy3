"""Research planner: generates structured research plan via Hy3."""

from __future__ import annotations

import json
import re
from hy3research.client import call_hy3

PLAN_SYSTEM_PROMPT = """你是一个资深研究规划专家。用户会给你一个研究主题，你需要生成一份结构化的研究计划。

要求：
1. 将主题拆分为3-6个子主题
2. 为每个子主题生成一个搜索query和核心问题
3. 生成报告大纲（6-10个章节）

输出格式（严格JSON，不包含markdown代码块标记）：
{
  "title": "报告标题",
  "subtopics": [
    {"query": "搜索关键词", "key_question": "该子主题要回答的核心问题"}
  ],
  "report_outline": ["1. 引言", "2. xxx", ...]
}
"""


def _extract_json(text: str) -> str:
    """Extract JSON from text that may have markdown fences."""
    # Try to find JSON block
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try to find raw JSON object with balanced braces
    start = text.find('{')
    if start == -1:
        return text.strip()
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1].strip()
    return text.strip()


def generate_plan(topic: str, mock: bool = False) -> dict:
    """Generate research plan for a topic.

    Args:
        topic: Research topic string.
        mock: Use mock client if True.

    Returns:
        Dict with keys: title, subtopics, report_outline.
    """
    messages = [
        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
        {"role": "user", "content": f"请为以下主题生成研究计划：{topic}"},
    ]
    response = call_hy3(messages, max_tokens=4096, temperature=0.3, mock=mock)
    json_str = _extract_json(response)
    try:
        plan = json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback: return minimal valid plan
        plan = {
            "title": topic,
            "subtopics": [{"query": topic, "key_question": f"{topic}的核心问题是什么？"}],
            "report_outline": ["1. 引言", "2. 主体分析", "3. 结论"],
        }
    # Validate required fields and types
    plan.setdefault("title", topic)
    if not isinstance(plan.get("subtopics"), list):
        plan["subtopics"] = [{"query": topic, "key_question": f"{topic}的核心问题是什么？"}]
    plan.setdefault("subtopics", [{"query": topic, "key_question": topic}])
    if not isinstance(plan.get("report_outline"), list):
        plan["report_outline"] = ["1. 引言", "2. 分析", "3. 结论"]
    plan.setdefault("report_outline", ["1. 引言", "2. 分析", "3. 结论"])
    return plan
