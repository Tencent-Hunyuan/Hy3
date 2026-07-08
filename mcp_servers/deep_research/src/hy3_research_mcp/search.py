from __future__ import annotations

import html as html_module
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .config import ResearchSettings
from .web_utils import fetch_html, resolve_relative


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


def web_search(query: str, settings: ResearchSettings) -> List[SearchResult]:
    """Run a web search via the configured engine. Defaults to DuckDuckGo (no key)."""
    engine = (settings.search_engine or "duckduckgo").lower()
    if settings.search_api_key and engine in {"tavily", "brave"}:
        if engine == "tavily":
            return _tavily_search(query, settings)
        if engine == "brave":
            return _brave_search(query, settings)
    return _duckduckgo_search(query, settings)


def _duckduckgo_search(query: str, settings: ResearchSettings) -> List[SearchResult]:
    """Parse DuckDuckGo Lite HTML results. Pure stdlib, no API key required.

    Uses lite.duckduckgo.com, which returns server-rendered result HTML that is
    reliable to parse without JavaScript. The public duckduckgo.com/html/ page
    frequently serves a JS/redirect shell to non-browser clients.
    """
    import urllib.parse
    import urllib.request

    params = urllib.parse.urlencode({"q": query})
    url = f"https://lite.duckduckgo.com/html/?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": settings.user_agent})
    with urllib.request.urlopen(req, timeout=settings.page_timeout) as resp:
        html = resp.read().decode("utf-8", "replace")

    results: List[SearchResult] = []
    # Match each <a ... class="result__a" ... href="...">title</a> independently,
    # Match each result__a anchor regardless of attribute ORDER.
    anchor_re = re.compile(r'<a\b[^>]*class="result__a"[^>]*>(.*?)</a>', re.DOTALL)
    href_re = re.compile(r'href="([^"]+)"')
    for m in anchor_re.finditer(html):
        raw_href = href_re.search(m.group(0))
        if not raw_href:
            continue
        href_value = html_module.unescape(raw_href.group(1))
        actual = _unwrap_ddg_link(href_value) or resolve_relative("https://duckduckgo.com", href_value)
        if not actual or not actual.startswith("http"):
            continue
        title = _strip_tags(m.group(1)) or actual
        tail = html[m.end(): m.end() + 2000]
        next_anchor = tail.find("result__a")
        if next_anchor > 0:
            tail = tail[:next_anchor]
        snip = ""
        snip_m = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', tail, re.DOTALL)
        if snip_m:
            snip = _strip_tags(snip_m.group(1))
        results.append(SearchResult(title=title.strip(), url=actual, snippet=snip.strip()))
        if len(results) >= settings.max_search_results:
            break
    return results


def _unwrap_ddg_link(href: str) -> Optional[str]:
    import urllib.parse

    parsed = urllib.parse.urlparse(href)
    if "duckduckgo.com" in (parsed.netloc or "") and "/l/" in (parsed.path or ""):
        qs = urllib.parse.parse_qs(parsed.query)
        uddg = qs.get("uddg", [""])[0]
        if uddg:
            return html_module.unescape(uddg)
    return None


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _tavily_search(query: str, settings: ResearchSettings) -> List[SearchResult]:
    import urllib.parse

    payload = json.dumps(
        {
            "api_key": settings.search_api_key,
            "query": query,
            "max_results": settings.max_search_results,
        }
    ).encode("utf-8")
    req = urllib.parse.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": settings.user_agent,
        },
        method="POST",
    )
    import urllib.request

    with urllib.request.urlopen(req, timeout=settings.page_timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return [
        SearchResult(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("content", ""),
        )
        for item in data.get("results", [])[: settings.max_search_results]
    ]


def _brave_search(query: str, settings: ResearchSettings) -> List[SearchResult]:
    import urllib.parse

    params = urllib.parse.urlencode({"q": query, "count": settings.max_search_results})
    req = urllib.parse.Request(
        f"https://api.search.brave.com/res/v1/web/search?{params}",
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": settings.search_api_key or "",
            "User-Agent": settings.user_agent,
        },
    )
    import urllib.request

    with urllib.request.urlopen(req, timeout=settings.page_timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    results: List[SearchResult] = []
    for item in data.get("results", []) or []:
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
            )
        )
    return results[: settings.max_search_results]