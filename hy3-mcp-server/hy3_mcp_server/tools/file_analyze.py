import os

from hy3_mcp_server.hy3_client import Hy3Client


_client: Hy3Client | None = None


def get_client() -> Hy3Client:
    global _client
    if _client is None:
        _client = Hy3Client()
    return _client


async def file_analyze(file_path: str, prompt: str) -> str:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    max_chars = 50000
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n... [truncated]"

    client = get_client()
    messages = [
        {
            "role": "system",
            "content": "You are a file analysis assistant. Analyze the provided file content and respond to the user's request.",
        },
        {
            "role": "user",
            "content": f"File path: {file_path}\n\nFile content:\n```\n{content}\n```\n\nRequest: {prompt}",
        },
    ]
    return client.chat(messages=messages)
