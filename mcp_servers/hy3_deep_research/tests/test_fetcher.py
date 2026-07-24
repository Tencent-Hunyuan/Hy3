from __future__ import annotations

import pytest

from hy3_deep_research.fetcher import FetchError, WebFetcher


@pytest.mark.asyncio
async def test_fetcher_blocks_loopback_urls_by_default() -> None:
    fetcher = WebFetcher(timeout_seconds=1)

    with pytest.raises(FetchError, match="private, loopback"):
        await fetcher.fetch("http://127.0.0.1/internal")


def test_html_extraction_removes_scripts_and_navigation() -> None:
    fetcher = WebFetcher(max_chars=1_000)
    title, content = fetcher._extract(  # noqa: SLF001 - focused extraction unit test
        """
        <html>
          <head><title>Research title</title><script>ignore me</script></head>
          <body><nav>menu</nav><main><h1>Finding</h1><p>Evidence text.</p></main></body>
        </html>
        """,
        "text/html",
        "https://example.com/research",
    )

    assert title == "Research title"
    assert "Finding" in content
    assert "Evidence text." in content
    assert "ignore me" not in content
    assert "menu" not in content
