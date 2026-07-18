"""多语言查询规划、检索集成与证据预算测试。"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from hy3_knowledge_mcp.errors import IndexNotFoundError
from hy3_knowledge_mcp.models import (
    ChunkDraft,
    RetrievedChunk,
    RetrievedPage,
    SearchRequest,
    SourceFormat,
)
from hy3_knowledge_mcp.retrieval import (
    assign_evidence,
    build_query_plan,
    build_search_result,
    search_store,
    select_context_chunks,
)
from hy3_knowledge_mcp.store import SQLiteStore


def _chunks(*texts: str) -> tuple[ChunkDraft, ...]:
    """构造顺序稳定的测试分块。"""
    return tuple(
        ChunkDraft(ordinal=index, text=text, char_count=len(text))
        for index, text in enumerate(texts)
    )


def _replace(
    store: SQLiteStore,
    relative_path: str,
    digest_character: str,
    *texts: str,
) -> PurePosixPath:
    """向真实 SQLite 索引写入单一来源。"""
    store.replace_source(
        collection="docs",
        root_id="0123456789ab",
        relative_path=PurePosixPath(relative_path),
        content_sha256=digest_character * 64,
        mtime_ns=1,
        size_bytes=sum(map(len, texts)),
        source_format=SourceFormat.MARKDOWN,
        page_count=None,
        chunks=_chunks(*texts),
    )
    return PurePosixPath("0123456789ab") / relative_path


def _retrieved(chunk_id: int, text: str, *, rank: float = 0.0) -> RetrievedChunk:
    """构造一条预算测试所需的检索分块。"""
    return RetrievedChunk(
        chunk_id=chunk_id,
        source_path=PurePosixPath(f"root/doc-{chunk_id}.md"),
        text=text,
        rank=rank,
    )


def _create_empty_collection(store: SQLiteStore) -> None:
    """创建不含来源或分块但真实存在的集合。"""
    with store.connect() as connection, connection:
        connection.execute(
            "INSERT INTO collections(name, created_at, updated_at) VALUES (?, ?, ?)",
            ("docs", "2026-07-11T00:00:00+00:00", "2026-07-11T00:00:00+00:00"),
        )


@pytest.mark.parametrize(
    ("query", "expected_fts", "expected_like"),
    [
        ('Hy3 退款 "条件"', '"Hy3"', ("退款", "条件")),
        ("退款", None, ("退款",)),
        ("What is Hy3?", '"Hy3"', ()),
        ("an and the", None, ()),
    ],
)
def test_query_plan_compiles_ascii_cjk_and_stopwords(
    query: str,
    expected_fts: str | None,
    expected_like: tuple[str, ...],
) -> None:
    plan = build_query_plan(query)

    assert plan.fts_query == expected_fts
    assert plan.like_terms == expected_like


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("不仅回答日期，还要解释原因", "不仅回答日期,还要解释原因"),  # noqa: RUF001
        ("讨论仅回答模式的安全性", "讨论仅回答模式的安全性"),
        ("仅仅回复日期", "仅仅回复日期"),
        ("问题。仅回复日期", "问题。仅回复日期"),
        ("问题; 仅输出日期", "问题; 仅输出日期"),
    ],
)
def test_instruction_like_chinese_prose_is_preserved(query: str, expected: str) -> None:
    plan = build_query_plan(query)

    assert plan.normalized_query == expected


def test_query_term_counts_are_bounded_and_deduplicated_before_sql() -> None:
    long_terms = " ".join(f"term{index}" for index in range(80))
    short_terms = " ".join(chr(0x4E00 + index) * 2 for index in range(40))
    plan = build_query_plan(f"{long_terms} {short_terms}")

    assert plan.fts_query is not None
    assert len(plan.fts_query.split(" OR ")) == 64
    assert len(plan.like_terms) == 32


def test_query_plan_quotes_fts_syntax_instead_of_compiling_operators() -> None:
    plan = build_query_plan('Hy3" OR * NEAR(foo) "unterminated')

    assert plan.fts_query == '"Hy3" OR "NEAR" OR "foo" OR "unterminated"'
    assert plan.like_terms == ()


def test_context_budget_counts_real_separators_before_selecting() -> None:
    chunks = (_retrieved(1, "x" * 10), _retrieved(2, "y" * 10), _retrieved(3, "z"))

    selected = select_context_chunks(chunks, max_context_chars=22)

    assert [item.chunk_id for item in selected] == [1, 2]
    assert len("\n\n".join(item.text for item in selected)) == 22


def test_context_budget_truncates_first_chunk_without_empty_evidence() -> None:
    chunks = (_retrieved(1, "abcdef"), _retrieved(2, "later"))

    selected = select_context_chunks(chunks, max_context_chars=3)
    evidence = assign_evidence(selected)

    assert [item.text for item in selected] == ["abc"]
    assert evidence[0].text == "abc"


def test_evidence_ids_are_assigned_only_after_budget_cutoff() -> None:
    selected = select_context_chunks(
        (_retrieved(7, "x" * 10), _retrieved(9, "y" * 10), _retrieved(11, "z" * 10)),
        max_context_chars=22,
    )

    evidence = assign_evidence(selected)

    assert [(item.evidence_id, item.chunk_id) for item in evidence] == [("S1", 7), ("S2", 9)]


def test_search_result_has_stable_ids_scores_snippets_and_pagination() -> None:
    page = RetrievedPage(
        total=3,
        items=(
            RetrievedChunk(
                chunk_id=7,
                source_path=PurePosixPath("root/guide.md"),
                text="a" * 500,
                line_start=10,
                line_end=12,
                rank=1.5,
            ),
            _retrieved(8, "short", rank=0.25),
        ),
        has_more=True,
        next_offset=4,
    )
    request = SearchRequest(collection="docs", query="guide", limit=2, offset=2)

    result = build_search_result(request, page, snippet_chars=240)

    assert [item.evidence_id for item in result.results] == ["S1", "S2"]
    assert [item.score for item in result.results] == [1.5, 0.25]
    assert len(result.results[0].snippet) == 240
    assert result.results[0].source_path == PurePosixPath("root/guide.md")
    assert (result.total, result.count, result.offset) == (3, 2, 2)
    assert result.has_more is True
    assert result.next_offset == 4


@pytest.mark.anyio
async def test_search_store_uses_like_for_two_character_chinese_query(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    expected = _replace(store, "refund.md", "a", "退款条件为七天内提交申请。")
    _replace(store, "other.md", "b", "模型部署与推理指南。")

    result = await search_store(SearchRequest(collection="docs", query="退款"), store)

    assert result.total == 1
    assert result.results[0].source_path == expected


@pytest.mark.anyio
async def test_search_store_combines_fts_and_short_like_as_union(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    hy3_path = _replace(store, "hy3.md", "c", "Hy3 architecture and deployment notes.")
    refund_path = _replace(store, "refund.md", "d", "退款流程需要订单编号。")

    result = await search_store(SearchRequest(collection="docs", query="Hy3 退款"), store)

    assert {item.source_path for item in result.results} == {hy3_path, refund_path}


@pytest.mark.anyio
async def test_natural_chinese_question_recalls_source_through_trigrams(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    expected = _replace(store, "roadmap.md", "e", "项目的最终里程碑定于二零二六年十二月。")
    _replace(store, "distractor.md", "f", "日常会议记录与开发说明。")

    request = SearchRequest(
        collection="docs",
        query="项目的最终里程碑是什么？仅回复日期。",  # noqa: RUF001
    )
    result = await search_store(request, store)

    assert expected in {item.source_path for item in result.results}


@pytest.mark.anyio
async def test_source_filter_is_applied_after_query_matching(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    allowed = _replace(store, "allowed.md", "3", "Hy3 reference")
    _replace(store, "excluded.md", "4", "Hy3 Hy3 detailed reference")

    request = SearchRequest(
        collection="docs",
        query="Hy3",
        source_paths=(allowed,),
    )
    result = await search_store(request, store)

    assert [item.source_path for item in result.results] == [allowed]


@pytest.mark.anyio
async def test_zero_results_return_an_empty_stable_page(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    _replace(store, "guide.md", "5", "Hy3 deployment guide")

    result = await search_store(
        SearchRequest(collection="docs", query="nonexistent-token"),
        store,
    )

    assert result.total == 0
    assert result.count == 0
    assert result.results == ()
    assert result.has_more is False
    assert result.next_offset is None


@pytest.mark.anyio
async def test_stopword_plan_preserves_missing_collection_error(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()

    with pytest.raises(IndexNotFoundError, match="hy3_kb_index_documents"):
        await search_store(SearchRequest(collection="missing", query="and the is"), store)


@pytest.mark.anyio
async def test_fts_special_characters_and_sql_injection_text_are_safe(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    expected = _replace(store, "hy3.md", "7", "Hy3 is searchable")
    _replace(store, "other.md", "8", "unrelated content")

    request = SearchRequest(collection="docs", query='Hy3" OR * NEAR(foo); DROP TABLE chunks; --')
    result = await search_store(request, store)

    assert expected in {item.source_path for item in result.results}
    with store.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 2
