"""引用核验单元测试。"""

from __future__ import annotations

from rulelens.models import Citation, CitationStatus, SourceBlock
from rulelens.services.citation_verifier import CitationVerifier


def _by_id():
    return {
        "S0001": SourceBlock(
            source_id="S0001",
            page_number=1,
            text="报名截止时间为2026年4月30日。",
            char_start=0,
            char_end=10,
        )
    }


def test_verified():
    v = CitationVerifier()
    out = v.verify(
        [Citation(source_id="S0001", evidence_quote="报名截止时间为2026年4月30日。")], _by_id()
    )
    assert out[0].status == CitationStatus.VERIFIED


def test_source_only():
    v = CitationVerifier()
    out = v.verify([Citation(source_id="S0001", evidence_quote="")], _by_id())
    assert out[0].status == CitationStatus.SOURCE_ONLY


def test_missing_source_failed():
    v = CitationVerifier()
    out = v.verify([Citation(source_id="S9999", evidence_quote="任意")], _by_id())
    assert out[0].status == CitationStatus.FAILED


def test_rewritten_quote_failed():
    v = CitationVerifier()
    out = v.verify([Citation(source_id="S0001", evidence_quote="报名截止时间是五月一日")], _by_id())
    assert out[0].status == CitationStatus.FAILED


def test_whitespace_and_fullwidth_pass():
    v = CitationVerifier()
    # 全角空格与连续空白差异应被规范化后通过
    out = v.verify(
        [Citation(source_id="S0001", evidence_quote="报名截止时间为 2026 年 4 月 30 日。")],
        _by_id(),
    )
    assert out[0].status == CitationStatus.VERIFIED


def test_short_chinese_no_fuzzy_misjudge():
    v = CitationVerifier()
    # 短中文引文（<12 字）明显改写，不应误判为模糊通过
    out = v.verify([Citation(source_id="S0001", evidence_quote="截止时间是明天")], _by_id())
    assert out[0].status == CitationStatus.FAILED


def test_does_not_mutate_input():
    v = CitationVerifier()
    cit = Citation(source_id="S0001", evidence_quote="报名截止时间为2026年4月30日。")
    v.verify([cit], _by_id())
    assert cit.status is None
