from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol

from .search import SearchResult


class CompletionClient(Protocol):
    def complete(
        self,
        prompt: str,
        *,
        system: str = ...,
        prior_turns: Optional[Iterable[Dict[str, str]]] = None,
    ) -> str: ...


@dataclass(frozen=True)
class Evidence:
    """One piece of sourced evidence gathered for a research question."""

    query: str
    results: List[SearchResult]

    def render(self) -> str:
        if not self.results:
            return f"Search '{self.query}' returned no usable results."
        lines = [f"Search: {self.query}"]
        for i, r in enumerate(self.results, 1):
            lines.append(f"[{i}] {r.title}\n    URL: {r.url}")
            if r.snippet:
                lines.append(f"    {r.snippet}")
        return "\n".join(lines)


def render_evidence_block(evidence: Iterable[Evidence]) -> str:
    blocks = [e.render() for e in evidence]
    return "\n\n".join(blocks) if blocks else "No evidence was gathered."


def build_research_prompt(
    question: str,
    evidence_block: str,
    *,
    focus: str = "",
    depth: str = "balanced",
) -> str:
    focus_line = f"Focus: {focus}.\n" if focus else ""
    return f"""Research question: {question}

{focus_line}Depth: {depth}. Use the search evidence below as primary grounding.
If evidence is missing or conflicts, state that explicitly instead of inventing facts.
Cite sources by their [N] index and URL when making claims.

Return concise markdown:
1. Answer - the direct answer to the question
2. Key findings - bullet list, each with a citation
3. Confidence - high/medium/low and a one-line reason
4. Gaps - what is still unknown or where evidence is weak

Evidence:
{evidence_block}
"""


def build_outline_prompt(question: str, evidence_block: str) -> str:
    return f"""A researcher is investigating: {question}

Below is raw search evidence. Produce a short research outline (markdown headings)
that would organize a report answering the question. List 3 to 6 sections with a
one-sentence purpose each. Do not write the full report.

Evidence:
{evidence_block}
"""


def build_summary_prompt(question: str, documents_block: str) -> str:
    return f"""Summarize the documents below into a faithful, structured answer for this question:

Question: {question}

Rules:
- Only use information present in the documents.
- Quote or paraphrase with a document label (Doc A, Doc B, ...).
- If the documents do not contain the answer, say so plainly.

Documents:
{documents_block}
"""