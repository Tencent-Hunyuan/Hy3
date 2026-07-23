"""Tests for hy3research.fetcher."""

import pytest
from hy3research.fetcher import extract_text, fetch_all


class TestExtractText:
    def test_extracts_text_from_html(self):
        html = "<html><head><script>console.log('x')</script><style>body{}</style></head><body><p>Hello World</p><p>More text here.</p></body></html>"
        text = extract_text(html)
        assert "Hello World" in text
        assert "More text" in text
        assert "console.log" not in text

    def test_strips_extra_whitespace(self):
        html = "<html><body><p>  Lots   of   spaces  </p></body></html>"
        text = extract_text(html)
        assert "Lots of spaces" in text


class TestFetchAll:
    def test_mock_returns_structured_data(self):
        sources = [
            {"url": "https://example.com/a", "title": "Article A", "index": 1, "query": "test"},
            {"url": "https://example.com/b", "title": "Article B", "index": 2, "query": "test2"},
        ]
        results = fetch_all(sources, mock=True)
        assert len(results) == 2
        for r in results:
            assert r["fetch_status"] in ("ok", "failed", "skipped")
            assert "raw_text" in r
            assert "fetch_time" in r
            assert isinstance(r["fetch_time"], (int, float))

    def test_mock_text_is_substantial(self):
        sources = [
            {"url": "https://example.com/a", "title": "Test", "index": 1, "query": "x"},
        ]
        results = fetch_all(sources, mock=True)
        assert len(results[0]["raw_text"]) > 100
