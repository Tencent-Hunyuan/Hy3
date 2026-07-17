import os
import re
import textwrap
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from openai import OpenAI


# lazy-init so env vars are resolved at call time, not module load
def _hy3_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ.get("HY3_API_BASE", "http://127.0.0.1:8000/v1"),
        api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    )


def _call_hy3(prompt: str, reasoning: str = "no_think") -> str:
    resp = _hy3_client().chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning}},
    )
    return resp.choices[0].message.content or ""


_DDG_URL = "https://html.duckduckgo.com/html/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; hy3-mcp/0.1)"}
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(html: str) -> str:
    return _TAG_RE.sub("", html)


def _search_web(query: str) -> str:
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.post(_DDG_URL, data={"q": query}, headers=_HEADERS)
            resp.raise_for_status()

        # lightweight extraction - avoids a heavy HTML-parser dependency
        text = resp.text
        results: list[str] = []
        idx = 0
        while len(results) < 5:
            if (start := text.find('class="result__title"', idx)) == -1:
                break
            href_start = text.find('href="', start)
            href_end = text.find('"', href_start + 6)
            url = text[href_start + 6: href_end] if href_start != -1 else ""
            a_end = text.find("</a>", href_start)
            title = _strip_tags(text[href_end + 2: a_end] if a_end != -1 else "").strip()
            snip_start = text.find('class="result__snippet"', a_end)
            snip_end = text.find("</a>", snip_start) if snip_start != -1 else -1
            snippet = _strip_tags(text[snip_start: snip_end]).strip() if snip_start != -1 and snip_end != -1 else ""
            if title:
                results.append(f"[{len(results)+1}] {title}\n    {url}\n    {snippet}")
            idx = (a_end + 1) if a_end != -1 else start + 1

        return "\n\n".join(results) if results else f"No results found for: {query}"

    except Exception as exc:  # noqa: BLE001
        return f"Search error: {exc}"


def _analyze_with_hy3(content: str, question: str, reasoning: str = "no_think") -> str:
    return _call_hy3(textwrap.dedent(f"""\
        You are a rigorous research analyst. Based on the provided content, answer the question.

        ## Content
        {content}

        ## Question
        {question}

        Provide a clear, evidence-based answer. Cite specific parts of the content where relevant.
    """), reasoning=reasoning)


def _generate_report(topic: str, findings: str) -> str:
    return _call_hy3(textwrap.dedent(f"""\
        You are an expert research writer. Generate a well-structured Markdown research report.

        ## Topic
        {topic}

        ## Research Findings
        {findings}

        ## Report Structure (follow exactly)
        # {topic}

        ## Executive Summary
        (2-3 sentences)

        ## Key Findings
        (bullet points)

        ## Analysis
        (detailed paragraphs)

        ## Conclusion
        (actionable insights)

        ## References
        (list sources mentioned in findings)
    """), reasoning="high")


TOOLS: list[Tool] = [
    Tool(
        name="search_web",
        description=(
            "Search the web using DuckDuckGo and return the top 5 results "
            "(title, URL, snippet). Use this to gather information on a topic."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="analyze_with_hy3",
        description=(
            "Send content to Hy3 for in-depth analysis. "
            "Returns Hy3's analytical response to the given question about the content."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The source content to analyse (search results, documents, etc.)",
                },
                "question": {
                    "type": "string",
                    "description": "The specific question or analysis task",
                },
                "reasoning": {
                    "type": "string",
                    "enum": ["no_think", "low", "high"],
                    "description": "Reasoning depth: 'no_think' (fast), 'low', 'high' (deep CoT)",
                    "default": "no_think",
                },
            },
            "required": ["content", "question"],
        },
    ),
    Tool(
        name="generate_report",
        description=(
            "Ask Hy3 to generate a structured Markdown research report on a topic, "
            "given accumulated findings. Returns a complete report with summary, "
            "key findings, analysis, conclusion and references."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The research topic or title"},
                "findings": {
                    "type": "string",
                    "description": "Accumulated research findings and notes to synthesise",
                },
            },
            "required": ["topic", "findings"],
        },
    ),
]


async def _handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    match name:
        case "search_web":
            result = _search_web(arguments["query"])
        case "analyze_with_hy3":
            result = _analyze_with_hy3(
                arguments["content"],
                arguments["question"],
                arguments.get("reasoning", "no_think"),
            )
        case "generate_report":
            result = _generate_report(arguments["topic"], arguments["findings"])
        case _:
            result = f"Unknown tool: {name}"
    return [TextContent(type="text", text=result)]


_server = Server("hy3-research-assistant")


@_server.list_tools()
async def _list_tools() -> list[Tool]:
    return TOOLS


@_server.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    return await _handle_call_tool(name, arguments)


def main() -> None:
    import asyncio

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await _server.run(read_stream, write_stream, _server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
