"""
Hy3 Deep Research Demo — minimal end-to-end example.

Requires:
    pip install openai httpx

Usage:
    HY3_API_BASE=http://127.0.0.1:8000/v1 python research_demo.py
"""

import os
import re
import textwrap

import httpx
from openai import OpenAI

API_BASE = os.environ.get("HY3_API_BASE", "http://127.0.0.1:8000/v1")
API_KEY = os.environ.get("HY3_API_KEY", "EMPTY")

_client = OpenAI(base_url=API_BASE, api_key=API_KEY)
_DDG_URL = "https://html.duckduckgo.com/html/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; hy3-demo/0.1)"}
_TAG_RE = re.compile(r"<[^>]+>")


def search(query: str, n: int = 5) -> str:
    with httpx.Client(timeout=15, follow_redirects=True) as c:
        resp = c.post(_DDG_URL, data={"q": query}, headers=_HEADERS)
        resp.raise_for_status()
    text, results, idx = resp.text, [], 0
    while len(results) < n:
        if (start := text.find('class="result__title"', idx)) == -1:
            break
        href_s = text.find('href="', start)
        href_e = text.find('"', href_s + 6)
        url = text[href_s + 6:href_e] if href_s != -1 else ""
        a_end = text.find("</a>", href_s)
        title = _TAG_RE.sub("", text[href_e + 2:a_end] if a_end != -1 else "").strip()
        if title:
            results.append(f"[{len(results)+1}] {title}\n    {url}")
        idx = (a_end + 1) if a_end != -1 else start + 1
    return "\n\n".join(results) if results else "No results."


def ask_hy3(prompt: str, reasoning: str = "no_think") -> str:
    resp = _client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning}},
    )
    return resp.choices[0].message.content or ""


def research(topic: str) -> str:
    print(f"[1/3] Searching: {topic}")
    findings = search(topic)

    print("[2/3] Analysing with Hy3 ...")
    analysis = ask_hy3(textwrap.dedent(f"""\
        Based on these search results, answer: what are the key points about "{topic}"?

        Results:
        {findings}
    """))

    print("[3/3] Generating report ...")
    return ask_hy3(textwrap.dedent(f"""\
        Write a concise Markdown research report on "{topic}".

        Findings:
        {analysis}
    """), reasoning="high")


if __name__ == "__main__":
    topic = "Tencent Hunyuan Hy3 model capabilities"
    report = research(topic)
    print("\n" + "=" * 60)
    print(report)
