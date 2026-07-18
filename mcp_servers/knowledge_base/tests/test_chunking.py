"""知识文档分块测试。"""

from itertools import pairwise

import pytest

from hy3_knowledge_mcp import chunking
from hy3_knowledge_mcp.chunking import chunk_document
from hy3_knowledge_mcp.errors import LimitExceededError
from hy3_knowledge_mcp.models import ChunkDraft, ParsedBlock, ParsedDocument, SourceFormat


def make_document(
    *blocks: ParsedBlock,
    source_format: SourceFormat = SourceFormat.TEXT,
    page_count: int | None = None,
) -> ParsedDocument:
    """构造用于分块的解析文档。"""
    return ParsedDocument(
        source_format=source_format,
        blocks=blocks,
        page_count=page_count,
    )


def reconstruct_chunks(chunks: tuple[ChunkDraft, ...], overlap_chars: int) -> str:
    """校验最终输出的精确重叠并重建去重叠文本。"""
    reconstructed = chunks[0].text
    for left, right in pairwise(chunks):
        actual_overlap = next(
            (
                size
                for size in range(min(overlap_chars, len(left.text)), 0, -1)
                if right.text.startswith(left.text[-size:])
            ),
            0,
        )
        reconstructed += right.text[actual_overlap:]
    return reconstructed


@pytest.mark.parametrize(
    ("max_chars", "overlap_chars"),
    ((0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)),
)
def test_chunk_document_rejects_invalid_limits(max_chars: int, overlap_chars: int) -> None:
    """分块上限与重叠量必须形成可前进的有效窗口。"""
    with pytest.raises(ValueError, match=r"^Require 0 <= overlap_chars < max_chars$"):
        chunk_document(make_document(), max_chars=max_chars, overlap_chars=overlap_chars)


def test_empty_document_has_no_chunks() -> None:
    """空文档不会生成空分块。"""
    assert chunk_document(make_document(), max_chars=10, overlap_chars=3) == ()


def test_chunks_stay_within_limit_and_ordinals_are_contiguous() -> None:
    """普通块溢出时携带精确重叠。序号与长度保持不变量。"""
    document = make_document(
        ParsedBlock(text="A" * 30, line_start=1, line_end=1),
        ParsedBlock(text="B" * 30, line_start=3, line_end=3),
    )

    chunks = chunk_document(document, max_chars=40, overlap_chars=5)

    assert [chunk.text for chunk in chunks] == ["A" * 30, "A" * 5 + "\n\n" + "B" * 30]
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.char_count == len(chunk.text) <= 40 for chunk in chunks)


def test_separator_counts_toward_chunk_limit() -> None:
    """块间双换行分隔符计入最大字符数。"""
    document = make_document(
        ParsedBlock(text="A" * 6, line_start=1, line_end=1),
        ParsedBlock(text="B" * 6, line_start=3, line_end=3),
    )

    chunks = chunk_document(document, max_chars=10, overlap_chars=2)

    assert [chunk.text for chunk in chunks] == ["A" * 6, "AA\n\n" + "B" * 6]
    assert [chunk.char_count for chunk in chunks] == [6, 10]


def test_heading_starts_a_new_chunk_without_overlap() -> None:
    """标题硬边界会先 flush。新块不继承旧章节重叠文本。"""
    document = make_document(
        ParsedBlock(text="old section", line_start=1, line_end=1),
        ParsedBlock(
            text="## New section",
            line_start=3,
            line_end=3,
            hard_boundary_before=True,
        ),
        source_format=SourceFormat.MARKDOWN,
    )

    chunks = chunk_document(document, max_chars=100, overlap_chars=10)

    assert [chunk.text for chunk in chunks] == ["old section", "## New section"]


def test_pdf_chunks_never_cross_pages() -> None:
    """PDF 长页面可页内重叠。任何分块都不跨页。"""
    document = make_document(
        ParsedBlock(text="0123456789AB", page_number=1),
        ParsedBlock(
            text="abcdefghijkl",
            page_number=2,
        ),
        source_format=SourceFormat.PDF,
        page_count=2,
    )

    chunks = chunk_document(document, max_chars=10, overlap_chars=3)

    assert [(chunk.page_number, chunk.text) for chunk in chunks] == [
        (1, "0123456789"),
        (1, "789AB"),
        (2, "abcdefghij"),
        (2, "hijkl"),
    ]
    assert all(chunk.line_start is None and chunk.line_end is None for chunk in chunks)


