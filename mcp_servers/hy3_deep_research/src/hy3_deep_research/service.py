"""Orchestration layer for search, extraction, and Hy3 synthesis."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from .fetcher import FetchError, WebFetcher
from .hy3_client import Analyzer
from .models import Evidence, EvidenceInput, SearchResult
from .prompts import (
    SYSTEM_PROMPT,
    analysis_prompt,
    research_prompt,
    verification_prompt,
)
from .search import SearchProvider, TimeRange


class ResearchService:
    def __init__(
        self,
        *,
        search_provider: SearchProvider,
        fetcher: WebFetcher,
        analyzer_factory: Callable[[], Analyzer],
        max_page_chars: int = 20_000,
    ) -> None:
        self._search_provider = search_provider
        self._fetcher = fetcher
        self._analyzer_factory = analyzer_factory
        self._max_page_chars = max_page_chars

    async def search_web(
        self,
        query: str,
        *,
        max_results: int,
        region: str,
        time_range: TimeRange,
    ) -> dict:
        results = await self._search_provider.search(
            query,
            max_results=max_results,
            region=region,
            time_range=time_range,
        )
        return {
            "query": query,
            "result_count": len(results),
            "results": [result.model_dump() for result in results],
        }

    async def analyze_evidence(
        self,
        question: str,
        sources: list[EvidenceInput],
        *,
        focus: str,
        language: str,
    ) -> dict:
        evidence, warnings = await self._prepare_supplied_evidence(sources)
        if not evidence:
            raise ValueError("no usable evidence was supplied")
        report = await self._analyzer_factory().complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=analysis_prompt(question, focus, language, evidence),
        )
        return self._result(report, evidence, warnings)

    async def deep_research(
        self,
        query: str,
        *,
        max_results: int,
        depth: str,
        language: str,
        region: str,
        time_range: TimeRange,
    ) -> dict:
        results = await self._search_provider.search(
            query,
            max_results=max_results,
            region=region,
            time_range=time_range,
        )
        if not results:
            raise ValueError("search returned no sources; try a broader query")
        evidence, warnings = await self._search_results_to_evidence(results)
        report = await self._analyzer_factory().complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=research_prompt(query, language, depth, evidence),
        )
        return self._result(report, evidence, warnings, query=query)

    async def verify_claim(
        self,
        claim: str,
        *,
        max_results: int,
        language: str,
        region: str,
        time_range: TimeRange,
    ) -> dict:
        results = await self._search_provider.search(
            claim,
            max_results=max_results,
            region=region,
            time_range=time_range,
        )
        if not results:
            raise ValueError("search returned no sources; the claim cannot be verified")
        evidence, warnings = await self._search_results_to_evidence(results)
        report = await self._analyzer_factory().complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=verification_prompt(claim, language, evidence),
        )
        return self._result(report, evidence, warnings, query=claim)

    async def _prepare_supplied_evidence(
        self, sources: list[EvidenceInput]
    ) -> tuple[list[Evidence], list[str]]:
        if len(sources) > 12:
            raise ValueError("at most 12 sources are accepted per analysis")
        fetch_tasks = [
            self._fetcher.fetch(str(source.url))
            if source.url and not source.content
            else None
            for source in sources
        ]
        fetched = await asyncio.gather(
            *(task for task in fetch_tasks if task is not None), return_exceptions=True
        )
        fetched_iter = iter(fetched)
        evidence: list[Evidence] = []
        warnings: list[str] = []
        for index, (source, task) in enumerate(
            zip(sources, fetch_tasks, strict=True), start=1
        ):
            if task is None:
                content = (source.content or "").strip()[: self._max_page_chars]
                url = str(source.url) if source.url else None
                title = source.title
            else:
                document = next(fetched_iter)
                if isinstance(document, BaseException):
                    warnings.append(
                        f"S{index} could not be fetched ({self._safe_error(document)}) and was skipped"
                    )
                    continue
                content = document.content
                url = document.url
                title = source.title or document.title
            if content:
                evidence.append(
                    Evidence(
                        source_id=f"S{index}",
                        title=title,
                        url=url,
                        content=content,
                    )
                )
        return evidence, warnings

    async def _search_results_to_evidence(
        self, results: list[SearchResult]
    ) -> tuple[list[Evidence], list[str]]:
        fetched = await asyncio.gather(
            *(self._fetcher.fetch(result.url) for result in results),
            return_exceptions=True,
        )
        evidence: list[Evidence] = []
        warnings: list[str] = []
        for result, document in zip(results, fetched, strict=True):
            if isinstance(document, BaseException):
                if not result.snippet:
                    warnings.append(
                        f"{result.url} could not be fetched ({self._safe_error(document)}) and was skipped"
                    )
                    continue
                content = result.snippet
                warnings.append(
                    f"{result.url} used its search snippet because page fetch failed"
                )
            else:
                content = document.content
            evidence.append(
                Evidence(
                    source_id=f"S{len(evidence) + 1}",
                    title=result.title,
                    url=result.url,
                    content=content[: self._max_page_chars],
                )
            )
        if not evidence:
            raise FetchError("none of the search results contained usable evidence")
        return evidence, warnings

    @staticmethod
    def _safe_error(error: BaseException) -> str:
        if isinstance(error, FetchError):
            return str(error)
        return type(error).__name__

    @staticmethod
    def _result(
        report: str,
        evidence: list[Evidence],
        warnings: list[str],
        *,
        query: str | None = None,
    ) -> dict:
        result = {
            "report": report,
            "sources": [
                {
                    "id": item.source_id,
                    "title": item.title,
                    "url": item.url,
                }
                for item in evidence
            ],
            "warnings": warnings,
        }
        if query is not None:
            result["query"] = query
        return result
