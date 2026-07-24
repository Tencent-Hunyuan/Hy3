"""search_web tool: web search via DuckDuckGo (no key) or Tavily (optional key)."""

from __future__ import annotations

import time
from typing import Any

from ..config import Config
from ..models import SearchResult


def _search_ddg(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search with DuckDuckGo. Requires no API key."""
    from duckduckgo_search import DDGS

    results: list[dict[str, Any]] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", "") or r.get("url", ""),
                    "snippet": r.get("body", "") or r.get("snippet", ""),
                }
            )
    return results


def _search_tavily(query: str, max_results: int, api_key: str) -> list[dict[str, Any]]:
    """Search with Tavily. Higher quality, but requires an API key."""
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    response = client.search(query, max_results=max_results)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        }
        for r in response.get("results", [])
    ]


def search_web_impl(
    query: str, max_results: int, config: Config
) -> list[dict[str, Any]]:
    """Run a web search and return unified result dicts.

    Uses Tavily when ``config.tavily_api_key`` is set, otherwise DuckDuckGo.
    On failure returns a single-element list with an ``error`` entry so the
    caller (and the MCP client) always gets a structured, non-crashing result.
    """
    query = (query or "").strip()
    if not query:
        return [{"error": "query must not be empty"}]

    max_results = max(1, min(int(max_results or 5), 20))

    last_error: str | None = None
    attempts = 3 if not config.tavily_api_key else 1
    for attempt in range(1, attempts + 1):
        try:
            if config.tavily_api_key:
                return _search_tavily(query, max_results, config.tavily_api_key)
            return _search_ddg(query, max_results)
        except Exception as exc:  # noqa: BLE001 - search backends raise varied errors
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts:
                time.sleep(0.8 * attempt)  # light backoff for DDGS rate limits

    return [{"error": f"search failed after {attempts} attempt(s): {last_error}"}]


def register_search_tools(mcp, config: Config) -> None:
    """Register the `search_web` MCP tool."""

    @mcp.tool()
    def search_web(query: str, max_results: int = 5) -> list[SearchResult]:
        """Search the web for up-to-date information.

        Uses DuckDuckGo by default (no API key required). If the TAVILY_API_KEY
        environment variable is set, Tavily is used instead for higher-quality
        results. Returns a list of results, each with title, url and snippet.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return (1-20, default 5).

        Returns:
            A list of objects: [{"title": str, "url": str, "snippet": str}, ...].
            On failure returns [{"error": str}].
        """
        results = search_web_impl(query, max_results, config)
        # Return plain dicts — FastMCP serialises them to the same JSON shape
        # that SearchResult describes, but dicts are more flexible for error rows.
        return results  # type: ignore[return-value]
