from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from hy3_deep_research.fetcher import FetchError
from hy3_deep_research.models import EvidenceInput, FetchedDocument, SearchResult
from hy3_deep_research.service import ResearchService


@dataclass
class FakeSearchProvider:
    results: list[SearchResult]

    async def search(self, query: str, **_: object) -> list[SearchResult]:
        return self.results


@dataclass
class FakeFetcher:
    documents: dict[str, FetchedDocument | Exception]

    async def fetch(self, url: str) -> FetchedDocument:
        result = self.documents[url]
        if isinstance(result, Exception):
            raise result
        return result


@dataclass
class FakeAnalyzer:
    response: str = "Grounded answer [S1]."
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


def make_service(
    results: list[SearchResult],
    documents: dict[str, FetchedDocument | Exception],
) -> tuple[ResearchService, FakeAnalyzer]:
    analyzer = FakeAnalyzer()
    return (
        ResearchService(
            search_provider=FakeSearchProvider(results),
            fetcher=FakeFetcher(documents),  # type: ignore[arg-type]
            analyzer_factory=lambda: analyzer,
            max_page_chars=20_000,
        ),
        analyzer,
    )


@pytest.mark.asyncio
async def test_search_web_returns_structured_results() -> None:
    result = SearchResult(title="Hy3", url="https://example.com/hy3", snippet="Model")
    service, _ = make_service([result], {})

    output = await service.search_web(
        "Hy3",
        max_results=5,
        region="wt-wt",
        time_range="any",
    )

    assert output["result_count"] == 1
    assert output["results"][0]["url"] == "https://example.com/hy3"


@pytest.mark.asyncio
async def test_deep_research_uses_page_text_and_snippet_fallback() -> None:
    results = [
        SearchResult(
            title="Primary", url="https://example.com/one", snippet="one snippet"
        ),
        SearchResult(
            title="Backup", url="https://example.com/two", snippet="backup snippet"
        ),
    ]
    documents = {
        "https://example.com/one": FetchedDocument(
            title="Primary",
            url="https://example.com/one",
            content="full primary evidence",
            content_type="text/html",
        ),
        "https://example.com/two": FetchError("blocked"),
    }
    service, analyzer = make_service(results, documents)

    output = await service.deep_research(
        "research question",
        max_results=2,
        depth="standard",
        language="English",
        region="wt-wt",
        time_range="any",
    )

    assert output["report"] == "Grounded answer [S1]."
    assert [source["id"] for source in output["sources"]] == ["S1", "S2"]
    assert len(output["warnings"]) == 1
    prompt = analyzer.calls[0][1]
    assert "full primary evidence" in prompt
    assert "backup snippet" in prompt
    assert "Cite every material factual claim" in prompt


@pytest.mark.asyncio
async def test_analyze_evidence_preserves_source_ids_when_fetch_fails() -> None:
    documents = {
        "https://example.com/missing": FetchError("not found"),
    }
    service, analyzer = make_service([], documents)
    sources = [
        EvidenceInput(title="Missing", url="https://example.com/missing"),
        EvidenceInput(title="Inline", content="trusted supplied evidence"),
    ]

    output = await service.analyze_evidence(
        "What is supported?",
        sources,
        focus="facts",
        language="English",
    )

    assert output["sources"][0]["id"] == "S2"
    assert output["warnings"][0].startswith("S1 could not be fetched")
    assert '<source id="S2">' in analyzer.calls[0][1]


@pytest.mark.asyncio
async def test_research_rejects_empty_search_results() -> None:
    service, _ = make_service([], {})
    with pytest.raises(ValueError, match="no sources"):
        await service.deep_research(
            "unknown",
            max_results=2,
            depth="quick",
            language="English",
            region="wt-wt",
            time_range="any",
        )
