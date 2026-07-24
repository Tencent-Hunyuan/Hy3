from __future__ import annotations

from hy3_deep_research.config import Config
from hy3_deep_research.tools.research import _extract_json_array, deep_research_impl


def _make_config() -> Config:
    return Config(hunyuan_api_key="k")


class _FakeHy3:
    """Fake Hy3 client returning scripted responses."""

    def __init__(self):
        self.decompose_response = '["what is hy3", "hy3 benchmarks", "hy3 use cases"]'
        self.synthesis_response = "Hy3 is a MoE model [1]. It scores well on agent tasks [2]."

    def chat(self, messages, reasoning_effort="high", tools=None, temperature=0.9, top_p=1.0):
        content = messages[0]["content"]
        if "JSON array" in content:
            return self.decompose_response
        return self.synthesis_response


def test_extract_json_array_plain():
    assert _extract_json_array('["a", "b", "c"]') == ["a", "b", "c"]


def test_extract_json_array_fenced():
    text = 'Here you go:\n```json\n["x", "y"]\n```'
    assert _extract_json_array(text) == ["x", "y"]


def test_extract_json_array_invalid():
    assert _extract_json_array("not json at all") == []


def test_deep_research_orchestration(monkeypatch):
    import hy3_deep_research.tools.research as research_mod

    fake_search_results = [
        {"title": "Hy3 model", "url": "https://a.com", "snippet": "MoE model"},
        {"title": "Hy3 benchmarks", "url": "https://b.com", "snippet": "Agent tasks"},
    ]
    monkeypatch.setattr(
        research_mod, "search_web_impl", lambda q, n, c: list(fake_search_results)
    )
    monkeypatch.setattr(
        research_mod,
        "fetch_url_impl",
        lambda url, mc, c: {
            "url": url,
            "title": url,
            "content": f"Full content for {url}",
            "success": True,
            "error": None,
        },
    )

    result = deep_research_impl("What is Hy3?", _FakeHy3(), _make_config())

    assert result["query"] == "What is Hy3?"
    assert result["sub_queries"] == ["what is hy3", "hy3 benchmarks", "hy3 use cases"]
    assert result["sources_searched"] == 2
    assert result["sources_fetched"] == 2
    assert "[1]" in result["report"]
    assert len(result["citations"]) == 2
    assert result["citations"][0]["index"] == 1
    assert result["citations"][0]["url"] == "https://a.com"


def test_deep_research_empty_query():
    result = deep_research_impl("", _FakeHy3(), _make_config())
    assert "empty" in result["report"].lower()
    assert result["citations"] == []


class _TrackingHy3:
    """Fake Hy3 client that records the reasoning_effort used for each call."""

    def __init__(self):
        self.decompose_response = '["q1", "q2"]'
        self.synthesis_response = "Report [1]."
        self.efforts_used: list[str] = []

    def chat(self, messages, reasoning_effort="high", tools=None, temperature=0.9, top_p=1.0):
        self.efforts_used.append(reasoning_effort)
        content = messages[0]["content"]
        if "JSON array" in content:
            return self.decompose_response
        return self.synthesis_response


def test_deep_research_valid_reasoning_effort(monkeypatch):
    """Valid reasoning_effort values are passed through to Hy3."""
    import hy3_deep_research.tools.research as research_mod

    monkeypatch.setattr(research_mod, "search_web_impl", lambda q, n, c: [])
    monkeypatch.setattr(research_mod, "fetch_url_impl", lambda url, mc, c: {"success": False})

    hy3 = _TrackingHy3()
    deep_research_impl("query", hy3, _make_config(), reasoning_effort="low")
    # First call is decompose (always "low"), second is synthesis (should be "low").
    assert hy3.efforts_used[-1] == "low"


def test_deep_research_invalid_reasoning_effort_falls_back(monkeypatch):
    """Invalid reasoning_effort falls back to the configured default."""
    import hy3_deep_research.tools.research as research_mod

    monkeypatch.setattr(research_mod, "search_web_impl", lambda q, n, c: [])
    monkeypatch.setattr(research_mod, "fetch_url_impl", lambda url, mc, c: {"success": False})

    hy3 = _TrackingHy3()
    # "ultra" is not a valid value — should fall back to config default "high".
    deep_research_impl("query", hy3, _make_config(), reasoning_effort="ultra")
    assert hy3.efforts_used[-1] == "high"  # fell back to config default


def test_deep_research_falls_back_when_no_json(monkeypatch):
    import hy3_deep_research.tools.research as research_mod

    hy3 = _FakeHy3()
    hy3.decompose_response = "I cannot produce JSON."
    monkeypatch.setattr(research_mod, "search_web_impl", lambda q, n, c: [{"title": "t", "url": "https://x.com", "snippet": "s"}])
    monkeypatch.setattr(
        research_mod,
        "fetch_url_impl",
        lambda url, mc, c: {"url": url, "title": "t", "content": "c", "success": True, "error": None},
    )
    result = deep_research_impl("Hy3?", hy3, _make_config())
    # Falls back to using the original query as the single sub-query.
    assert result["sub_queries"] == ["Hy3?"]
