from hy3_research_mcp.config import ResearchSettings
from hy3_research_mcp.web_utils import html_to_text, resolve_relative


def test_html_to_text_strips_tags_and_keeps_text():
    html = "<html><body><script>var x=1</script><h1>Title</h1><p>Hello <b>world</b>.</p></body></html>"
    text = html_to_text(html, max_chars=0)
    assert "Title" in text
    assert "Hello world" in text
    assert "var x=1" not in text


def test_html_to_text_truncates_with_marker():
    html = "<p>" + ("a" * 100) + "</p>"
    text = html_to_text(html, max_chars=10)
    assert text.endswith("[truncated]")
    assert text.startswith("aaaaaaaaaa")


def test_html_to_text_unescapes_entities():
    assert "&amp;" not in html_to_text("<p>Tom &amp; Jerry</p>", max_chars=0)
    assert "Tom & Jerry" in html_to_text("<p>Tom &amp; Jerry</p>", max_chars=0)


def test_resolve_relative_handles_common_cases():
    assert resolve_relative("https://example.com/", "https://other.com/x") == "https://other.com/x"
    assert resolve_relative("https://example.com/page", "/x") == "https://example.com/x"
    assert resolve_relative("https://example.com/", "mailto:a@b.com") is None
    assert resolve_relative("https://example.com/", "#frag") is None
    assert resolve_relative("https://example.com/", "") is None


def test_fetch_html_rejects_non_http(monkeypatch):
    from hy3_research_mcp.web_utils import fetch_html

    settings = ResearchSettings.from_env()
    try:
        fetch_html("file:///etc/passwd", settings)
    except ValueError:
        return
    raise AssertionError("expected ValueError for non-http scheme")