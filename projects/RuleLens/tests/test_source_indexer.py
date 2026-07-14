"""来源编号单元测试。"""

from __future__ import annotations

from rulelens.ingestion.extractors import PageText
from rulelens.ingestion.source_indexer import SourceIndexer


def _index(pages: list[PageText]):
    return SourceIndexer().index(pages)


def test_ids_continuous_and_unique():
    pages = [
        PageText(page_number=1, text="段落一内容。"),
        PageText(page_number=1, text="段落二内容。"),
    ]
    res = _index(pages)
    ids = [b.source_id for b in res.blocks]
    assert ids == ["S0001", "S0002"]
    assert len(set(ids)) == len(ids)


def test_page_number_preserved():
    pages = [
        PageText(page_number=1, text="第一页。"),
        PageText(page_number=3, text="第三页。"),
    ]
    res = _index(pages)
    assert res.blocks[0].page_number == 1
    assert res.blocks[1].page_number == 3


def test_long_paragraph_split():
    long_text = "。".join([f"第{i}句话内容较长用于测试拆分机制是否生效" for i in range(30)]) + "。"
    res = _index([PageText(page_number=1, text=long_text)])
    assert len(res.blocks) >= 2
    # 单个块不应过长
    assert all(len(b.text) <= 600 for b in res.blocks)
    # 拼接后的来源文本应包含原始全部内容
    for b in res.blocks:
        assert b.text in long_text


def test_short_paragraphs_merged():
    pages = [
        PageText(page_number=1, text="短句一。"),
        PageText(page_number=1, text="短句二。"),
        PageText(page_number=1, text="短句三。"),
    ]
    res = _index(pages)
    # 三句都很短，应被合并为一个来源块
    assert len(res.blocks) == 1
    assert "短句一" in res.blocks[0].text and "短句三" in res.blocks[0].text


def test_all_content_reachable():
    pages = [PageText(page_number=1, text="苹果。香蕉。橙子。")]
    res = _index(pages)
    combined = " ".join(b.text for b in res.blocks)
    assert "苹果" in combined and "香蕉" in combined and "橙子" in combined


def test_indexed_text_includes_ids():
    pages = [PageText(page_number=2, text="示例文本。")]
    res = _index(pages)
    assert "[S0001|page=2]" in res.indexed_text
