"""Pydantic data models for structured tool outputs.

These models make the JSON Schema that FastMCP exposes to clients clean and
self-documenting, and keep the orchestration logic type-safe.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single web search result."""

    title: str = Field(description="Title of the search result")
    url: str = Field(description="URL of the search result")
    snippet: str = Field(description="Short snippet/summary of the result content")


class FetchResult(BaseModel):
    """The extracted content of a fetched web page."""

    url: str = Field(description="The URL that was fetched")
    title: str = Field(description="Page title, if available")
    content: str = Field(description="Extracted main text content of the page")
    success: bool = Field(description="Whether the fetch and extraction succeeded")
    error: str | None = Field(default=None, description="Error message if the fetch failed")


class ResearchCitation(BaseModel):
    """A citation/source referenced in a research report."""

    index: int = Field(description="1-based citation index used in the report (e.g. [1])")
    title: str = Field(description="Title of the source")
    url: str = Field(description="URL of the source")


class ResearchReport(BaseModel):
    """The full output of a deep_research run."""

    query: str = Field(description="The original research question")
    sub_queries: list[str] = Field(description="Sub-queries Hy3 decomposed the question into")
    sources_searched: int = Field(description="Total number of search results gathered")
    sources_fetched: int = Field(description="Number of sources whose full text was read")
    report: str = Field(description="The synthesized research report with inline [n] citations")
    citations: list[ResearchCitation] = Field(description="Ordered list of cited sources")
