"""本地知识来源解析测试。"""

import logging
from io import BytesIO
from pathlib import Path, PurePosixPath

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from reportlab.pdfgen import canvas

from hy3_knowledge_mcp import parsers
from hy3_knowledge_mcp.errors import LimitExceededError, UnsupportedFileError
from hy3_knowledge_mcp.models import ResolvedSource, SourceFormat
from hy3_knowledge_mcp.parsers import detect_source_format, parse_document


def make_source(path: Path) -> ResolvedSource:
    """根据真实文件元数据构造已解析来源。"""
    metadata = path.stat()
    return ResolvedSource(
        absolute_path=path,
        root_path=path.parent,
        root_id="0123456789ab",
        relative_path=PurePosixPath(path.name),
        source_path=PurePosixPath(path.name),
        size_bytes=metadata.st_size,
        mtime_ns=metadata.st_mtime_ns,
        device_id=metadata.st_dev,
        file_id=metadata.st_ino,
    )


def make_pdf(*pages: str) -> bytes:
    """生成每个字符串占一页的测试 PDF。"""
    output = BytesIO()
    document = canvas.Canvas(output)
    for page in pages:
        document.drawString(72, 720, page)
        document.showPage()
    document.save()
    return output.getvalue()


def make_pdf_without_pages() -> bytes:
    """生成有 Catalog 但缺少 /Pages 的最小 PDF。"""
    header = b"%PDF-1.4\n"
    catalog = b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    xref_offset = len(header) + len(catalog)
    return (
        header
        + catalog
        + b"xref\n0 2\n0000000000 65535 f \n"
        + f"{len(header):010d} 00000 n \n".encode()
        + b"trailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    (
        ("guide.md", SourceFormat.MARKDOWN),
        ("guide.MARKDOWN", SourceFormat.MARKDOWN),
        ("notes.txt", SourceFormat.TEXT),
        ("reference.rst", SourceFormat.RST),
        ("paper.PDF", SourceFormat.PDF),
    ),
)
def test_detect_source_format_supports_known_suffixes(
    path: str,
    expected: SourceFormat,
) -> None:
    """已支持的文件后缀映射到对应来源格式。"""
    assert detect_source_format(PurePosixPath(path)) is expected


def test_parse_markdown_preserves_headings_paragraphs_fence_and_lines(tmp_path: Path) -> None:
    """Markdown 标题、段落和代码围栏形成带行号的独立块。"""
    path = tmp_path / "guide.md"
    data = (
        b"# Guide\n\nFirst line\nsecond line\n\n"
        b"```python\n# not a heading\nprint('ok')\n```\n\n## Next\n"
    )
    path.write_bytes(data)

    result = parse_document(make_source(path), data, max_pdf_pages=10)

    assert result.source_format is SourceFormat.MARKDOWN
    assert result.page_count is None
    assert [block.model_dump() for block in result.blocks] == [
        {
            "text": "# Guide",
            "page_number": None,
            "line_start": 1,
            "line_end": 1,
            "hard_boundary_before": True,
        },
        {
            "text": "First line\nsecond line",
            "page_number": None,
            "line_start": 3,
            "line_end": 4,
            "hard_boundary_before": False,
        },
        {
            "text": "```python\n# not a heading\nprint('ok')\n```",
            "page_number": None,
            "line_start": 6,
            "line_end": 9,
            "hard_boundary_before": False,
        },
        {
            "text": "## Next",
            "page_number": None,
            "line_start": 11,
            "line_end": 11,
            "hard_boundary_before": True,
        },
    ]


@pytest.mark.parametrize(
    ("filename", "expected_format"),
    (("notes.txt", SourceFormat.TEXT), ("reference.rst", SourceFormat.RST)),
)
def test_parse_text_accepts_utf8_bom_and_crlf(
    tmp_path: Path,
    filename: str,
    expected_format: SourceFormat,
) -> None:
    """纯文本格式接受 UTF-8 BOM 与 CRLF。保留一基行号。"""
    path = tmp_path / filename
    data = b"\xef\xbb\xbfFirst\r\nline\r\n\r\nSecond\r\n"
    path.write_bytes(data)

    result = parse_document(make_source(path), data, max_pdf_pages=10)

    assert result.source_format is expected_format
    assert [(block.text, block.line_start, block.line_end) for block in result.blocks] == [
        ("First\nline", 1, 2),
        ("Second", 4, 4),
    ]


