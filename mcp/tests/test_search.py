from __future__ import annotations

import duckduckgo_search

from hy3_deep_research.config import Config
from hy3_deep_research.tools.search import search_web_impl


def _make_config(tavily_key=None) -> Config:
    return Config(hunyuan_api_key="k", tavily_api_key=tavily_key)


class _FakeDDGS:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, max_results=5):
        return [
            {"title": f"Result {i}", "href": f"https://example.com/{i}", "body": f"Snippet {i}"}
            for i in range(min(max_results, 3))
        ]


def test_search_returns_unified_format(monkeypatch):
    monkeypatch.setattr(duckduckgo_search, "DDGS", _FakeDDGS)
    results = search_web_impl("tencent hy3", 3, _make_config())
    assert len(results) == 3
    for r in results:
        assert set(r.keys()) == {"title", "url", "snippet"}
        assert r["url"].startswith("https://example.com/")


def test_search_clamps_max_results(monkeypatch):
    monkeypatch.setattr(duckduckgo_search, "DDGS", _FakeDDGS)
    results = search_web_impl("q", 100, _make_config())
    assert len(results) == 3  # fake only returns 3


def test_search_empty_query_returns_error(monkeypatch):
    monkeypatch.setattr(duckduckgo_search, "DDGS", _FakeDDGS)
    results = search_web_impl("   ", 5, _make_config())
    assert results == [{"error": "query must not be empty"}]


def test_search_failure_returns_error(monkeypatch):
    class _BrokenDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def text(self, query, max_results=5):
            raise RuntimeError("rate limited")

    monkeypatch.setattr(duckduckgo_search, "DDGS", _BrokenDDGS)
    # Speed up the test by removing backoff sleeps.
    import hy3_deep_research.tools.search as search_mod

    monkeypatch.setattr(search_mod.time, "sleep", lambda *_: None)
    results = search_web_impl("q", 5, _make_config())
    assert len(results) == 1
    assert "error" in results[0]
    assert "search failed" in results[0]["error"]
