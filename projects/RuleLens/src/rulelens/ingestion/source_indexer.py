"""来源编号（Source Indexing）。

将解析后的页 / 段文本切分为可引用的来源块，并为模型生成带来源编号的文本。
切分规则：
- 优先按自然段切分；
- 单块目标长度 150～600 字符；
- 极长段落按句号 / 分号 / 换行继续拆分；
- 极短且连续的行可以合并；
- 每个块保存 source_id、page_number、text 与字符区间。
"""

from __future__ import annotations

from pydantic import BaseModel

from ..models import SourceBlock
from .extractors import PageText

TARGET_MIN = 150
TARGET_MAX = 600
# 仅当相邻行极短（<5 字）且合并后整体仍较小（<=MERGE_MAX）时才合并。
SHORT_MERGE = 5
MERGE_MAX = 60
_SENTENCE_DELIMS = "。；！？\n"


class IndexedResult(BaseModel):
    blocks: list[SourceBlock]
    indexed_text: str

    @property
    def by_id(self) -> dict[str, SourceBlock]:
        return {b.source_id: b for b in self.blocks}


class SourceIndexer:
    def _clean(self, text: str) -> str:
        text = text.replace("\u3000", " ")  # 全角空格 -> 半角
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\t", " ")
        # 压缩连续空白（保留换行）
        lines = ["" if not ln.strip() else " ".join(ln.split()) for ln in text.split("\n")]
        return "\n".join(lines).strip()

    def _split_paragraphs(self, cleaned: str) -> list[str]:
        paras: list[str] = []
        for raw in cleaned.split("\n"):
            if not raw.strip():
                continue
            paras.append(raw.strip())
        return paras

    def _bisect(self, text: str, min_len: int, max_len: int) -> tuple[str, str]:
        """在 [min_len, max_len] 内寻找句末标点进行切分，找不到则硬切。"""
        best = -1
        for i, ch in enumerate(text):
            if i > max_len:
                break
            if i >= min_len and ch in _SENTENCE_DELIMS:
                best = i + 1
                break
        if best == -1:
            split = min(max_len, max(1, len(text) - 1))
            return text[:split], text[split:]
        return text[:best], text[best:]

    def _build_chunks(self, paragraphs: list[str]) -> list[str]:
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            while len(current) > TARGET_MAX:
                head, current = self._bisect(current, TARGET_MIN, TARGET_MAX)
                if head:
                    chunks.append(head)
            if not current:
                current = para
            elif len(para) < SHORT_MERGE and (len(current) + len(para) + 1 <= MERGE_MAX):
                current = current + "\n" + para
            else:
                chunks.append(current)
                current = para
        while len(current) > TARGET_MAX:
            head, current = self._bisect(current, TARGET_MIN, TARGET_MAX)
            if head:
                chunks.append(head)
        if current:
            chunks.append(current)
        return chunks

    def index(self, pages: list[PageText]) -> IndexedResult:
        # 按页码分组，合并同一页内的连续短行，同时保留页边界。
        from collections import OrderedDict

        by_page: "OrderedDict[int, list[str]]" = OrderedDict()
        for page in pages:
            cleaned = self._clean(page.text)
            if not cleaned:
                continue
            for para in self._split_paragraphs(cleaned):
                by_page.setdefault(page.page_number, []).append(para)

        blocks: list[SourceBlock] = []
        indexed_parts: list[str] = []
        cursor = 0

        for page_number, paras in by_page.items():
            for chunk in self._build_chunks(paras):
                chunk = chunk.strip()
                if not chunk:
                    continue
                source_id = f"S{len(blocks) + 1:04d}"
                prefix = f"[{source_id}|page={page_number}] "
                if indexed_parts:
                    indexed_parts.append("")
                    cursor += 1
                line = prefix + chunk
                start = cursor
                indexed_parts.append(line)
                cursor += len(line)
                blocks.append(
                    SourceBlock(
                        source_id=source_id,
                        page_number=page_number,
                        text=chunk,
                        char_start=start + len(prefix),
                        char_end=start + len(prefix) + len(chunk),
                    )
                )

        indexed_text = "\n".join(indexed_parts)
        return IndexedResult(blocks=blocks, indexed_text=indexed_text)
