"""Web search provider backed by DDGS."""

from __future__ import annotations

import asyncio
from typing import Literal, Protocol

from ddgs import DDGS

from .models import SearchResult

TimeRange = Literal["day", "week", "month", "year", "any"]


class SearchProvider(Protocol):
    async def search(
        self,
        query: str,
        *,
        max_results: int,
        region: str,
        time_range: TimeRange,
    ) -> list[SearchResult]: ...


class SearchError(RuntimeError):
    """Raised when the search provider fails."""


class DDGSSearchProvider:
    """Key-free public web search through the DDGS package."""

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._timeout_seconds = timeout_seconds

    async def search(
        self,
        query: str,
        *,
        max_results: int,
        region: str,
        time_range: TimeRange,
    ) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._search_sync,
                    query,
                    max_results,
                    region,
                    time_range,
                ),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise SearchError("web search timed out") from exc
        except Exception as exc:
            raise SearchError(f"web search failed: {type(exc).__name__}") from exc

    @staticmethod
    def _search_sync(
        query: str,
        max_results: int,
        region: str,
        time_range: TimeRange,
    ) -> list[SearchResult]:
        timelimit = None if time_range == "any" else time_range[0]
        raw_results = DDGS().text(
            query,
            region=region,
            safesearch="moderate",
            timelimit=timelimit,
            max_results=max_results,
        )
        results: list[SearchResult] = []
        seen_urls: set[str] = set()
        for item in raw_results or []:
            url = str(item.get("href") or item.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(
                SearchResult(
                    title=str(item.get("title") or url).strip(),
                    url=url,
                    snippet=str(item.get("body") or item.get("snippet") or "").strip(),
                    published_at=item.get("date"),
                )
            )
        return results[:max_results]
