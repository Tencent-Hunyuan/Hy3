from pathlib import Path, PurePosixPath

from hy3_knowledge_mcp.models import (
    AllowedRoot,
    AskResult,
    Citation,
    IndexDocumentsResult,
    ListSourcesResult,
    SummaryResult,
)
from hy3_knowledge_mcp.renderers import (
    render_ask_markdown,
    render_index_markdown,
    render_json,
    render_list_sources_markdown,
    render_summary_markdown,
)


def citation() -> Citation:
    return Citation(
        evidence_id="S1",
        source_path=PurePosixPath("0123456789ab/guide.md"),
        line_start=2,
        line_end=3,
    )


def test_answer_and_summary_render_public_locations_only() -> None:
    ask = AskResult(
        answer="answer",
        grounded=True,
        insufficient_evidence=False,
        citations=(citation(),),
    )
    summary = SummaryResult(
        summary="summary",
        coverage="full",
        used_evidence_ids=("S1",),
        citations=(citation(),),
    )

    assert "C:\\" not in render_ask_markdown(ask)
    assert "[S1] 0123456789ab/guide.md, lines 2-3" in render_ask_markdown(ask)
    assert "Coverage: full" in render_summary_markdown(summary)


def test_index_list_and_json_renderers_are_stable() -> None:
    indexed = IndexDocumentsResult(
        collection="docs",
        discovered_sources=1,
        indexed_sources=1,
        updated_sources=0,
        unchanged_sources=0,
        skipped_sources=0,
        failed_sources=0,
        chunk_count=2,
    )
    listed = ListSourcesResult(
        total=0,
        count=0,
        offset=0,
        has_more=False,
        sources=(),
    )

    assert "# Indexed collection: docs" in render_index_markdown(indexed)
    assert render_list_sources_markdown(listed).startswith("# Indexed sources (0)")
    assert render_json(indexed).startswith('{\n  "collection": "docs"')


def test_json_renderer_excludes_internal_absolute_paths(tmp_path: Path) -> None:
    absolute_root = tmp_path.resolve()
    root = AllowedRoot(root_id="0123456789ab", path=absolute_root)

    rendered = render_json(root)

    assert rendered == '{\n  "root_id": "0123456789ab"\n}'
    assert str(absolute_root) not in rendered