def test_long_single_block_advances_with_exact_overlap() -> None:
    """超长单块按窗口前进。普通分块间保留精确重叠。"""
    document = make_document(
        ParsedBlock(text="0123456789ABCDEF", line_start=1, line_end=1),
    )

    chunks = chunk_document(document, max_chars=10, overlap_chars=3)

    assert [chunk.text for chunk in chunks] == ["0123456789", "789ABCDEF"]


@pytest.mark.parametrize("text", ("abcd efgh", "abcd\nefgh", "abcd\t efgh", "a aa"))
def test_whitespace_at_window_boundary_preserves_final_chunk_invariants(text: str) -> None:
    """窗口边界空白不会被模型二次裁剪而破坏长度或重叠。"""
    document = make_document(ParsedBlock(text=text, line_start=1, line_end=2))

    chunks = chunk_document(document, max_chars=5, overlap_chars=2)

    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.char_count == len(chunk.text) <= 5 for chunk in chunks)
    assert all(chunk.text for chunk in chunks)
    reconstructed = reconstruct_chunks(chunks, 2)
    assert reconstructed == text


def test_materialization_budget_rejects_extreme_overlap_before_large_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """直接调用的极端 overlap 在物化大量重复文本前稳定拒绝。"""
    document = make_document(ParsedBlock(text="A" * 10_000))
    original_to_chunk = chunking._to_chunk
    calls = 0

    def counting_to_chunk(ordinal: int, pieces: list[chunking._Piece]) -> ChunkDraft:
        nonlocal calls
        calls += 1
        if calls > 1_000:
            raise AssertionError("分块预算未能及时拒绝")
        return original_to_chunk(ordinal, pieces)

    monkeypatch.setattr(chunking, "_to_chunk", counting_to_chunk)

    with pytest.raises(LimitExceededError, match=r"^Chunk materialization limit exceeded$"):
        chunk_document(document, max_chars=501, overlap_chars=500)

    assert calls < 1_000


def test_materialization_budget_allows_small_high_overlap_document() -> None:
    """直接调用的小型高 overlap 文档不被保守预算误拒。"""
    document = make_document(ParsedBlock(text="abcdef"))

    chunks = chunk_document(document, max_chars=5, overlap_chars=4)

    assert [chunk.text for chunk in chunks] == ["abcde", "bcdef"]


@pytest.mark.parametrize("boundary_kind", ("hard", "pdf"))
def test_hard_boundaries_do_not_inflate_materialization_allowance(
    boundary_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """硬边界和 PDF 换页不以未物化 separator 扩大重复预算。"""
    if boundary_kind == "pdf":
        blocks = (
            *(ParsedBlock(text="A", page_number=page_number) for page_number in range(1, 1_001)),
            ParsedBlock(text="B" * 10_000, page_number=1_001),
        )
        document = make_document(
            *blocks,
            source_format=SourceFormat.PDF,
            page_count=1_001,
        )
    else:
        blocks = tuple(ParsedBlock(text="A", hard_boundary_before=True) for _ in range(1_000))
        document = make_document(
            *blocks,
            ParsedBlock(text="B" * 10_000, hard_boundary_before=True),
        )

    original_to_chunk = chunking._to_chunk
    calls = 0

    def counting_to_chunk(ordinal: int, pieces: list[chunking._Piece]) -> ChunkDraft:
        nonlocal calls
        calls += 1
        if calls > 1_750:
            raise AssertionError("硬边界虚增了分块预算")
        return original_to_chunk(ordinal, pieces)

    monkeypatch.setattr(chunking, "_to_chunk", counting_to_chunk)

    with pytest.raises(LimitExceededError, match=r"^Chunk materialization limit exceeded$"):
        chunk_document(document, max_chars=501, overlap_chars=500)

    assert calls < 1_750
