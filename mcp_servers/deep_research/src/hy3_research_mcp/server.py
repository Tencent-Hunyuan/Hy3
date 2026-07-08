from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .config import ResearchSettings, load_default_dotenv
from .hy3_client import Hy3Client
from .research import (
    CompletionClient,
    Evidence,
    build_outline_prompt,
    build_research_prompt,
    build_summary_prompt,
    render_evidence_block,
)
from .search import SearchResult, web_search
from .web_utils import read_url_text


mcp = FastMCP("Hy3 Deep Research MCP", json_response=True)


def _research_settings() -> ResearchSettings:
    load_default_dotenv()
    return ResearchSettings.from_env()


def _client() -> CompletionClient:
    load_default_dotenv()
    return Hy3Client.from_env()


@mcp.tool()
def web_search_tool(query: str, max_results: Optional[int] = None) -> Dict[str, Any]:
    """Search the web for sources on a query and return titles, URLs, and snippets.

    Uses the configured search engine (DuckDuckGo by default, no API key required).
    When HY3_SEARCH_API_KEY and HY3_SEARCH_ENGINE=tavily|brave are set, that engine is used.

    Args:
        query: The search query.
        max_results: Optional override for the number of results (default 5).
    """
    settings = _research_settings()
    if max_results is not None and max_results > 0:
        settings = ResearchSettings(
            search_api_key=settings.search_api_key,
            search_engine=settings.search_engine,
            max_search_results=max_results,
            page_timeout=settings.page_timeout,
            max_page_chars=settings.max_page_chars,
            user_agent=settings.user_agent,
        )
    results = web_search(query, settings)
    return {
        "query": query,
        "results": [r.to_dict() for r in results],
        "count": len(results),
    }


@mcp.tool()
def read_url_tool(url: str, max_chars: Optional[int] = None) -> Dict[str, Any]:
    """Fetch a web page and return its readable plain text.

    Args:
        url: Absolute http or https URL to read.
        max_chars: Optional character budget for the returned text.
    """
    settings = _research_settings()
    text = read_url_text(url, settings, max_chars=max_chars)
    return {"url": url, "text": text, "chars": len(text)}


@mcp.tool()
def research_question(
    question: str,
    searches: str = "",
    focus: str = "",
    depth: str = "balanced",
    read_top_pages: int = 0,
) -> Dict[str, Any]:
    """Answer a research question by searching the web, reading sources, then asking Hy3 to synthesize.

    Args:
        question: The research question to answer.
        searches: Optional comma- or newline-separated sub-queries. When omitted, the question itself is used as one search.
        focus: Optional focus lens, e.g. "security", "cost", "recent changes since 2025".
        depth: Analysis depth: shallow, balanced, or deep (controls Hy3 reasoning).
        read_top_pages: Number of top URLs from searches to read into evidence (0-3 recommended).
    """
    settings = _research_settings()
    extra = {"balanced": "", "shallow": "Keep it brief.", "deep": "Be thorough and exhaustive."}
    focus_line = focus.strip()

    queries = [q.strip() for q in (searches or question).replace("\n", ",").split(",") if q.strip()]
    if not queries:
        queries = [question]

    evidence: List[Evidence] = []
    top_urls: List[str] = []
    for q in queries:
        results = web_search(q, settings)
        evidence.append(Evidence(query=q, results=results))
        for r in results:
            if r.url not in top_urls:
                top_urls.append(r.url)

    page_texts: List[Dict[str, str]] = []
    for url in top_urls[: max(0, min(read_top_pages, 3))]:
        try:
            page_texts.append({"url": url, "text": read_url_text(url, settings)})
        except RuntimeError as exc:
            page_texts.append({"url": url, "error": str(exc)})

    evidence_block = render_evidence_block(evidence)
    if page_texts:
        pages = "\n\n".join(
            f"Page {chr(ord('A') + i)} - {p['url']}:\n{(p.get('text') or p.get('error'))[:settings.max_page_chars]}"
            for i, p in enumerate(page_texts)
        )
        evidence_block += "\n\nFull page excerpts:\n" + pages

    depth_hint = extra.get(depth, "")
    prompt = build_research_prompt(
        question,
        evidence_block,
        focus=focus_line,
        depth=depth,
    ) + (f"\n\nDepth hint: {depth_hint}" if depth_hint else "")

    answer = _client().complete(prompt)
    return {
        "question": question,
        "queries": queries,
        "search_results": {e.query: [r.to_dict() for r in e.results] for e in evidence},
        "pages_read": page_texts,
        "answer": answer,
    }


@mcp.tool()
def summarize_documents(
    question: str,
    documents: List[str],
) -> Dict[str, Any]:
    """Summarize one or more pasted documents into a cited answer to a question.

    Args:
        question: The question to answer from the documents.
        documents: List of document texts (long strings). Each becomes a labeled Doc A, Doc B, ...
    """
    if not documents:
        raise ValueError("documents must contain at least one non-empty string.")
    documents_block = "\n\n".join(
        f"Doc {chr(ord('A') + i)}:\n{doc}" for i, doc in enumerate(documents) if doc
    )
    prompt = build_summary_prompt(question, documents_block)
    summary = _client().complete(prompt)
    return {
        "question": question,
        "document_count": len([d for d in documents if d]),
        "summary": summary,
    }


@mcp.tool()
def generate_research_outline(question: str, searches: str = "") -> Dict[str, Any]:
    """Generate a structured research outline (sections + purpose) for a question.

    Args:
        question: The topic or question to outline.
        searches: Optional sub-queries to ground the outline in live evidence.
    """
    settings = _research_settings()
    queries = [q.strip() for q in (searches or question).replace("\n", ",").split(",") if q.strip()] or [question]
    evidence = [Evidence(query=q, results=web_search(q, settings)) for q in queries]
    evidence_block = render_evidence_block(evidence)
    prompt = build_outline_prompt(question, evidence_block)
    outline = _client().complete(prompt)
    return {
        "question": question,
        "queries": queries,
        "search_results": {e.query: [r.to_dict() for r in e.results] for e in evidence},
        "outline": outline,
    }


def main() -> None:
    load_default_dotenv()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()