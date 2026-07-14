"""文档解析：根据扩展名选择提取器，统一为「页 / 段」文本对象。

支持：
- `.pdf`：使用 pypdf 按页提取文本（保留页码信息）；
- `.txt` / `.md`：按 UTF-8-SIG 回退到 UTF-8 读取；

解析异常统一转换为 :mod:`rulelens.exceptions` 中的项目异常。
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from pydantic import BaseModel

from ..exceptions import (
    DocumentExtractionError,
    EmptyDocumentError,
    UnsupportedFileError,
)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}

# 单页文本低于该长度（去除空白后）视为空页，不计入。
_MIN_PAGE_CHARS = 1


class PageText(BaseModel):
    page_number: int  # 1-based
    text: str


class ExtractedDocument(BaseModel):
    file_name: str
    full_text: str
    pages: list[PageText]
    file_sha256: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_text_bytes(raw: bytes) -> str:
    """尝试 UTF-8-SIG，再回退 UTF-8。"""
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    # 最后兜底 latin-1（不会抛错），但上层会因内容为空/乱码进一步处理。
    return raw.decode("latin-1", errors="replace")


def _extract_pdf(raw: bytes) -> list[PageText]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001 - 包裹为项目异常
        raise DocumentExtractionError(
            f"PDF 解析失败：{exc}", user_message="PDF 解析失败，请确认文件未损坏。"
        ) from exc

    if not reader.pages:
        raise EmptyDocumentError(user_message="PDF 没有页面内容，请检查文件。")

    pages: list[PageText] = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - 单页失败不应中断整体
            text = ""
        text = text.strip()
        if len(text) >= _MIN_PAGE_CHARS:
            pages.append(PageText(page_number=idx, text=text))

    if not pages:
        raise DocumentExtractionError(
            user_message=(
                "未在 PDF 中检测到可提取的文本层。当前版本不支持 OCR，"
                "请上传含文本层的 PDF，或转换为 TXT / MD 后上传。"
            )
        )
    return pages


def _extract_text_file(raw: bytes) -> list[PageText]:
    text = _read_text_bytes(raw).strip()
    if not text:
        raise EmptyDocumentError(user_message="文档内容为空或无法解码为文本，请检查文件编码。")
    return [PageText(page_number=1, text=text)]


def extract_text(file_name: str, file_bytes: bytes) -> ExtractedDocument:
    """解析文档并返回统一的提取结果。

    :raises UnsupportedFileError: 扩展名不支持
    :raises DocumentExtractionError: PDF 无文本层或损坏
    :raises EmptyDocumentError: 文本为空
    """
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(
            f"不支持的扩展名：{suffix}",
            user_message="不支持的文件类型，请上传 PDF、Markdown 或 TXT 文件。",
        )

    if suffix == ".pdf":
        pages = _extract_pdf(file_bytes)
    else:
        pages = _extract_text_file(file_bytes)

    full_text = "\n\n".join(p.text for p in pages)
    return ExtractedDocument(
        file_name=file_name,
        full_text=full_text,
        pages=pages,
        file_sha256=_sha256(file_bytes),
    )
