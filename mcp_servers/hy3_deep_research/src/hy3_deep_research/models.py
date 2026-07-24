"""Input and internal data models."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl, model_validator


class EvidenceInput(BaseModel):
    """One source supplied to the evidence-analysis tool."""

    title: str = Field(
        description="Human-readable source title", min_length=1, max_length=300
    )
    url: HttpUrl | None = Field(
        default=None,
        description="Optional HTTP(S) URL. It is fetched when content is omitted.",
    )
    content: str | None = Field(
        default=None,
        description="Optional source text. Supplying text avoids a network fetch.",
        max_length=100_000,
    )

    @model_validator(mode="after")
    def require_url_or_content(self) -> "EvidenceInput":
        if self.url is None and not (self.content and self.content.strip()):
            raise ValueError("each source requires either url or non-empty content")
        return self


class SearchResult(BaseModel):
    """Normalized result returned by the web search provider."""

    title: str
    url: str
    snippet: str = ""
    published_at: str | None = None


class Evidence(BaseModel):
    """Normalized evidence passed to Hy3."""

    source_id: str
    title: str
    url: str | None
    content: str


class FetchedDocument(BaseModel):
    """Extracted content from a web page."""

    title: str
    url: str
    content: str
    content_type: str
