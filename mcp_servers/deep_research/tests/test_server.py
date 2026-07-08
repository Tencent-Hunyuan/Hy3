import asyncio
import os

from hy3_research_mcp import server


def test_server_exposes_five_research_tools():
    tools = asyncio.run(server.mcp.list_tools())
    names = {tool.name for tool in tools}
    assert names == {
        "web_search_tool",
        "read_url_tool",
        "research_question",
        "summarize_documents",
        "generate_research_outline",
    }
    assert all(tool.description for tool in tools)
    assert all(tool.inputSchema is not None for tool in tools)




def test_web_search_tool_requires_query_schema():
    tools = asyncio.run(server.mcp.list_tools())
    tool = next(t for t in tools if t.name == "web_search_tool")
    props = tool.inputSchema.get("properties", {})
    assert "query" in props
    assert "max_results" in props
    required = tool.inputSchema.get("required", [])
    assert "query" in required


def test_research_question_tool_schema_documents_inputs():
    tools = asyncio.run(server.mcp.list_tools())
    tool = next(t for t in tools if t.name == "research_question")
    props = tool.inputSchema.get("properties", {})
    for name in ["question", "searches", "focus", "depth", "read_top_pages"]:
        assert name in props
    assert "question" in tool.inputSchema.get("required", [])

class FakeClient:
    def __init__(self, text="HY3-SAYS"):
        self.text = text
        self.last_prompt = ""

    def complete(self, prompt, *, system="", prior_turns=None):
        self.last_prompt = prompt
        return self.text


def test_research_question_uses_hy3_client_and_search(monkeypatch):
    fake = FakeClient("## Answer\nHy3 synthesized.")

    def fake_client():
        return fake

    def fake_web_search(query, settings):
        from hy3_research_mcp.search import SearchResult

        return [SearchResult(title=query, url=f"https://example.com/{query}", snippet="snip")]

    monkeypatch.setattr(server, "_client", fake_client)
    monkeypatch.setattr(server, "web_search", fake_web_search)

    env = dict(os.environ)
    os.environ.pop("HY3_API_KEY", None)
    os.environ.pop("HY3_BASE_URL", None)
    result = server.research_question(
        question="What is Hy3?",
        searches="Hy3 model",
        depth="balanced",
    )
    os.environ.clear()
    os.environ.update(env)

    assert result["question"] == "What is Hy3?"
    assert "Hy3 model" in result["queries"]
    assert result["answer"] == "## Answer\nHy3 synthesized."
    assert "Hy3 synthesized." in fake.last_prompt or "Hy3 model" in fake.last_prompt


def test_summarize_documents_requires_documents():
    try:
        server.summarize_documents(question="q", documents=[])
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty documents")


def test_generate_research_outline_returns_outline(monkeypatch):
    fake = FakeClient("## Outline\n1. Intro\n2. Body")

    monkeypatch.setattr(server, "_client", lambda: fake)

    def fake_web_search(query, settings):
        from hy3_research_mcp.search import SearchResult

        return [SearchResult(title="t", url="https://e.com", snippet="s")]

    monkeypatch.setattr(server, "web_search", fake_web_search)
    result = server.generate_research_outline(question="topic")
    assert result["outline"] == "## Outline\n1. Intro\n2. Body"
    assert "topic" in fake.last_prompt