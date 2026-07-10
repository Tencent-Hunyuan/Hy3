"""MCP server exposing Hy3-powered knowledge-base tools over stdio.

Run with::

    hy3-kb-mcp            # console script (after pip install)
    python -m hy3_mcp     # module form

The server reads its configuration (API key, endpoints) exclusively from
environment variables — nothing sensitive is hardcoded.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import load_settings
from .hy3_client import Hy3Client
from .knowledge_base import KnowledgeBase
from .parsers import UnsupportedFileType

# --- shared state (per server process) ------------------------------------
_SETTINGS = load_settings()
_KB = KnowledgeBase(_SETTINGS)
_HY3 = Hy3Client(_SETTINGS)

mcp = FastMCP("hy3-knowledge-base")


# --- helpers --------------------------------------------------------------
def _require_key() -> str | None:
    if not _SETTINGS.has_api_key:
        return (
            "HY3_API_KEY is not set. Export it as an environment variable "
            "(e.g. `export HY3_API_KEY=...`) and restart the server."
        )
    return None


def _render_sources(chunks) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        snippet = c.text.replace("\n", " ").strip()
        if len(snippet) > 160:
            snippet = snippet[:160] + "..."
        lines.append(f"[{i}] {c.source}\n    {snippet}")
    return "\n".join(lines)


# --- tools ----------------------------------------------------------------
@mcp.tool()
def load_knowledge(paths: list[str]) -> str:
    """Load documents into the knowledge base.

    Parses and chunks the given files/directories, builds a retrieval index,
    and persists it locally. Supported formats: .txt, .md, .markdown, .csv.

    Args:
        paths: List of file or directory paths. Directories are scanned
            recursively for supported files; unsupported files are skipped.

    Returns:
        A summary of how many files were loaded and chunks were added.
    """
    if not paths:
        return "No paths provided. Please pass a list of files or directories."
    result = _KB.load_paths(paths)
    msg = (
        f"Loaded {result['files_loaded']} file(s), added "
        f"{result['chunks_added']} chunk(s). "
        f"Total chunks in KB: {result['total_chunks']}."
    )
    if result["skipped"]:
        msg += f" Skipped {result['skipped']} path(s)."
    if result["errors"]:
        msg += "\nErrors:\n" + "\n".join(f"  - {e}" for e in result["errors"])
    return msg


@mcp.tool()
def search_knowledge(query: str, top_k: int = 5) -> str:
    """Retrieve relevant chunks from the knowledge base (no LLM call).

    Useful to inspect what the knowledge base contains for a query before
    asking the model, or to fetch raw evidence.

    Args:
        query: The search query (keywords / question).
        top_k: Number of chunks to return (default 5).

    Returns:
        The top matching chunks with their source file paths.
    """
    if _KB.is_empty():
        return "Knowledge base is empty. Call `load_knowledge` first."
    chunks = _KB.search(query, top_k=max(1, top_k))
    if not chunks:
        return "No relevant chunks found."
    return "Retrieved chunks:\n\n" + _render_sources(chunks)


@mcp.tool()
def ask_knowledge(
    question: str, top_k: int = 5, include_sources: bool = True
) -> str:
    """Answer a question using the knowledge base and the Hy3 model.

    Retrieves the most relevant chunks for the question, then asks the Hy3
    model to answer strictly from that context, citing sources.

    Args:
        question: The question to answer.
        top_k: How many chunks to retrieve as context (default 5).
        include_sources: If true (default), append the cited source
            snippets to the answer.

    Returns:
        The model's answer, optionally followed by the source passages.
    """
    if _KB.is_empty():
        return "Knowledge base is empty. Call `load_knowledge` first."
    chunks = _KB.search(question, top_k=max(1, top_k))
    if not chunks:
        return "I could not find relevant information in the knowledge base."

    context = "\n\n".join(
        f"[Source: {c.source}]\n{c.text}" for c in chunks
    )
    system_prompt = (
        "You are a precise knowledge-base assistant. Answer the user's "
        "question using ONLY the provided context passages. If the context "
        "does not contain enough information to answer, say so honestly. "
        "When possible, mention the source file names."
    )
    user_prompt = (
        f"Context passages:\n{context}\n\n"
        f"Question: {question}\n\nAnswer:"
    )

    err = _require_key()
    if err:
        return err
    try:
        answer = _HY3.chat(system_prompt, user_prompt, temperature=0.2)
    except Exception as exc:  # surface API errors to the client
        return f"Hy3 API call failed: {exc}"

    if include_sources:
        return f"{answer.strip()}\n\n---\nSources:\n" + _render_sources(chunks)
    return answer.strip()


@mcp.tool()
def summarize_document(path: str) -> str:
    """Summarize a single document using the Hy3 model.

    Reads and summarizes the file at `path` (txt/md/csv). The file does not
    need to be loaded into the knowledge base first.

    Args:
        path: Path to the document to summarize.

    Returns:
        A concise summary generated by Hy3.
    """
    from .parsers import parse_file

    try:
        doc = parse_file(path)
    except UnsupportedFileType as exc:
        return str(exc)
    except FileNotFoundError:
        return f"File not found: {path}"

    system_prompt = (
        "You are a documentation assistant. Produce a concise, well-structured "
        "summary of the given document. Use bullet points where helpful."
    )
    user_prompt = f"Document ({doc.path}):\n\n{doc.content[:20000]}"
    err = _require_key()
    if err:
        return err
    try:
        return _HY3.chat(system_prompt, user_prompt, temperature=0.3)
    except Exception as exc:
        return f"Hy3 API call failed: {exc}"


@mcp.tool()
def chat_hy3(message: str, system_prompt: str = "", temperature: float = 0.7) -> str:
    """Chat directly with the Hy3 model (general-purpose reasoning).

    A thin pass-through to the Hy3 Chat Completions API for open-ended tasks
    that do not require the knowledge base.

    Args:
        message: The user message.
        system_prompt: Optional system instruction to steer the model.
        temperature: Sampling temperature, 0.0-1.0 (default 0.7).

    Returns:
        The model's reply.
    """
    err = _require_key()
    if err:
        return err
    sys_p = system_prompt or "You are a helpful assistant powered by Hy3."
    try:
        return _HY3.chat(sys_p, message, temperature=max(0.0, min(1.0, temperature)))
    except Exception as exc:
        return f"Hy3 API call failed: {exc}"


def main() -> None:
    """Console-script entry point."""
    mcp.run()


if __name__ == "__main__":
    main()
