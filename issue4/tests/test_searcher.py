"""Tests for hy3research.searcher."""

import pytest
from hy3research.searcher import deduplicate_sources, search_all


class TestDeduplicate:
    def test_removes_duplicate_urls(self):
        sources = [
            {"url": "http://a.com", "title": "A"},
            {"url": "http://a.com", "title": "A dup"},
            {"url": "http://b.com", "title": "B"},
        ]
        result = deduplicate_sources(sources)
        urls = [s["url"] for s in result]
        assert urls == ["http://a.com", "http://b.com"]

    def test_preserves_first_occurrence(self):
        sources = [
            {"url": "http://a.com", "title": "First"},
            {"url": "http://a.com", "title": "Second"},
        ]
        result = deduplicate_sources(sources)
        assert result[0]["title"] == "First"


class TestSearchAll:
    def test_returns_list_with_indices(self):
        subtopics = [
            {"query": "Python programming", "key_question": "What is Python?"},
        ]
        results = search_all(subtopics, mock=True)
        assert isinstance(results, list)
        assert len(results) > 0
        for r in results:
            assert "index" in r
            assert "url" in r
            assert "title" in r
            assert "snippet" in r
            assert "query" in r

    def test_mock_no_duplicates(self):
        subtopics = [
            {"query": "same query", "key_question": "q1"},
            {"query": "same query", "key_question": "q2"},
        ]
        results = search_all(subtopics, mock=True)
        urls = [r["url"] for r in results]
        assert len(urls) == len(set(urls))
