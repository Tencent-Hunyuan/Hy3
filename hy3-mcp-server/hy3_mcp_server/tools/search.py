from duckduckgo_search import DDGS

from hy3_mcp_server.hy3_client import Hy3Client


_client: Hy3Client | None = None


def get_client() -> Hy3Client:
    global _client
    if _client is None:
        _client = Hy3Client()
    return _client


async def search_and_analyze(query: str, max_results: int = 5) -> str:
    search_results = []
    try:
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=max_results)):
                search_results.append(
                    f"[{i + 1}] {r['title']}\n    URL: {r['href']}\n    Snippet: {r['body']}"
                )
    except Exception as e:
        search_results.append(f"[Search failed: {e}]")

    if not search_results:
        return "No search results found."

    search_text = "\n\n".join(search_results)
    client = get_client()
    messages = [
        {
            "role": "system",
            "content": "You are a research assistant. Analyze the web search results and provide a comprehensive summary addressing the user's query.",
        },
        {
            "role": "user",
            "content": f"Search query: {query}\n\nSearch results:\n{search_text}\n\nPlease analyze these results and provide a comprehensive answer.",
        },
    ]
    return client.chat(messages=messages)
