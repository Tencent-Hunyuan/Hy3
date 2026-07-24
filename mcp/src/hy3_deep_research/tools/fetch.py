"""fetch_url tool: download a web page and extract its clean main text."""

from __future__ import annotations

import socket
from typing import Any
from urllib.parse import urlparse

from ..config import Config
from ..models import FetchResult

# Allowed URL schemes for fetch_url — prevents accidental file:// or ftp:// access.
_ALLOWED_SCHEMES = ("http", "https")


def fetch_url_impl(
    url: str, max_chars: int, config: Config
) -> dict[str, Any]:
    """Fetch a URL and extract its main text content with trafilatura.

    Returns a dict with keys: url, title, content, success, error.
    Never raises; failures are reported via ``success=False``.
    """
    url = (url or "").strip()
    if not url:
        return {"url": "", "title": "", "content": "", "success": False, "error": "url must not be empty"}

    # Validate URL scheme — only http/https are allowed.
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return {
            "url": url,
            "title": "",
            "content": "",
            "success": False,
            "error": f"unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        }

    try:
        import trafilatura
    except Exception as exc:  # noqa: BLE001
        return {
            "url": url,
            "title": "",
            "content": "",
            "success": False,
            "error": f"trafilatura not available: {exc}",
        }

    # Apply the configured timeout to the underlying socket operations so
    # that a hanging server cannot block the entire MCP server.
    timeout = max(5, int(config.fetch_timeout))
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {
                "url": url,
                "title": "",
                "content": "",
                "success": False,
                "error": "failed to download the page (empty response or blocked)",
            }

        # Extract metadata (title) and main text.
        metadata = trafilatura.extract(downloaded, output_format="json") or "{}"
        import json

        try:
            meta_obj = json.loads(metadata) if isinstance(metadata, str) else metadata
            title = (meta_obj or {}).get("title", "") or ""
        except (ValueError, TypeError):
            title = ""

        text = trafilatura.extract(
            downloaded, include_links=True, include_tables=True
        )
        if not text:
            return {
                "url": url,
                "title": title,
                "content": "",
                "success": False,
                "error": "could not extract main text from the page",
            }

        max_chars = max(100, int(max_chars or config.fetch_max_chars))
        if len(text) > max_chars:
            text = text[:max_chars].rsplit(" ", 1)[0] + "…"

        return {"url": url, "title": title, "content": text, "success": True, "error": None}
    except socket.timeout:
        return {"url": url, "title": "", "content": "", "success": False, "error": f"fetch timed out after {timeout}s"}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "title": "", "content": "", "success": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        socket.setdefaulttimeout(old_timeout)


def register_fetch_tools(mcp, config: Config) -> None:
    """Register the `fetch_url` MCP tool."""

    @mcp.tool()
    def fetch_url(url: str, max_chars: int = 8000) -> FetchResult:
        """Fetch a web page and extract its clean main text content.

        Useful for reading the full content of a URL found via `search_web`,
        so Hy3 can reason over the actual article text rather than just snippets.
        Only http:// and https:// URLs are supported.

        Args:
            url: The full URL of the web page to fetch (http or https only).
            max_chars: Maximum characters of text to return (default 8000).

        Returns:
            An object: {"url": str, "title": str, "content": str, "success": bool, "error": str|null}.
        """
        return fetch_url_impl(url, max_chars, config)  # type: ignore[return-value]
