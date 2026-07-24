"""Web search client using Tavily Search API."""

import os
import json
import urllib.request
import urllib.error


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using Tavily API and return results.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (1-10).

    Returns:
        List of dicts with keys: title, url, content.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY environment variable is not set. "
            "Get a free key at https://tavily.com and set it in your .env file."
        )

    url = "https://api.tavily.com/search"
    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "max_results": min(max_results, 10),
        "include_answer": False,
        "include_raw_content": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Tavily API error {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error contacting Tavily: {e.reason}") from e

    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
        })
    return results
