"""引用核验。

两级核验：
1. source_id 是否存在；
2. 若模型返回 evidence_quote，其规范化文本是否是对应来源块的子串，或达到可配置模糊匹配阈值。

不原地修改输入对象，返回带 status 的新 Citation。
"""

from __future__ import annotations

import difflib
import re
import unicodedata

from ..models import Citation, CitationStatus, SourceBlock

# 短引文低于该长度时不启用模糊匹配，避免中文误报。
FUZZY_MIN_LEN = 12
FUZZY_THRESHOLD = 0.90


def normalize_text(text: str) -> str:
    """规范化：NFKC + 压缩空白 + 去除首尾空白。"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = " ".join(text.split())
    return text.strip()


def _spaceless(text: str) -> str:
    """去除全部空白，用于空白差异不敏感的比对。"""
    return re.sub(r"\s+", "", text)


class CitationVerifier:
    def verify(self, citations: list[Citation], by_id: dict[str, SourceBlock]) -> list[Citation]:
        verified: list[Citation] = []
        for cit in citations:
            status = self._verify_one(cit, by_id)
            verified.append(
                Citation(
                    source_id=cit.source_id,
                    evidence_quote=cit.evidence_quote,
                    status=status,
                )
            )
        return verified

    def _verify_one(self, cit: Citation, by_id: dict[str, SourceBlock]) -> CitationStatus:
        source = by_id.get(cit.source_id)
        if source is None:
            return CitationStatus.FAILED

        quote = cit.evidence_quote.strip()
        if not quote:
            return CitationStatus.SOURCE_ONLY

        # 空白不敏感比对：全角/半角与空白差异（含插入/缺失空格）均可通过。
        sp_quote = _spaceless(normalize_text(quote))
        sp_source = _spaceless(normalize_text(source.text))

        if sp_quote and sp_quote in sp_source:
            return CitationStatus.VERIFIED

        # 仅当引文足够长时才允许模糊匹配，避免短中文误报。
        if len(normalize_text(quote)) >= FUZZY_MIN_LEN:
            ratio = difflib.SequenceMatcher(None, sp_quote, sp_source).ratio()
            if ratio >= FUZZY_THRESHOLD:
                return CitationStatus.VERIFIED

        return CitationStatus.FAILED
