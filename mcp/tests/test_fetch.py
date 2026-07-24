from __future__ import annotations

import json
import socket

import trafilatura

from hy3_deep_research.config import Config
from hy3_deep_research.tools.fetch import fetch_url_impl


def _make_config(fetch_timeout: int = 30) -> Config:
    return Config(hunyuan_api_key="k", fetch_max_chars=8000, fetch_timeout=fetch_timeout)


def test_fetch_success(monkeypatch):
    page_html = "<html><head><title>Example</title></head><body><p>Hello world content here.</p></body></html>"

    def fake_fetch_url(url):
        return page_html

    def fake_extract(downloaded, **kwargs):
        if kwargs.get("output_format") == "json":
            return json.dumps({"title": "Example"})
        return "Hello world content here."

    monkeypatch.setattr(trafilatura, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(trafilatura, "extract", fake_extract)

    result = fetch_url_impl("https://example.com", 8000, _make_config())
    assert result["success"] is True
    assert result["title"] == "Example"
    assert "Hello world" in result["content"]
    assert result["error"] is None


def test_fetch_truncates_to_max_chars(monkeypatch):
    long_text = "word " * 5000  # ~25000 chars
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: "<html><body>x</body></html>")
    monkeypatch.setattr(
        trafilatura,
        "extract",
        lambda downloaded, **kw: json.dumps({"title": "T"}) if kw.get("output_format") == "json" else long_text,
    )

    result = fetch_url_impl("https://example.com", 500, _make_config())
    assert result["success"] is True
    assert len(result["content"]) <= 510  # 500 + ellipsis allowance
    assert result["content"].endswith("…")


def test_fetch_empty_url():
    result = fetch_url_impl("", 8000, _make_config())
    assert result["success"] is False
    assert "empty" in result["error"]


def test_fetch_download_failure(monkeypatch):
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: None)
    result = fetch_url_impl("https://example.com", 8000, _make_config())
    assert result["success"] is False
    assert "download" in result["error"]


def test_fetch_timeout_returns_error(monkeypatch):
    """When the socket times out, the tool returns a structured error."""

    def _raise_timeout(url):
        raise socket.timeout("timed out")

    monkeypatch.setattr(trafilatura, "fetch_url", _raise_timeout)
    result = fetch_url_impl("https://slow-server.com", 8000, _make_config(fetch_timeout=5))
    assert result["success"] is False
    assert "timed out" in result["error"]


def test_fetch_timeout_restores_socket_default(monkeypatch):
    """Ensure the original socket default timeout is restored after fetch."""
    original = socket.getdefaulttimeout()
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: None)
    fetch_url_impl("https://example.com", 8000, _make_config(fetch_timeout=10))
    assert socket.getdefaulttimeout() == original


def test_fetch_rejects_non_http_scheme():
    """Non-http/https URL schemes are rejected before any network call."""
    for bad_url in ("file:///etc/passwd", "ftp://example.com/file", "javascript:alert(1)"):
        result = fetch_url_impl(bad_url, 8000, _make_config())
        assert result["success"] is False
        assert "scheme" in result["error"]


def test_fetch_accepts_http_url():
    """http:// URLs (without ssl) should be accepted (scheme check only)."""
    # We just check the scheme validation passes; the actual fetch will fail
    # since there's no real server, but the error should NOT mention "scheme".
    result = fetch_url_impl("http://localhost:9999/nonexistent", 8000, _make_config(fetch_timeout=5))
    assert "scheme" not in result.get("error", "")
