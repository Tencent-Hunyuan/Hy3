from hy3_research_mcp.research import (
    Evidence,
    build_outline_prompt,
    build_research_prompt,
    build_summary_prompt,
    render_evidence_block,
)
from hy3_research_mcp.search import SearchResult


class FakeCompletionClient:
    def __init__(self, text: str = "fake answer"):
        self.text = text
        self.last_prompt = ""
        self.calls = 0

    def complete(self, prompt, *, system="", prior_turns=None):  # noqa: D401
        self.calls += 1
        self.last_prompt = prompt
        return self.text


def _settings_for() -> None:
    return None


def test_evidence_render_for_empty_results():
    e = Evidence(query="q", results=[])
    assert "no usable results" in e.render()


def test_evidence_render_lists_results_with_indices():
    r = SearchResult(title="T", url="https://example.com", snippet="S")
    out = Evidence(query="q", results=[r]).render()
    assert "[1]" in out
    assert "T" in out
    assert "https://example.com" in out
    assert "S" in out


def test_render_evidence_block_joins_multiple():
    a = Evidence(query="a", results=[SearchResult("A", "https://a", "x")])
    b = Evidence(query="b", results=[SearchResult("B", "https://b", "y")])
    out = render_evidence_block([a, b])
    assert "Search: a" in out
    assert "Search: b" in out


def test_build_research_prompt_includes_question_and_focus():
    prompt = build_research_prompt("Why X?", "EVIDENCE", focus="cost", depth="deep")
    assert "Why X?" in prompt
    assert "EVIDENCE" in prompt
    assert "cost" in prompt


def test_build_outline_prompt_asks_for_outline_not_report():
    prompt = build_outline_prompt("topic", "EVIDENCE")
    assert "outline" in prompt.lower()
    assert "sections" in prompt.lower()


def test_build_summary_prompt_references_documents_label():
    prompt = build_summary_prompt("Q", "Doc A:\nbody")
    assert "Doc A" in prompt
    assert "Q" in prompt