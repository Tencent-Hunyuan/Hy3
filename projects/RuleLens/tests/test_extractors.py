"""文件解析单元测试。"""

from __future__ import annotations

import pytest

from rulelens.exceptions import (
    DocumentExtractionError,
    EmptyDocumentError,
    UnsupportedFileError,
)
from rulelens.ingestion.extractors import extract_text


# --------------------------------------------------------------------------- #
# TXT / MD
# --------------------------------------------------------------------------- #
def test_txt_read():
    doc = extract_text("a.txt", "这是一段规则文本。".encode("utf-8"))
    assert doc.full_text == "这是一段规则文本。"
    assert doc.pages[0].page_number == 1


def test_md_read():
    doc = extract_text("a.md", "# 标题\n\n正文内容。".encode("utf-8"))
    assert "正文内容" in doc.full_text


def test_utf8_bom_read():
    # 源串不含 BOM，使用 utf-8-sig 编码会写入文件级 BOM；解码应被剥离。
    raw = "这是带 BOM 的文本。".encode("utf-8-sig")
    doc = extract_text("b.md", raw)
    assert doc.full_text == "这是带 BOM 的文本。"


def test_empty_file_raises():
    with pytest.raises(EmptyDocumentError):
        extract_text("empty.txt", b"")


def test_unsupported_extension_raises():
    with pytest.raises(UnsupportedFileError):
        extract_text("x.docx", b"data")


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def _make_pdf(pages_text: list[str]) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 8, text)
    return pdf.output()


def test_pdf_preserves_pages():
    data = _make_pdf(["Page one content.", "Page two content."])
    doc = extract_text("doc.pdf", data)
    assert len(doc.pages) == 2
    assert doc.pages[0].page_number == 1
    assert doc.pages[1].page_number == 2
    assert "Page one" in doc.pages[0].text
    assert "Page two" in doc.pages[1].text


def test_pdf_no_text_layer_raises():
    # 仅画一条线，不含文本，pypdf 提取不到文本。
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_draw_color(0, 0, 0)
    pdf.line(10, 10, 100, 100)
    data = pdf.output()
    with pytest.raises(DocumentExtractionError):
        extract_text("scan.pdf", data)


def test_extract_text_returns_sha256():
    doc = extract_text("a.txt", b"hello")
    assert len(doc.file_sha256) == 64
