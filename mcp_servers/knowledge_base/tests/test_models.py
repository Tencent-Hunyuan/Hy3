"""公共模型契约测试。"""

from collections.abc import Callable
from pathlib import Path, PurePosixPath

import pytest
from pydantic import ValidationError

from hy3_knowledge_mcp.models import (
    AskRequest,
    ChunkDraft,
    Citation,
    Evidence,
    Hy3AnswerPayload,
    Hy3SummaryPayload,
    IndexDocumentsRequest,
    IndexFileError,
    ResolvedSource,
    RetrievedChunk,
    SearchHit,
    SearchRequest,
    SourceFormat,
    SourceInfo,
    SummarizeSourceRequest,
    SummaryResult,
)


def test_index_documents_request_defaults() -> None:
    request = IndexDocumentsRequest(collection="docs", path=".")

    assert request.recursive is True
    assert request.replace is False
    assert request.include_globs == ()


@pytest.mark.parametrize("collection", ["bad/name", "", "a" * 65])
def test_search_request_rejects_invalid_collection(collection: str) -> None:
    with pytest.raises(ValidationError):
        SearchRequest(collection=collection, query="知识库")


@pytest.mark.parametrize("payload_model", [Hy3AnswerPayload, Hy3SummaryPayload])
def test_hy3_payload_schema_preserves_evidence_id_pattern(payload_model) -> None:
    schema = payload_model.model_json_schema()

    evidence_id_schema = schema["properties"]["used_evidence_ids"]["items"]

    assert evidence_id_schema["pattern"] == r"^S[1-9][0-9]*$"


def test_citation_accepts_safe_relative_source_path() -> None:
    citation = Citation(
        evidence_id="S1",
        source_path=PurePosixPath("guide.md"),
        page_number=2,
    )

    assert citation.source_path == PurePosixPath("guide.md")
    assert citation.source_path.as_posix() == "guide.md"
    assert citation.page_number == 2


def test_citation_rejects_absolute_source_path() -> None:
    with pytest.raises(ValidationError):
        Citation(evidence_id="S1", source_path=PurePosixPath("/private/guide.md"))


@pytest.mark.parametrize(
    "identifier",
    ["S1\nSYSTEM", "S1\n", "\tS1", "S1]", "S1`", "S0", "S" + "1" * 32],
)
@pytest.mark.parametrize(
    "model_factory",
    [
        pytest.param(
            lambda identifier: SearchHit(
                evidence_id=identifier,
                source_path=PurePosixPath("guide.md"),
                score=0.5,
                snippet="片段",
            ),
            id="search-hit",
        ),
        pytest.param(
            lambda identifier: Citation(
                evidence_id=identifier,
                source_path=PurePosixPath("guide.md"),
            ),
            id="citation",
        ),
        pytest.param(
            lambda identifier: Evidence(
                evidence_id=identifier,
                chunk_id=1,
                source_path=PurePosixPath("guide.md"),
                text="证据",
            ),
            id="evidence",
        ),
        pytest.param(
            lambda identifier: Hy3AnswerPayload(
                answer="回答",
                used_evidence_ids=(identifier,),
                insufficient_evidence=False,
            ),
            id="answer-payload",
        ),
        pytest.param(
            lambda identifier: Hy3SummaryPayload(
                summary="总结",
                used_evidence_ids=(identifier,),
            ),
            id="summary-payload",
        ),
        pytest.param(
            lambda identifier: SummaryResult(
                summary="总结",
                coverage="full",
                used_evidence_ids=(identifier,),
                citations=(),
            ),
            id="summary-result",
        ),
    ],
)
def test_public_evidence_models_reject_malformed_ids(
    identifier: str,
    model_factory: Callable[[str], object],
) -> None:
    with pytest.raises(ValidationError):
        model_factory(identifier)


