from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from .config import ResearchSettings


def _build_opener(settings: ResearchSettings):
    import urllib.request

    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", settings.user_agent)]
    return opener


def fetch_html(url: str, settings: ResearchSettings) -> str:
    """Fetch raw HTML for a URL with a timeout. Raises on HTTP errors."""
    import urllib.error

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Only http/https URLs are supported: {url}")

    opener = _build_opener(settings)
    try:
        with opener.open(url, timeout=settings.page_timeout) as response:
            raw = response.read(settings.max_page_chars + 4096)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} fetching {url}") from exc
    except Exception as exc:  # noqa: BLE001 - surface any fetch failure to the tool caller
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc

    charset = "utf-8"
    if hasattr(response, "headers") and response.headers.get("Content-Type"):
        for part in response.headers.get("Content-Type", "").split(";"):
            part = part.strip()
            if part.startswith("charset="):
                charset = part[len("charset=") :]
    try:
        return raw.decode(charset or "utf-8", errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)


def html_to_text(html: str, max_chars: int) -> str:
    """Crude but dependency-free HTML -> text extraction for research snippets."""
    text = _SCRIPT_STYLE_RE.sub(" ", html)
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    text = text.replace("</p>", "\n\n").replace("</li>", "\n").replace("</h", "\n")
    text = _TAG_RE.sub("", text)
    import html as html_module

    text = html_module.unescape(text)
    lines = [ln.strip() for ln in text.splitlines()]
    text = _WS_RE.sub(" ", "\n".join(ln for ln in lines if ln)).strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars] + "\n\n[truncated]"
    return text


def read_url_text(url: str, settings: ResearchSettings, max_chars: Optional[int] = None) -> str:
    """Fetch a URL and return readable text bounded by max_chars."""
    limit = max_chars if max_chars is not None else settings.max_page_chars
    html = fetch_html(url, settings)
    return html_to_text(html, limit)


def resolve_relative(base: str, href: str) -> Optional[str]:
    if not href or href.startswith(("#", "mailto:", "javascript:")):
        return None
    return urljoin(base, href)