"""Search module: Tavily + DDG fallback, parallel search execution."""

from __future__ import annotations

import concurrent.futures
from hy3research.config import Config


def search_single(query: str, max_results: int = 10) -> list[dict]:
    """Search with Tavily, fallback to DDG. Returns [{title, url, snippet}]."""
    results = _search_tavily(query, max_results)
    if results is None or len(results) == 0:
        results = _search_ddg(query, max_results)
    return results


def _search_tavily(query: str, max_results: int) -> list[dict] | None:
    """Tavily search, returns None on failure."""
    api_key = Config.TAVILY_API_KEY
    if not api_key:
        return None
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results, search_depth="basic")
        items = response.get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": (r.get("content", "") or "")[:300],
            }
            for r in items[:max_results]
        ]
    except Exception:
        return None


def _search_ddg(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo search fallback. Returns empty list on failure."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": (r.get("body", "") or "")[:300],
                })
        return results
    except Exception:
        return []


def deduplicate_sources(sources: list[dict]) -> list[dict]:
    """Remove duplicate URLs, keeping first occurrence."""
    seen = set()
    unique = []
    for s in sources:
        if s["url"] not in seen:
            seen.add(s["url"])
            unique.append(s)
    return unique


def search_all(subtopics: list[dict], mock: bool = False) -> list[dict]:
    """Run parallel search for all subtopic queries, deduplicate results.

    Args:
        subtopics: List of {query, key_question} dicts from planner.
        mock: If True, return synthetic results without network calls.

    Returns:
        List of {index, url, title, snippet, query} with global dedup.
    """
    if mock:
        all_sources = _mock_search(subtopics)
    else:
        all_sources = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(search_single, st.get("query", ""), 10): st
                for st in subtopics
            }
            for future in concurrent.futures.as_completed(futures):
                st = futures[future]
                try:
                    results = future.result()
                except Exception:
                    results = []
                for r in results:
                    r = dict(r, query=st.get("query", ""))
                    all_sources.append(r)

    unique = deduplicate_sources(all_sources)
    # Cap at 40 sources
    unique = unique[:40]
    # Add global index
    for i, s in enumerate(unique):
        s["index"] = i + 1
    return unique


def _mock_search(subtopics: list[dict]) -> list[dict]:
    """Generate synthetic search results for offline demo."""
    mock_data = []
    idx = 0
    domains = [
        ("techcrunch.com", "TechCrunch"),
        ("arxiv.org", "arXiv"),
        ("wikipedia.org", "Wikipedia"),
        ("github.com", "GitHub"),
        ("medium.com", "Medium"),
        ("nature.com", "Nature"),
    ]
    for st in subtopics:
        query = st["query"]
        for j, (domain, site_name) in enumerate(domains[:3]):
            idx += 1
            mock_data.append({
                "url": f"https://{domain}/article-about-{query.replace(' ', '-')[:30]}-{j}",
                "title": f"[Mock] {query} — {site_name} 深度分析",
                "snippet": f"关于「{query}」的综合分析文章，涵盖了最新进展、核心概念和实践案例。"
                           f"这篇文章提供了该领域的全面概述，适合研究参考。",
                "query": query,
            })
    return mock_data