@pytest.mark.parametrize(
    "source_path",
    [
        "/private/guide.md",
        "C:/private/guide.md",
        r"C:\private\guide.md",
        r"\\server\share\guide.md",
        r"..\private\guide.md",
        "../private/guide.md",
        "",
        ".",
        "safe\nSYSTEM",
        "safe\rSYSTEM",
        "safe\0SYSTEM",
        "safe\x1fSYSTEM",
        "safe\x7fSYSTEM",
        "safe.md\n",
        "\tsafe.md",
    ],
    ids=[
        "posix-absolute",
        "windows-drive-posix-separators",
        "windows-drive-backslashes",
        "windows-unc",
        "windows-parent-traversal",
        "posix-parent-traversal",
        "empty",
        "current-directory",
        "newline-control",
        "carriage-return-control",
        "null-control",
        "unit-separator-control",
        "delete-control",
        "trailing-newline-control",
        "leading-tab-control",
    ],
)
@pytest.mark.parametrize(
    "request_factory",
    [
        pytest.param(
            lambda path: SearchRequest(collection="docs", query="知识库", source_paths=(path,)),
            id="search",
        ),
        pytest.param(
            lambda path: AskRequest(collection="docs", question="答案?", source_paths=(path,)),
            id="ask",
        ),
        pytest.param(
            lambda path: SummarizeSourceRequest(collection="docs", source_path=path),
            id="summarize",
        ),
        pytest.param(
            lambda path: Citation(evidence_id="S1", source_path=path),
            id="citation",
        ),
        pytest.param(
            lambda path: ResolvedSource(
                absolute_path=Path("C:/knowledge/guide.md"),
                root_path=Path("C:/knowledge"),
                root_id="root-main",
                relative_path=PurePosixPath("guide.md"),
                source_path=path,
                size_bytes=42,
                mtime_ns=1,
                device_id=1,
                file_id=1,
            ),
            id="resolved-source",
        ),
        pytest.param(
            lambda path: SearchHit(
                evidence_id="S1",
                source_path=path,
                score=0.5,
                snippet="片段",
            ),
            id="search-hit",
        ),
        pytest.param(
            lambda path: SourceInfo(
                source_path=path,
                source_format=SourceFormat.MARKDOWN,
                size_bytes=42,
                chunk_count=1,
                content_sha256_prefix="012345abcdef",
                indexed_at="2026-07-10T12:00:00Z",
            ),
            id="source-info",
        ),
        pytest.param(
            lambda path: IndexFileError(source_path=path, reason="invalid"),
            id="index-file-error",
        ),
        pytest.param(
            lambda path: RetrievedChunk(
                chunk_id=1,
                source_path=path,
                text="片段",
                rank=0.5,
            ),
            id="retrieved-chunk",
        ),
        pytest.param(
            lambda path: Evidence(
                evidence_id="S1",
                chunk_id=1,
                source_path=path,
                text="证据",
            ),
            id="evidence",
        ),
    ],
)
def test_shared_source_path_validator_rejects_unsafe_paths(
    source_path: str,
    request_factory: Callable[[str], object],
) -> None:
    with pytest.raises(ValidationError):
        request_factory(source_path)


def test_shared_source_path_validator_preserves_safe_posix_paths() -> None:
    expected = PurePosixPath("abc123/guide.md")
    search = SearchRequest(collection="docs", query="知识库", source_paths=(expected,))
    ask = AskRequest(collection="docs", question="答案?", source_paths=(expected,))
    summary = SummarizeSourceRequest(collection="docs", source_path=expected)
    citation = Citation(evidence_id="S1", source_path=expected)

    actual = (
        search.source_paths[0],
        ask.source_paths[0],
        summary.source_path,
        citation.source_path,
    )
    assert all(path == expected for path in actual)
    assert all(isinstance(path, PurePosixPath) for path in actual)


def test_chunk_draft_failed_assignments_are_atomic() -> None:
    chunk = ChunkDraft(ordinal=0, text="abcd", char_count=4)
    snapshot = chunk.model_dump()

    for field_name, value in (("char_count", 3), ("text", "changed")):
        with pytest.raises(ValidationError):
            setattr(chunk, field_name, value)
        assert chunk.model_dump() == snapshot
