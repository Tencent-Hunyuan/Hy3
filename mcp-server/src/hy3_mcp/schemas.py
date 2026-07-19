# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Structured output models for every hy3-mcp tool.

FastMCP turns these pydantic models into each tool's ``outputSchema`` and
serializes returned instances as ``structuredContent`` alongside the text
content.  Design rule: every structured field is computed deterministically
in Python; Hy3's narrative goes exclusively into the ``markdown`` field and
is never parsed.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

__all__ = [
    "DiffStats",
    "Flag",
    "ReviewResult",
    "Citation",
    "DocAnswer",
    "ColumnProfile",
    "TableProfile",
    "DataReport",
    "Evidence",
    "ResearchReport",
    "UsageStats",
    "ServerInfo",
]


class DiffStats(BaseModel):
    """Deterministic statistics parsed from a unified diff."""

    files: list[str] = Field(description="Touched file paths (from +++ headers)")
    hunks: int = Field(description="Number of @@ hunks")
    added_lines: int = Field(description="Count of added (+) lines")
    removed_lines: int = Field(description="Count of removed (-) lines")


class Flag(BaseModel):
    """One deterministic heuristic finding (computed in Python, not by Hy3)."""

    category: Literal["security", "correctness", "maintainability", "style"]
    severity: Literal["high", "medium", "low"]
    file: str
    line: int = Field(description="New-file line number (0 if unknown)")
    message: str


class ReviewResult(BaseModel):
    """Output of the review_code tool."""

    markdown: str = Field(description="Hy3's review narrative (never parsed)")
    stats: DiffStats
    heuristic_flags: list[Flag]
    model: str = Field(description="Backend model that produced the narrative")
    mode: Literal["offline", "real"]


class Citation(BaseModel):
    """A retrieved evidence chunk backing the answer."""

    file: str
    chunk_id: int
    snippet: str = Field(description="First characters of the cited chunk")


class DocAnswer(BaseModel):
    """Output of the ask_docs tool."""

    markdown: str
    citations: list[Citation]
    searched_files: int = Field(description="How many documents were scanned")
    mode: Literal["offline", "real"]


class ColumnProfile(BaseModel):
    """Deterministic per-column statistics."""

    name: str
    dtype: Literal["number", "text", "mixed", "empty"]
    missing: int
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    top_values: list[str] = Field(
        default_factory=list, description='Top categories as "value (count)"'
    )


class TableProfile(BaseModel):
    """Deterministic profile of a CSV/JSON table."""

    format: Literal["csv", "json"]
    rows: int
    columns: list[ColumnProfile]


class DataReport(BaseModel):
    """Output of the analyze_data tool."""

    markdown: str
    profile: TableProfile
    chart_suggestions: list[str] = Field(
        description="Rule-based chart ideas (independent of the LLM narrative)"
    )
    mode: Literal["offline", "real"]


class Evidence(BaseModel):
    """One evidence item collected for deep_research."""

    kind: Literal["search", "file"]
    ref: str = Field(description="Search hit 'title <url>' or sandbox-relative path")
    snippet: str


class ResearchReport(BaseModel):
    """Output of the deep_research tool."""

    markdown: str
    evidence: list[Evidence]
    search_provider: str
    mode: Literal["offline", "real"]


class UsageStats(BaseModel):
    calls: int
    prompt_tokens: int
    completion_tokens: int


class ServerInfo(BaseModel):
    """Output of the hy3_status diagnostics tool (no LLM call)."""

    server_version: str
    protocol: str = "MCP/stdio"
    mode: Literal["offline", "real"]
    api_base: str
    api_key_present: bool
    model: str
    search_provider: str
    sandbox_root: str
    usage: UsageStats
