"""deep_research tool: multi-step research orchestrated by Hy3.

Pipeline:
  1. Hy3 decomposes the question into sub-queries.
  2. Each sub-query is run through `search_web`.
  3. The top sources are read in full via `fetch_url`.
  4. Hy3 (high reasoning) synthesises a report with inline [n] citations.
  5. A structured result (report + ordered citations) is returned.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..config import Config
from ..hy3_client import Hy3Client
from ..models import ResearchReport
from .fetch import fetch_url_impl
from .search import search_web_impl

# Valid reasoning_effort values for the Hy3 API.
_VALID_REASONING_EFFORTS = ("no_think", "low", "high")


def _extract_json_array(text: str) -> list[str]:
    """Best-effort extraction of a JSON string array from an LLM response."""
    if not text:
        return []
    # Strip markdown code fences if present.
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    # Find the first JSON array in the text.
    match = re.search(r"\[.*\]", candidate, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except (ValueError, TypeError):
        pass
    return []


def deep_research_impl(
    query: str,
    hy3: Hy3Client,
    config: Config,
    max_search_results: int = 5,
    max_sources_to_fetch: int | None = None,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    """Run the full deep-research pipeline. Returns a structured result dict."""
    query = (query or "").strip()
    if not query:
        return {
            "query": "",
            "sub_queries": [],
            "sources_searched": 0,
            "sources_fetched": 0,
            "report": "query must not be empty",
            "citations": [],
        }

    # Validate and normalise reasoning_effort.
    reasoning_effort = (reasoning_effort or config.research_reasoning_effort).strip().lower()
    if reasoning_effort not in _VALID_REASONING_EFFORTS:
        # Fall back to the configured default rather than passing an invalid value.
        reasoning_effort = config.research_reasoning_effort

    max_sources_to_fetch = (
        int(max_sources_to_fetch) if max_sources_to_fetch is not None else config.research_max_sources
    )

    # --- Step 1: decompose the query into sub-queries with Hy3 ---
    n = config.research_max_sub_queries
    decompose_prompt = (
        f"You are a research planning assistant. Break the following research question "
        f"into up to {n} specific, diverse web search queries that together would gather "
        f"comprehensive information. Return ONLY a JSON array of query strings, nothing else.\n\n"
        f"Research question: {query}"
    )
    try:
        raw = hy3.chat(
            messages=[{"role": "user", "content": decompose_prompt}],
            reasoning_effort="low",
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "query": query,
            "sub_queries": [],
            "sources_searched": 0,
            "sources_fetched": 0,
            "report": f"Failed to decompose query with Hy3: {exc}",
            "citations": [],
        }

    sub_queries = _extract_json_array(raw)
    if not sub_queries:
        sub_queries = [query]  # fall back to the original query itself

    # --- Step 2: search the web for each sub-query (dedupe by URL) ---
    seen_urls: set[str] = set()
    gathered: list[dict[str, Any]] = []
    for sq in sub_queries:
        for r in search_web_impl(sq, max_search_results, config):
            url = r.get("url") or ""
            if r.get("error") or not url or url in seen_urls:
                continue
            seen_urls.add(url)
            gathered.append(r)

    # --- Step 3: fetch full content from the top sources ---
    fetched: list[dict[str, Any]] = []
    for r in gathered[:max_sources_to_fetch]:
        result = fetch_url_impl(r["url"], config.fetch_max_chars, config)
        if result.get("success"):
            fetched.append(result)

    if not fetched:
        # Still produce a report from snippets if no page could be fetched.
        context = "\n\n".join(
            f"[{i + 1}] {r.get('title', '')}\nURL: {r.get('url', '')}\n{r.get('snippet', '')}"
            for i, r in enumerate(gathered[: max_sources_to_fetch * 2])
        ) or "No sources were found."
        citations = [
            {"index": i + 1, "title": r.get("title", ""), "url": r.get("url", "")}
            for i, r in enumerate(gathered[: max_sources_to_fetch * 2])
        ]
    else:
        context = "\n\n---\n\n".join(
            f"[Source {i + 1}] Title: {c.get('title', '')}\nURL: {c.get('url', '')}\nContent: {c.get('content', '')}"
            for i, c in enumerate(fetched)
        )
        citations = [
            {"index": i + 1, "title": c.get("title", ""), "url": c.get("url", "")}
            for i, c in enumerate(fetched)
        ]

    # --- Step 4: synthesise a report with Hy3 high reasoning ---
    synthesis_prompt = (
        "You are a deep research assistant. Using ONLY the web sources below, write a "
        "comprehensive research report answering the user's question.\n\n"
        "Rules:\n"
        "- Cite specific claims with inline references like [1], [2] matching the source numbers.\n"
        "- Start with a concise summary, then a detailed analysis.\n"
        "- Be factual; do not invent facts not supported by the sources.\n"
        "- If the sources are insufficient to fully answer, say so explicitly.\n\n"
        f"Question: {query}\n\nSources:\n{context}"
    )
    try:
        report = hy3.chat(
            messages=[{"role": "user", "content": synthesis_prompt}],
            reasoning_effort=reasoning_effort,
        )
    except Exception as exc:  # noqa: BLE001
        report = f"Failed to synthesise report with Hy3: {exc}"

    return {
        "query": query,
        "sub_queries": sub_queries,
        "sources_searched": len(gathered),
        "sources_fetched": len(fetched),
        "report": report,
        "citations": citations,
    }


def register_research_tools(mcp, config: Config, hy3: Hy3Client) -> None:
    """Register the `deep_research` MCP tool."""

    @mcp.tool()
    def deep_research(
        query: str,
        max_search_results: int = 5,
        max_sources_to_fetch: int = 3,
        reasoning_effort: str = "high",
    ) -> ResearchReport:
        """Conduct deep research on a topic and produce a cited report.

        This orchestrates a multi-step workflow powered by Tencent Hy3:
          1. Hy3 decomposes the question into focused sub-queries.
          2. Each sub-query is searched on the web (search_web).
          3. The most relevant sources are read in full (fetch_url).
          4. Hy3 with high reasoning synthesises a report with inline [n] citations.

        Args:
            query: The research question or topic to investigate.
            max_search_results: Max web results per sub-query (default 5).
            max_sources_to_fetch: Max URLs to read in full (default 3).
            reasoning_effort: Hy3 reasoning depth: "no_think", "low" or "high" (default "high").

        Returns:
            An object with: query, sub_queries, sources_searched, sources_fetched,
            report (markdown with [n] citations), and citations (list of {index,title,url}).
        """
        return deep_research_impl(  # type: ignore[return-value]
            query=query,
            hy3=hy3,
            config=config,
            max_search_results=max_search_results,
            max_sources_to_fetch=max_sources_to_fetch,
            reasoning_effort=reasoning_effort,
        )
