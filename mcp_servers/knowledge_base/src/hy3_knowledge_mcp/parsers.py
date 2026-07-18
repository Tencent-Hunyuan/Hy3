"""UTF-8 文本与 PDF 知识来源解析。"""

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from io import BytesIO
from pathlib import PurePosixPath
from threading import RLock

from pypdf import PdfReader

from .errors import LimitExceededError, UnsupportedFileError
from .models import ParsedBlock, ParsedDocument, ResolvedSource, SourceFormat

MARKDOWN_SUFFIXES = {".md", ".markdown"}
FENCE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_PDF_READER_LOGGER = logging.getLogger("pypdf._reader")
_PDF_LOGGING_LOCK = RLock()


class _PdfHeaderFilter(logging.Filter):
    """仅过滤会包含来源原始字节的 PDF header 警告。"""

    def filter(self, record: logging.LogRecord) -> bool:
        """保留其他诊断日志。"""
        return record.msg != "invalid pdf header: %(header_byte)r"


_PDF_HEADER_FILTER = _PdfHeaderFilter()


@contextmanager
def _suppress_pdf_header_logging() -> Iterator[None]:
    """在构造读取器期间定向隐藏原始 header 字节。"""
    with _PDF_LOGGING_LOCK:
        _PDF_READER_LOGGER.addFilter(_PDF_HEADER_FILTER)
        try:
            yield
        finally:
            _PDF_READER_LOGGER.removeFilter(_PDF_HEADER_FILTER)


def detect_source_format(path: PurePosixPath) -> SourceFormat:
    """根据来源路径后缀识别受支持的文档格式。"""
    suffix = path.suffix.lower()
    if suffix in MARKDOWN_SUFFIXES:
        return SourceFormat.MARKDOWN
    if suffix == ".txt":
        return SourceFormat.TEXT
    if suffix == ".rst":
        return SourceFormat.RST
    if suffix == ".pdf":
        return SourceFormat.PDF
    raise UnsupportedFileError(f"Unsupported source format: {suffix or '<none>'}")


def parse_document(
    source: ResolvedSource,
    data: bytes,
    *,
    max_pdf_pages: int,
) -> ParsedDocument:
    """将已读取的来源字节解析为带定位信息的文本块。"""
    source_format = detect_source_format(source.relative_path)
    if source_format is SourceFormat.PDF:
        return _parse_pdf(data, max_pdf_pages=max_pdf_pages)
    return _parse_utf8_text(data, source_format=source_format)


def _parse_utf8_text(data: bytes, *, source_format: SourceFormat) -> ParsedDocument:
    """严格解码 UTF-8 文本并扫描连续文本块。"""
    text: str | None = None
    with suppress(UnicodeDecodeError):
        text = data.decode("utf-8-sig")
    if text is None:
        raise UnsupportedFileError("Source must be valid UTF-8")

    blocks = _scan_text_blocks(text, markdown=source_format is SourceFormat.MARKDOWN)
    if not blocks:
        raise UnsupportedFileError("Source contains no extractable text")
    return ParsedDocument(source_format=source_format, blocks=blocks)


def _scan_text_blocks(text: str, *, markdown: bool) -> tuple[ParsedBlock, ...]:
    """按空行、Markdown 标题及代码围栏扫描一基行范围。"""
    blocks: list[ParsedBlock] = []
    pending: list[str] = []
    pending_start = 0
    fence_marker: str | None = None

    def flush(line_end: int, *, hard_boundary_before: bool = False) -> None:
        nonlocal pending, pending_start
        block_text = "\n".join(pending).strip()
        if block_text:
            blocks.append(
                ParsedBlock(
                    text=block_text,
                    line_start=pending_start,
                    line_end=line_end,
                    hard_boundary_before=hard_boundary_before,
                )
            )
        pending = []
        pending_start = 0

    lines = text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        if fence_marker is not None:
            pending.append(line)
            if _is_closing_fence(line, fence_marker):
                flush(line_number)
                fence_marker = None
            continue

        if markdown:
            fence_match = FENCE_PATTERN.match(line)
            if fence_match is not None:
                if pending:
                    flush(line_number - 1)
                pending_start = line_number
                pending.append(line)
                fence_marker = fence_match.group(1)
                continue

            if HEADING_PATTERN.match(line):
                if pending:
                    flush(line_number - 1)
                pending_start = line_number
                pending.append(line)
                flush(line_number, hard_boundary_before=True)
                continue

        if not line.strip():
            if pending:
                flush(line_number - 1)
            continue

        if not pending:
            pending_start = line_number
        pending.append(line)

    if pending:
        flush(len(lines))
    return tuple(blocks)


def _is_closing_fence(line: str, opening_marker: str) -> bool:
    """判断当前行是否为同字符且长度足够的 Markdown 关闭围栏。"""
    marker_character = re.escape(opening_marker[0])
    minimum_length = len(opening_marker)
    return re.fullmatch(rf"\s*{marker_character}{{{minimum_length},}}\s*", line) is not None


def _parse_pdf(data: bytes, *, max_pdf_pages: int) -> ParsedDocument:
    """解析未加密 PDF。为每个非空页面生成独立文本块。"""
    reader: PdfReader | None = None
    with _suppress_pdf_header_logging(), suppress(Exception):
        reader = PdfReader(BytesIO(data))
    if reader is None:
        raise UnsupportedFileError("Source is not a valid PDF") from None

    is_encrypted = None
    with suppress(Exception):
        is_encrypted = reader.is_encrypted
    if is_encrypted is None:
        raise UnsupportedFileError("Source is not a valid PDF") from None
    if is_encrypted:
        raise UnsupportedFileError("Encrypted PDF sources are not supported")

    pages = None
    page_count = None
    with suppress(Exception):
        pages = reader.pages
        page_count = len(pages)
    if pages is None or page_count is None:
        raise UnsupportedFileError("Source is not a valid PDF") from None

    if page_count > max_pdf_pages:
        raise LimitExceededError("PDF exceeds HY3_KB_MAX_PDF_PAGES")

    materialized_pages = None
    with suppress(Exception):
        materialized_pages = tuple(pages)
    if materialized_pages is None:
        raise UnsupportedFileError("Source is not a valid PDF") from None

    blocks: list[ParsedBlock] = []
    for page_number, page in enumerate(materialized_pages, start=1):
        extraction_failed = False
        try:
            text = page.extract_text()
        except Exception:
            extraction_failed = True
            text = None
        if extraction_failed:
            raise UnsupportedFileError("Unable to extract PDF text")
        if text and text.strip():
            blocks.append(
                ParsedBlock(
                    text=text.strip(),
                    page_number=page_number,
                    hard_boundary_before=bool(blocks),
                )
            )

    if not blocks:
        raise UnsupportedFileError("PDF contains no extractable text")
    return ParsedDocument(
        source_format=SourceFormat.PDF,
        blocks=tuple(blocks),
        page_count=page_count,
    )
