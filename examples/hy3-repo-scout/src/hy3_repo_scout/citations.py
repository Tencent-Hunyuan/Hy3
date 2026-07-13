"""Parse and validate repository citations in model responses."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .tools import RepoTools, ToolError

_CITATION_PATTERN = re.compile(
    r"\[(?P<path>[^\[\]\r\n]+):L(?P<start>[1-9]\d{0,8})-L(?P<end>[1-9]\d{0,8})\]"
)
_BRACKETED_TEXT_PATTERN = re.compile(r"\[[^\[\]\r\n]+\]")
_LINE_ATTEMPT_PATTERN = re.compile(r"(?i)^(?:l|line\s*)?\d")
_OPEN_ENDED_ATTEMPT_PATTERN = re.compile(
    r"(?i)\[[^\[\]\r\n]+:L[0-9]+-L[0-9]+(?![0-9\]])"
)
_RANGE_ATTEMPT_PATTERN = re.compile(r"(?i)[^\s\[\]\r\n]+:L[0-9]+-L[0-9]+")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[/\\]")
DEFAULT_MAX_CITATION_LINES = 200
DEFAULT_MAX_CITATIONS = 500
DEFAULT_MAX_CITED_LINES = 10_000


class CitationError(ValueError):
    """Raised when a response contains a malformed or unverifiable citation."""

    def __init__(self, code: str, message: str, *, citation: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.citation = citation

    def to_dict(self) -> dict[str, str]:
        result = {"code": self.code, "message": self.message}
        if self.citation is not None:
            result["citation"] = self.citation
        return result


@dataclass(frozen=True)
class Citation:
    """A canonical, one-based inclusive repository line range."""

    path: str
    start_line: int
    end_line: int

    @property
    def label(self) -> str:
        return f"[{self.path}:L{self.start_line}-L{self.end_line}]"

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "label": self.label,
        }


@dataclass(frozen=True)
class EvidenceLine:
    """Hash of one repository line that was actually returned to the model."""

    path: str
    line: int
    sha256: str
    source_id: str | None = None
    source_tool: str | None = None


def parse_citation(value: str) -> Citation:
    """Parse one exact ``[path:Lx-Ly]`` citation and enforce canonical syntax."""
    if not isinstance(value, str):
        raise CitationError("malformed", "Citation must be a string.")
    match = _CITATION_PATTERN.fullmatch(value)
    if match is None:
        raise CitationError(
            "malformed",
            "Citation must use the exact format [relative/path:Lx-Ly].",
            citation=value,
        )

    path = match.group("path")
    _validate_citation_path(path, value)
    start_line = int(match.group("start"))
    end_line = int(match.group("end"))
    if end_line < start_line:
        raise CitationError(
            "invalid_range",
            "Citation end line must not be before its start line.",
            citation=value,
        )
    return Citation(path=path, start_line=start_line, end_line=end_line)


def extract_citations(text: str, *, strict: bool = True) -> list[Citation]:
    """Extract citations, optionally rejecting malformed bracketed citation attempts."""
    if not isinstance(text, str):
        raise CitationError("invalid_response", "Response must be a string.")
    if strict:
        _reject_broken_citation_brackets(text)
    citations: list[Citation] = []
    for match in _BRACKETED_TEXT_PATTERN.finditer(text):
        candidate = match.group(0)
        if ":L" not in candidate and not _looks_like_citation_attempt(candidate):
            continue
        try:
            citations.append(parse_citation(candidate))
        except CitationError:
            if strict:
                raise
    return citations


def _reject_broken_citation_brackets(text: str) -> None:
    """Reject missing, cross-line, or nested brackets around numeric citation ranges."""

    canonical = list(_CITATION_PATTERN.finditer(text))
    for match in canonical:
        nested_left = match.start() > 0 and text[match.start() - 1] == "["
        nested_right = match.end() < len(text) and text[match.end()] == "]"
        if nested_left or nested_right:
            _raise_broken_bracket(text, match.start(), match.end())

    open_ended = _OPEN_ENDED_ATTEMPT_PATTERN.search(text)
    if open_ended is not None:
        _raise_broken_bracket(text, open_ended.start(), open_ended.end())

    canonical_spans = [(match.start(), match.end()) for match in canonical]
    span_index = 0
    for attempt in _RANGE_ATTEMPT_PATTERN.finditer(text):
        if attempt.end() >= len(text) or text[attempt.end()] != "]":
            continue
        while (
            span_index < len(canonical_spans)
            and canonical_spans[span_index][1] <= attempt.start()
        ):
            span_index += 1
        if span_index < len(canonical_spans):
            start, end = canonical_spans[span_index]
        else:
            start, end = -1, -1
        if start <= attempt.start() and attempt.end() < end:
            continue
        _raise_broken_bracket(text, attempt.start(), attempt.end() + 1)


def _raise_broken_bracket(text: str, start: int, end: int) -> None:
    snippet_end = min(len(text), end + 32)
    candidate = text[max(0, start - 1) : snippet_end].splitlines()[0][:300]
    raise CitationError(
        "malformed",
        "Citation-like text must use one complete [relative/path:Lx-Ly] bracket.",
        citation=candidate,
    )


def validate_citations(
    text: str,
    repository: RepoTools | str | os.PathLike[str],
    *,
    require: bool = False,
    max_span: int = DEFAULT_MAX_CITATION_LINES,
    evidence_lines: Iterable[EvidenceLine] | None = None,
) -> list[Citation]:
    """Verify syntax, path safety, readability, and line bounds for every citation."""
    if isinstance(max_span, bool) or not isinstance(max_span, int) or max_span < 1:
        raise CitationError("invalid_limit", "max_span must be a positive integer.")
    citations = extract_citations(text, strict=True)
    if len(citations) > DEFAULT_MAX_CITATIONS:
        raise CitationError(
            "too_many_citations",
            f"A response may contain at most {DEFAULT_MAX_CITATIONS} citations.",
        )
    if require and not citations:
        raise CitationError(
            "missing",
            "The response must contain at least one repository citation.",
        )

    unique_citations = list(dict.fromkeys(citations))
    for citation in unique_citations:
        if citation.end_line - citation.start_line + 1 > max_span:
            raise CitationError(
                "range_too_large",
                f"A citation may cover at most {max_span} lines.",
                citation=citation.label,
            )
    cited_lines = {
        (citation.path, line)
        for citation in unique_citations
        for line in range(citation.start_line, citation.end_line + 1)
    }
    if len(cited_lines) > DEFAULT_MAX_CITED_LINES:
        raise CitationError(
            "too_many_cited_lines",
            f"A response may cite at most {DEFAULT_MAX_CITED_LINES} distinct lines.",
        )

    evidence = tuple(evidence_lines) if evidence_lines is not None else None
    evidence_by_line: dict[tuple[str, int], set[str]] = {}
    evidence_groups: dict[str, set[tuple[str, int]]] = {}
    range_groups: set[str] = set()
    if evidence is not None:
        for item in evidence:
            evidence_by_line.setdefault((item.path, item.line), set()).add(item.sha256)
            source_id = item.source_id or "legacy"
            evidence_groups.setdefault(source_id, set()).add((item.path, item.line))
            if item.source_id is None or item.source_tool == "read_file":
                range_groups.add(source_id)
        for citation in unique_citations:
            required = {
                (citation.path, line)
                for line in range(citation.start_line, citation.end_line + 1)
            }
            if citation.start_line == citation.end_line:
                covered = required.issubset(evidence_by_line)
            else:
                covered = any(
                    required.issubset(evidence_groups[source_id])
                    for source_id in range_groups
                )
            if not covered:
                raise CitationError(
                    "unseen_evidence",
                    "Citation was not covered by evidence returned to the model.",
                    citation=citation.label,
                )

    tools = repository if isinstance(repository, RepoTools) else RepoTools(repository)
    by_path: dict[str, set[int]] = {}
    citations_by_path: dict[str, list[Citation]] = {}
    for citation in unique_citations:
        by_path.setdefault(citation.path, set()).update(
            range(citation.start_line, citation.end_line + 1)
        )
        citations_by_path.setdefault(citation.path, []).append(citation)

    for path, lines in by_path.items():
        first_citation = citations_by_path[path][0]
        try:
            result = tools.citation_snapshot(path, lines)
        except ToolError as exc:
            raise CitationError(
                exc.code,
                f"Citation could not be verified: {exc.message}",
                citation=first_citation.label,
            ) from exc
        if result["path"] != path:
            raise CitationError(
                "noncanonical_path",
                "Citation path must be the canonical repository-relative path.",
                citation=first_citation.label,
            )
        out_of_range = next(
            (
                citation
                for citation in citations_by_path[path]
                if citation.end_line > result["total_lines"]
            ),
            None,
        )
        if out_of_range is not None:
            raise CitationError(
                "invalid_range",
                "Citation line range extends beyond the file.",
                citation=out_of_range.label,
            )
        if evidence is not None:
            current = {
                (item["path"], item["line"]): item["sha256"]
                for item in result.get("_evidence", [])
            }
            stale = next(
                (
                    citation
                    for citation in citations_by_path[path]
                    if any(
                        current.get((path, line))
                        not in evidence_by_line.get((path, line), set())
                        for line in range(citation.start_line, citation.end_line + 1)
                    )
                ),
                None,
            )
            if stale is not None:
                raise CitationError(
                    "stale_evidence",
                    "Cited content changed after it was returned to the model.",
                    citation=stale.label,
                )
    return citations


def citation_validation_result(
    text: str,
    repository: RepoTools | str | os.PathLike[str],
    *,
    require: bool = False,
    max_span: int = DEFAULT_MAX_CITATION_LINES,
    evidence_lines: Iterable[EvidenceLine] | None = None,
) -> dict[str, Any]:
    """Return a JSON-friendly validation result without leaking a traceback."""
    try:
        citations = validate_citations(
            text,
            repository,
            require=require,
            max_span=max_span,
            evidence_lines=evidence_lines,
        )
    except CitationError as exc:
        return {"valid": False, "citations": [], "error": exc.to_dict()}
    return {
        "valid": True,
        "citations": [citation.to_dict() for citation in citations],
        "error": None,
    }


def evidence_lines_from_trace(trace: Iterable[Any]) -> list[EvidenceLine]:
    """Recover private line hashes attached only to accepted read/search results."""
    evidence: list[EvidenceLine] = []
    for index, item in enumerate(trace):
        if getattr(item, "error", None):
            continue
        if getattr(item, "name", "") not in {"read_file", "search_text"}:
            continue
        source_id = (
            f"{index}:{getattr(item, 'round', 0)}:"
            f"{getattr(item, 'call_id', '') or index}"
        )
        source_tool = str(getattr(item, "name", ""))
        for line in getattr(item, "evidence", ()):
            if isinstance(line, EvidenceLine):
                evidence.append(
                    EvidenceLine(
                        path=line.path,
                        line=line.line,
                        sha256=line.sha256,
                        source_id=source_id,
                        source_tool=source_tool,
                    )
                )
    return evidence


def _looks_like_citation_attempt(candidate: str) -> bool:
    inner = candidate[1:-1]
    if ":" not in inner:
        return False
    path, suffix = inner.rsplit(":", 1)
    path_name = PurePosixPath(path).name
    return ("/" in path or "." in path_name) and bool(
        _LINE_ATTEMPT_PATTERN.match(suffix.strip())
    )


def _validate_citation_path(path: str, label: str) -> None:
    if not path or "\x00" in path or any(ord(character) < 32 for character in path):
        raise CitationError("unsafe_path", "Citation path is empty or unsafe.", citation=label)
    if "\\" in path:
        raise CitationError(
            "unsafe_path",
            "Citation paths must use forward slashes.",
            citation=label,
        )
    pure = PurePosixPath(path)
    if pure.is_absolute() or _WINDOWS_ABSOLUTE_PATH.match(path) or ".." in pure.parts:
        raise CitationError(
            "unsafe_path",
            "Citation path must stay inside the repository.",
            citation=label,
        )
    canonical = pure.as_posix()
    if canonical in {"", "."} or canonical != path or path.startswith("./"):
        raise CitationError(
            "noncanonical_path",
            "Citation path must be a canonical repository-relative file path.",
            citation=label,
        )
    if Path(path).drive:
        raise CitationError(
            "unsafe_path",
            "Absolute citation paths are not allowed.",
            citation=label,
        )


__all__ = [
    "Citation",
    "CitationError",
    "EvidenceLine",
    "citation_validation_result",
    "evidence_lines_from_trace",
    "extract_citations",
    "parse_citation",
    "validate_citations",
]
