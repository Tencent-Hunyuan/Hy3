from hy3_mcp_server.hy3_client import Hy3Client


_client: Hy3Client | None = None


def get_client() -> Hy3Client:
    global _client
    if _client is None:
        _client = Hy3Client()
    return _client


async def ask_hy3(
    prompt: str,
    reasoning_effort: str = "no_think",
) -> str:
    client = get_client()
    messages = [
        {
            "role": "system",
            "content": "You are Hy3, a helpful AI assistant. Provide clear and accurate responses.",
        },
        {"role": "user", "content": prompt},
    ]
    return client.chat(
        messages=messages,
        reasoning_effort=reasoning_effort,
    )
