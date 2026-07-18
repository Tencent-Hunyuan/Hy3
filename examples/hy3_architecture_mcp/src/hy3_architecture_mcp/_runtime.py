"""Internal runtime helpers: prompt loading and a lazy Hy3 client singleton."""

from __future__ import annotations

import logging
import sys
from importlib import resources

from .config import Settings, load_settings
from .hy3_client import Hy3Client

# MCP runs over stdio: ALL logging MUST go to stderr, never stdout.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("hy3_architecture_mcp")

_client: Hy3Client | None = None


def get_client(settings: Settings | None = None) -> Hy3Client:
    """Return a lazily-created, cached Hy3Client."""
    global _client
    if _client is None:
        _client = Hy3Client(settings or load_settings())
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def load_prompt(name: str) -> str:
    """Read a prompt markdown file packaged under ``prompts/``."""
    return (
        resources.files("hy3_architecture_mcp")
        .joinpath("prompts", f"{name}.md")
        .read_text(encoding="utf-8")
    )
