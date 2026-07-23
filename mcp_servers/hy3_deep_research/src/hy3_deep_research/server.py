"""MCP stdio entry point and public tool definitions."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .config import Settings
from .fetcher import WebFetcher
from .hy3_client import Hy3Client
from .models import EvidenceInput
from .search import DDGSSearchProvider
from .service import ResearchService


def build_service(settings: Settings | None = None) -> ResearchService:
    settings = settings or Settings.from_env()
    analyzer: Hy3Client | None = None

    def get_analyzer() -> Hy3Client:
        nonlocal analyzer
        if analyzer is None:
            analyzer = Hy3Client(settings)
        return analyzer

    return ResearchService(
        search_provider=DDGSSearchProvider(settings.search_timeout_seconds),
        fetcher=WebFetcher(
            timeout_seconds=settings.fetch_timeout_seconds,
            max_chars=settings.max_page_chars,
            allow_private_urls=settings.allow_private_urls,
        ),
        analyzer_factory=get_analyzer,
        max_page_chars=settings.max_page_chars,
    )


def create_server(service: ResearchService | None = None) -> FastMCP:
    research = service or build_service()
    mcp = FastMCP(
        "Hy3 Deep Research",
        instructions=(
            "Search the public web, collect evidence, and ask Hy3 to produce grounded "
            "research reports and claim verification with source IDs."
        ),
    )

    @mcp.tool()
    async def search_web(
        query: Annotated[
            str,
            Field(
                description="Search query; include names, dates, and domain terms for precise results",
                min_length=2,
                max_length=500,
            ),
        ],
        max_results: Annotated[
            int, Field(description="Maximum number of unique results", ge=1, le=12)
        ] = 6,
        region: Annotated[
            str,
            Field(
                description="DDGS region code, for example cn-zh, us-en, or wt-wt",
                max_length=20,
            ),
        ] = "wt-wt",
        time_range: Annotated[
            Literal["day", "week", "month", "year", "any"],
            Field(description="Optional publication recency filter"),
        ] = "any",
    ) -> dict:
        """Search the public web and return normalized titles, URLs, snippets, and dates."""

        return await research.search_web(
            query,
            max_results=max_results,
            region=region,
            time_range=time_range,
        )

    @mcp.tool()
    async def analyze_evidence(
        question: Annotated[
            str,
            Field(
                description="Question Hy3 should answer from the supplied evidence",
                min_length=2,
            ),
        ],
        sources: Annotated[
            list[EvidenceInput],
            Field(
                description=(
                    "One to twelve sources. Each source needs a title and either inline content "
                    "or an HTTP(S) URL to fetch."
                ),
                min_length=1,
                max_length=12,
            ),
        ],
        focus: Annotated[
            str,
            Field(
                description="Desired analysis angle, constraints, or comparison criteria",
                max_length=1000,
            ),
        ] = "Identify the strongest supported conclusion and material uncertainties.",
        language: Annotated[
            str,
            Field(
                description="Output language or locale, for example zh-CN or English",
                max_length=40,
            ),
        ] = "zh-CN",
    ) -> dict:
        """Use Hy3 to analyze user-provided text or URLs with grounded source citations."""

        return await research.analyze_evidence(
            question,
            sources,
            focus=focus,
            language=language,
        )

    @mcp.tool()
    async def deep_research(
        query: Annotated[
            str,
            Field(
                description="Research topic or decision question",
                min_length=2,
                max_length=500,
            ),
        ],
        max_results: Annotated[
            int,
            Field(
                description="Number of web sources to search and inspect", ge=2, le=12
            ),
        ] = 8,
        depth: Annotated[
            Literal["quick", "standard", "deep"],
            Field(
                description="Requested report depth; deeper reports usually take longer"
            ),
        ] = "standard",
        language: Annotated[
            str,
            Field(
                description="Report language or locale, for example zh-CN or English",
                max_length=40,
            ),
        ] = "zh-CN",
        region: Annotated[
            str, Field(description="DDGS search region code", max_length=20)
        ] = "wt-wt",
        time_range: Annotated[
            Literal["day", "week", "month", "year", "any"],
            Field(description="Optional publication recency filter"),
        ] = "any",
    ) -> dict:
        """Search, read multiple pages, and have Hy3 synthesize a cited research report."""

        return await research.deep_research(
            query,
            max_results=max_results,
            depth=depth,
            language=language,
            region=region,
            time_range=time_range,
        )

    @mcp.tool()
    async def verify_claim(
        claim: Annotated[
            str,
            Field(
                description="Specific factual claim to verify",
                min_length=4,
                max_length=1000,
            ),
        ],
        max_results: Annotated[
            int,
            Field(
                description="Number of independent search results to inspect",
                ge=2,
                le=12,
            ),
        ] = 6,
        language: Annotated[
            str,
            Field(description="Verification report language or locale", max_length=40),
        ] = "zh-CN",
        region: Annotated[
            str, Field(description="DDGS search region code", max_length=20)
        ] = "wt-wt",
        time_range: Annotated[
            Literal["day", "week", "month", "year", "any"],
            Field(description="Optional publication recency filter"),
        ] = "any",
    ) -> dict:
        """Search for corroborating evidence and let Hy3 classify a claim with citations."""

        return await research.verify_claim(
            claim,
            max_results=max_results,
            language=language,
            region=region,
            time_range=time_range,
        )

    return mcp


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
