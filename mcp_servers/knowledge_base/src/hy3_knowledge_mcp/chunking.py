"""按段落、标题和 PDF 页边界安全分块。"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import LimitExceededError
from .models import ChunkDraft, ParsedBlock, ParsedDocument, SourceFormat

_SEPARATOR = "\n\n"
_MATERIALIZATION_MULTIPLIER = 32
_MIN_MATERIALIZATION_CHARS = 64 * 1024


@dataclass(frozen=True)
class _Piece:
    """一段连续文本及其可证明的来源位置。"""

    text: str
    page_number: int | None
    line_start: int | None
    line_end: int | None
    is_source: bool = True


def _slice_piece(piece: _Piece, start: int, end: int) -> _Piece:
    """切取 piece。仅在可计算时保留精确行范围。"""
    text = piece.text[start:end]
    line_start = None
    line_end = None
    if piece.line_start is not None and piece.line_end is not None:
        line_start = piece.line_start + piece.text[:start].count("\n")
        line_end = piece.line_start + piece.text[: end - 1].count("\n")
    return _Piece(
        text=text,
        page_number=piece.page_number,
        line_start=line_start,
        line_end=line_end,
        is_source=piece.is_source,
    )


def _join(pieces: list[_Piece]) -> str:
    """连接已显式包含分隔符的 pieces。"""
    return "".join(piece.text for piece in pieces)


def _slice_pieces(pieces: list[_Piece], start: int, end: int) -> list[_Piece]:
    """按合并文本的字符范围切取 pieces。"""
    sliced: list[_Piece] = []
    position = 0
    for piece in pieces:
        piece_end = position + len(piece.text)
        local_start = max(start - position, 0)
        local_end = min(end - position, len(piece.text))
        if local_start < local_end:
            sliced.append(_slice_piece(piece, local_start, local_end))
        position = piece_end
        if position >= end:
            break
    return sliced


def _trim(pieces: list[_Piece]) -> list[_Piece]:
    """移除会被严格模型裁掉的首尾空白并保留 piece 元数据。"""
    text = _join(pieces)
    trimmed = text.strip()
    if not trimmed:
        return []
    start = len(text) - len(text.lstrip())
    return _slice_pieces(pieces, start, start + len(trimmed))


def _tail(pieces: list[_Piece], overlap_chars: int) -> list[_Piece]:
    """保留精确的末尾字符及其来源元数据。"""
    if overlap_chars == 0:
        return []

    remaining = overlap_chars
    tail: list[_Piece] = []
    for piece in reversed(pieces):
        if remaining == 0:
            break
        take = min(remaining, len(piece.text))
        tail.append(_slice_piece(piece, len(piece.text) - take, len(piece.text)))
        remaining -= take
    tail.reverse()
    return tail


def _carry(pieces: list[_Piece], overlap_chars: int) -> list[_Piece]:
    """提取不会在下一块开头被严格模型裁掉的自适应 carry。"""
    return _trim(_tail(pieces, overlap_chars))


def _starts_hard_boundary(
    document: ParsedDocument,
    block: ParsedBlock,
    previous_page_number: int | None,
    has_previous_block: bool,
) -> bool:
    """统一判断显式硬边界和 PDF 换页边界。"""
    return block.hard_boundary_before or (
        has_previous_block
        and document.source_format is SourceFormat.PDF
        and block.page_number != previous_page_number
    )


def _logical_input_chars(document: ParsedDocument) -> int:
    """计算实际会进入分块流的来源字符与普通块分隔符。"""
    total = 0
    previous_page_number: int | None = None
    has_previous_block = False
    for block in document.blocks:
        if has_previous_block and not _starts_hard_boundary(
            document,
            block,
            previous_page_number,
            has_previous_block,
        ):
            total += len(_SEPARATOR)
        total += len(block.text)
        previous_page_number = block.page_number
        has_previous_block = True
    return total


def _to_chunk(ordinal: int, pieces: list[_Piece]) -> ChunkDraft:
    """将非空 pieces 转换为带保守定位信息的分块。"""
    text = _join(pieces)
    source_pieces = [piece for piece in pieces if piece.is_source]
    pages = {piece.page_number for piece in source_pieces}
    has_exact_lines = bool(source_pieces) and all(
        piece.line_start is not None and piece.line_end is not None for piece in source_pieces
    )
    return ChunkDraft(
        ordinal=ordinal,
        text=text,
        page_number=pages.pop() if len(pages) == 1 else None,
        line_start=(
            min(piece.line_start for piece in source_pieces if piece.line_start is not None)
            if has_exact_lines
            else None
        ),
        line_end=(
            max(piece.line_end for piece in source_pieces if piece.line_end is not None)
            if has_exact_lines
            else None
        ),
        char_count=len(text),
    )


def chunk_document(
    document: ParsedDocument,
    *,
    max_chars: int,
    overlap_chars: int,
) -> tuple[ChunkDraft, ...]:
    """生成不跨硬边界、长度受限且带精确字符重叠的分块。"""
    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Require 0 <= overlap_chars < max_chars")

    chunks: list[ChunkDraft] = []
    current: list[_Piece] = []
    previous_page_number: int | None = None
    has_previous_block = False
    input_chars = _logical_input_chars(document)
    # 限制 overlap 导致的重复物化。保留常规文档足够余量并阻止资源放大。
    materialization_limit = max(
        _MIN_MATERIALIZATION_CHARS,
        max_chars,
        input_chars * _MATERIALIZATION_MULTIPLIER,
    )
    materialized_chars = 0

    def flush(*, carry_overlap: bool) -> None:
        nonlocal current, materialized_chars
        normalized = _trim(current)
        if not normalized:
            current = []
            return
        text = _join(normalized)
        overlap_only = (
            carry_overlap
            and bool(chunks)
            and len(text) <= overlap_chars
            and chunks[-1].text.endswith(text)
        )
        if not overlap_only:
            projected_chars = materialized_chars + len(text)
            if projected_chars > materialization_limit:
                raise LimitExceededError("Chunk materialization limit exceeded")
            chunks.append(_to_chunk(len(chunks), normalized))
            materialized_chars = projected_chars
        current = _carry(normalized, overlap_chars) if carry_overlap else []

    def append_piece(piece: _Piece) -> None:
        nonlocal current
        offset = 0
        while offset < len(piece.text):
            current_length = len(_join(current))
            if current_length == max_chars:
                flush(carry_overlap=True)
                current_length = len(_join(current))

            if piece.text[offset].isspace():
                whitespace_end = offset
                while whitespace_end < len(piece.text) and piece.text[whitespace_end].isspace():
                    whitespace_end += 1
                if whitespace_end < len(piece.text):
                    whitespace_length = whitespace_end - offset
                    content_end = whitespace_end
                    while content_end < len(piece.text) and not piece.text[content_end].isspace():
                        content_end += 1
                    content_length = content_end - whitespace_end
                    representable_content = min(
                        content_length,
                        max_chars - whitespace_length - 1,
                    )
                    if representable_content > 0:
                        allowed_carry = max_chars - whitespace_length - representable_content
                        if current_length > allowed_carry:
                            current = _carry(current, allowed_carry)
                            current_length = len(_join(current))
                    else:
                        whitespace_capacity = max_chars - current_length - 1
                        if whitespace_length > whitespace_capacity:
                            offset += whitespace_length - whitespace_capacity

            take = min(max_chars - current_length, len(piece.text) - offset)
            candidate = piece.text[offset : offset + take]
            if offset + take < len(piece.text) and candidate[-1].isspace():
                content_length = len(candidate.rstrip())
                if content_length:
                    current.append(_slice_piece(piece, offset, offset + content_length))
                    offset += content_length
                    flush(carry_overlap=True)
                    continue
            current.append(_slice_piece(piece, offset, offset + take))
            offset += take

    for block in document.blocks:
        hard_boundary = _starts_hard_boundary(
            document,
            block,
            previous_page_number,
            has_previous_block,
        )
        if hard_boundary:
            flush(carry_overlap=False)

        block_piece = _Piece(
            text=block.text,
            page_number=block.page_number,
            line_start=block.line_start,
            line_end=block.line_end,
        )
        separator_piece = _Piece(
            text=_SEPARATOR,
            page_number=None,
            line_start=None,
            line_end=None,
            is_source=False,
        )

        if current:
            candidate_length = len(_join(current)) + len(_SEPARATOR) + len(block.text)
            if candidate_length <= max_chars:
                current.extend((separator_piece, block_piece))
            else:
                flush(carry_overlap=True)
                # 分隔符必须位于两个非空白字符之间。否则严格模型会裁掉边界空白。
                separator_carry = max_chars - len(_SEPARATOR) - 1
                if current and separator_carry > 0:
                    current = _carry(current, separator_carry)
                    append_piece(separator_piece)
                append_piece(block_piece)
        else:
            append_piece(block_piece)
        previous_page_number = block.page_number
        has_previous_block = True

    flush(carry_overlap=False)
    assert all(chunk.char_count <= max_chars for chunk in chunks)
    return tuple(chunks)
