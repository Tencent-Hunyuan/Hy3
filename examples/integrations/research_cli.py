"""
Terminal research assistant powered by Hy3.

Usage:
    python research_cli.py "Your research question"

Requires: openai httpx
"""
import re
import sys
import textwrap
import httpx
from openai import OpenAI

_DDG_URL = "https://html.duckduckgo.com/html/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; hy3-research/0.1)"}
_TAG_RE = re.compile(r"<[^>]+>")


def _client() -> OpenAI:
    return OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")


def _hy3(prompt: str, reasoning: str = "no_think") -> str:
    resp = _client().chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning}},
    )
    return resp.choices[0].message.content or ""


def _search(query: str, n: int = 5) -> list[dict[str, str]]:
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            resp = c.post(_DDG_URL, data={"q": query}, headers=_HEADERS)
            resp.raise_for_status()
    except Exception as exc:
        print(f"  [search error] {exc}", file=sys.stderr)
        return []

    text = resp.text
    results: list[dict[str, str]] = []
    idx = 0
    while len(results) < n:
        if (start := text.find('class="result__title"', idx)) == -1:
            break
        href_start = text.find('href="', start)
        href_end = text.find('"', href_start + 6)
        url = text[href_start + 6 : href_end] if href_start != -1 else ""
        a_end = text.find("</a>", href_start)
        title = _TAG_RE.sub("", text[href_end + 2 : a_end] if a_end != -1 else "").strip()
        snip_start = text.find('class="result__snippet"', a_end)
        snip_end = text.find("</a>", snip_start) if snip_start != -1 else -1
        snippet = (
            _TAG_RE.sub("", text[snip_start:snip_end]).strip()
            if snip_start != -1 and snip_end != -1
            else ""
        )
        if title:
            results.append({"title": title, "url": url, "snippet": snippet})
        idx = (a_end + 1) if a_end != -1 else start + 1
    return results


def _analyse(source: dict[str, str], question: str) -> str:
    content = f"Title: {source['title']}\nURL: {source['url']}\n\n{source['snippet']}"
    return _hy3(textwrap.dedent(f"""\
        Based on the following source, answer this question: {question}

        Source:
        {content}

        Be concise and cite specific details from the source.
    """))


def _report(question: str, findings: str) -> str:
    return _hy3(textwrap.dedent(f"""\
        Write a structured Markdown research report answering: {question}

        Research findings:
        {findings}

        Structure:
        # {question}
        ## Summary
        ## Key Findings
        ## Analysis
        ## Conclusion
    """), reasoning="high")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python research_cli.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"\nResearching: {question}\n")

    print("Searching...")
    sources = _search(question)
    if not sources:
        print("No search results. Check your network connection.")
        sys.exit(1)

    print(f"Found {len(sources)} sources. Analysing with Hy3...\n")
    findings: list[str] = []
    for i, src in enumerate(sources, 1):
        print(f"  [{i}/{len(sources)}] {src['title'][:60]}")
        analysis = _analyse(src, question)
        findings.append(f"[{i}] {src['title']} ({src['url']})\n{analysis}")

    print("\nSynthesising report (high reasoning)...\n")
    report = _report(question, "\n\n".join(findings))
    print(report)


if __name__ == "__main__":
    main()
