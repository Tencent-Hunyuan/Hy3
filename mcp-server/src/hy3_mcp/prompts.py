# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Prompt builders for every LLM-backed tool.

Each builder returns ``(system, user)``.  The user message always carries
the deterministic evidence (diff text, retrieved chunks, data profile,
sources) in a stable machine-readable layout — the same layout the offline
fake backend parses, and a clear grounding format for the real Hy3 model.
:meth:`hy3_mcp.hy3_client.Hy3Client.chat` prepends the ``[hy3-mcp task=...]``
routing marker to the system prompt.
"""

from __future__ import annotations

import json
from typing import Sequence

from .schemas import DiffStats, Evidence, TableProfile
from .sources.files import ScoredChunk

__all__ = [
    "review_prompts",
    "docs_prompts",
    "data_prompts",
    "research_prompts",
]

_LANG_RULE = (
    "Answer in the same language as the user's request (中文提问用中文回答); "
    "be concise, concrete and honest — never invent facts beyond the provided material."
)


def review_prompts(diff_text: str, stats: DiffStats, focus: str) -> tuple[str, str]:
    """Build prompts for review_code."""
    system = (
        "你是资深代码评审专家，请基于给出的 unified diff 输出结构化评审意见"
        "（按严重程度排序，引用具体行）。 "
        "You are a senior code reviewer: produce a structured review of the "
        f"given change, ordered by severity, citing concrete lines. Focus: {focus}. "
        + _LANG_RULE
    )
    user = (
        f"Review focus: {focus}\n"
        f"Deterministic pre-analysis: files={stats.files}, hunks={stats.hunks}, "
        f"+{stats.added_lines}/-{stats.removed_lines} lines\n\n"
        "=== BEGIN DIFF ===\n"
        f"{diff_text}\n"
        "=== END DIFF ==="
    )
    return system, user


def docs_prompts(question: str, ranked: Sequence[ScoredChunk]) -> tuple[str, str]:
    """Build prompts for ask_docs; evidence chunks use the [chunk N | ref] layout."""
    system = (
        "你是知识库问答助手，只能依据提供的文档片段作答，并给出 (file#chunk) 引用；"
        "片段中没有的信息必须明说不知道。 "
        "You answer strictly from the provided document chunks, cite them as "
        "(file#chunk), and explicitly say so when the chunks do not contain the answer. "
        + _LANG_RULE
    )
    blocks = [
        f"[chunk {i + 1} | {sc.chunk.source}#{sc.chunk.chunk_id}]\n{sc.chunk.text}"
        for i, sc in enumerate(ranked)
    ]
    user = f"Question: {question}\n\nRetrieved chunks:\n\n" + "\n\n".join(blocks)
    return system, user


def data_prompts(question: str, profile: TableProfile) -> tuple[str, str]:
    """Build prompts for analyze_data; the profile travels as a JSON block."""
    system = (
        "你是数据分析师，请基于给出的确定性数据画像（PROFILE JSON）撰写分析叙事"
        "并建议合适的图表；不要编造画像之外的数字。 "
        "You are a data analyst: narrate insights and chart suggestions based "
        "strictly on the deterministic PROFILE JSON; never invent numbers. "
        + _LANG_RULE
    )
    user = (
        f"Analysis question: {question or '(general overview)'}\n\n"
        "PROFILE JSON:\n```json\n"
        f"{json.dumps(profile.model_dump(), ensure_ascii=False, indent=2)}\n"
        "```"
    )
    return system, user


def research_prompts(topic: str, evidence: Sequence[Evidence]) -> tuple[str, str]:
    """Build prompts for deep_research; sources use the [source N | ref] layout."""
    system = (
        "你是深度研究助手，请综合给出的多个来源，产出带编号引用的研究结论"
        "（每条结论标注支撑来源，冲突处如实指出）。 "
        "You are a deep-research assistant: synthesize the numbered sources into "
        "cited conclusions, flagging conflicts honestly. " + _LANG_RULE
    )
    blocks = [
        f"[source {i + 1} | {ev.kind}:{ev.ref}]\n{ev.snippet}"
        for i, ev in enumerate(evidence)
    ]
    user = f"Research topic: {topic}\n\nSources:\n\n" + "\n\n".join(blocks)
    return system, user