def test_parse_text_rejects_invalid_utf8(tmp_path: Path) -> None:
    """无效 UTF-8 不会被替换或静默接受。"""
    path = tmp_path / "notes.txt"
    data = b"valid\xffinvalid"
    path.write_bytes(data)

    with pytest.raises(UnsupportedFileError, match="UTF-8") as exc_info:
        parse_document(make_source(path), data, max_pdf_pages=10)

    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None


@pytest.mark.parametrize("filename", ("blank.txt", "blank.rst", "blank.md"))
def test_parse_text_rejects_blank_documents(tmp_path: Path, filename: str) -> None:
    """只含空白的文本来源没有可提取内容。"""
    path = tmp_path / filename
    data = b" \r\n\t\r\n"
    path.write_bytes(data)

    with pytest.raises(UnsupportedFileError, match=r"^Source contains no extractable text$"):
        parse_document(make_source(path), data, max_pdf_pages=10)


def test_parse_pdf_extracts_non_empty_pages_and_page_boundaries(tmp_path: Path) -> None:
    """PDF 逐页提取文本并记录实际页数和硬分页。"""
    path = tmp_path / "paper.pdf"
    data = make_pdf("Page one", "Page two")
    path.write_bytes(data)

    result = parse_document(make_source(path), data, max_pdf_pages=2)

    assert result.source_format is SourceFormat.PDF
    assert result.page_count == 2
    assert [(block.text.strip(), block.page_number) for block in result.blocks] == [
        ("Page one", 1),
        ("Page two", 2),
    ]
    assert [block.hard_boundary_before for block in result.blocks] == [False, True]
    assert all(block.line_start is None and block.line_end is None for block in result.blocks)


def test_parse_pdf_rejects_page_count_over_limit(tmp_path: Path) -> None:
    """PDF 页数超过配置上限时停止解析。"""
    path = tmp_path / "paper.pdf"
    data = make_pdf("One", "Two")
    path.write_bytes(data)

    with pytest.raises(LimitExceededError, match=r"^PDF exceeds HY3_KB_MAX_PDF_PAGES$"):
        parse_document(make_source(path), data, max_pdf_pages=1)


def test_parse_pdf_rejects_encrypted_document(tmp_path: Path) -> None:
    """加密 PDF 不尝试解密或提取。"""
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt("secret")
    writer.write(output)
    path = tmp_path / "encrypted.pdf"
    data = output.getvalue()
    path.write_bytes(data)

    with pytest.raises(
        UnsupportedFileError,
        match=r"^Encrypted PDF sources are not supported$",
    ):
        parse_document(make_source(path), data, max_pdf_pages=10)


def test_parse_pdf_rejects_malformed_document(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """损坏的 PDF 被映射为稳定异常。日志不暴露原始字节。"""
    path = tmp_path / "broken.pdf"
    data = b"SECRET source bytes that are not a PDF"
    path.write_bytes(data)

    with pytest.raises(PdfReadError):
        PdfReader(BytesIO(data))
    assert "invalid pdf header" in caplog.text
    assert "SECRE" in caplog.text
    caplog.clear()

    with pytest.raises(UnsupportedFileError, match=r"^Source is not a valid PDF$") as exc_info:
        parse_document(make_source(path), data, max_pdf_pages=10)

    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None
    assert "invalid pdf header" not in caplog.text
    assert "SECRE" not in caplog.text
    assert parsers._PDF_HEADER_FILTER not in logging.getLogger("pypdf._reader").filters


def test_parse_pdf_maps_reader_runtime_errors_and_restores_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """读取器普通异常被脱敏映射。日志过滤器总会移除。"""

    def fail_reader(_stream: BytesIO) -> None:
        raise RuntimeError("sensitive reader failure")

    path = tmp_path / "paper.pdf"
    data = b"placeholder"
    path.write_bytes(data)
    monkeypatch.setattr(parsers, "PdfReader", fail_reader)

    with pytest.raises(UnsupportedFileError, match=r"^Source is not a valid PDF$") as exc_info:
        parse_document(make_source(path), data, max_pdf_pages=10)

    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None
    assert parsers._PDF_HEADER_FILTER not in logging.getLogger("pypdf._reader").filters


def test_parse_pdf_rejects_document_without_extractable_text(tmp_path: Path) -> None:
    """只有空白页的 PDF 没有可提取文本。"""
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(output)
    path = tmp_path / "blank.pdf"
    data = output.getvalue()
    path.write_bytes(data)

    with pytest.raises(UnsupportedFileError, match=r"^PDF contains no extractable text$"):
        parse_document(make_source(path), data, max_pdf_pages=10)
