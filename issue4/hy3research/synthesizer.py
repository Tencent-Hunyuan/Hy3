"""Synthesizer: per-subtopic source merging and synthesis via Hy3."""

from __future__ import annotations

import concurrent.futures
from hy3research.client import call_hy3

SYNTHESIZE_SYSTEM_PROMPT = """你是一个研究分析专家。用户会提供：
1. 一个子主题的核心问题
2. 一组相关的源材料（编号[1][2]...，包含标题和正文）

请基于这些源材料，用中文综合回答该核心问题。要求：
- 保留引用标注，使用 [1][2] 格式标注信息来源
- 客观、准确，不要添加材料中没有的信息
- 如果材料之间存在矛盾，请指出
- 结构化回答（可用小标题）

只需要输出综合后的回答文本，不需要JSON格式。"""


def synthesize_subtopic(
    subtopic: dict,
    sources: list[dict],
    fetched: list[dict],
    mock: bool = False,
) -> dict:
    """Synthesize materials for a single subtopic.

    Args:
        subtopic: {query, key_question} from planner.
        sources: All source metadata with indices.
        fetched: Fetched content with raw_text.
        mock: Use mock client.

    Returns:
        {subtopic, synthesized_text, cited_sources: [int]}.
    """
    # Find which sources are relevant to this subtopic's query
    query = subtopic["query"]
    query_lower = query.lower()

    # Match fetched content to sources by URL
    relevant_sources = []
    for s in sources:
        # Check if this source belongs to this query
        if s.get("query", "").lower() == query_lower or query_lower in s.get("query", "").lower():
            relevant_sources.append(s)

    if not relevant_sources:
        # If no exact match, use all sources
        relevant_sources = sources

    # Build context from fetched content
    context_parts = []
    cited_indices = []
    for s in relevant_sources:
        idx = s.get("index", 0)
        title = s.get("title", "")
        # Find matching fetched content
        matched = next(
            (f for f in fetched if f.get("index") == idx and f.get("fetch_status") == "ok"),
            None,
        )
        if matched and matched.get("raw_text"):
            text = matched["raw_text"][:2000]  # Truncate per source
            context_parts.append(f"[{idx}] {title}\n{text}")
            cited_indices.append(idx)

    if not context_parts:
        return {
            "subtopic": subtopic,
            "synthesized_text": f"## {query}\n\n该子主题暂无足够的源材料可供综合。",
            "cited_sources": [],
        }

    context = "\n\n---\n\n".join(context_parts)
    user_prompt = (
        f"核心问题：{subtopic['key_question']}\n\n"
        f"源材料：\n{context}\n\n"
        f"请基于以上源材料，综合回答核心问题。保留引用标注。"
    )

    messages = [
        {"role": "system", "content": SYNTHESIZE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    synthesized_text = call_hy3(messages, max_tokens=4096, temperature=0.3, mock=mock)

    return {
        "subtopic": subtopic,
        "synthesized_text": synthesized_text,
        "cited_sources": cited_indices,
    }


def synthesize_all(
    subtopics: list[dict],
    sources: list[dict],
    fetched: list[dict],
    mock: bool = False,
) -> list[dict]:
    """Synthesize all subtopics in parallel.

    Returns:
        List of {subtopic, synthesized_text, cited_sources}.
    """
    if mock:
        return [
            synthesize_subtopic(st, sources, fetched, mock=True)
            for st in subtopics
        ]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(
                synthesize_subtopic, st, sources, fetched, mock
            ): st
            for st in subtopics
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception:
                st = futures[future]
                results.append({
                    "subtopic": st,
                    "synthesized_text": f"## {st['query']}\n\n综合过程出错，请重试此子主题。",
                    "cited_sources": [],
                })

    # Sort by original subtopic order
    ordered = []
    for st in subtopics:
        match = next(
            (r for r in results if r["subtopic"]["query"] == st["query"]), None
        )
        if match:
            ordered.append(match)
    return ordered
