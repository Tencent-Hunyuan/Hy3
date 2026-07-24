"""Hy3 Knowledge Base Q&A MCP Server.

An MCP Server that provides knowledge base Q&A capabilities
powered by Tencent Hunyuan Hy3 model.
"""

import os
import sys
import time
import logging
import glob as glob_module
from pathlib import Path

from fastmcp import FastMCP
from dotenv import load_dotenv

# Logging: stderr + file (stdout is reserved for MCP protocol in stdio mode)
# The file handler ensures logs are visible even when the server is spawned
# as a subprocess by an MCP client (e.g. WorkBuddy/Cursor), where stderr
# is captured by the client and not shown in any console.
_log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("hy3-mcp")
logger.setLevel(logging.INFO)

# stderr handler
_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setFormatter(_log_format)
logger.addHandler(_stderr_handler)

# File handler — writes to a fixed path so you can `tail -f` it from any terminal
_log_file = Path.home() / ".hy3-mcp-server.log"
try:
    _file_handler = logging.FileHandler(str(_log_file), encoding="utf-8")
    _file_handler.setFormatter(_log_format)
    logger.addHandler(_file_handler)
except Exception:
    pass  # don't crash the server if log file can't be created

from .hy3_client import chat
from .search_client import web_search

# Load .env file: try current dir first, then package parent dirs
load_dotenv()
_package_dir = Path(__file__).resolve().parent
for _parent in [_package_dir, *_package_dir.parents]:
    if (_parent / ".env").exists():
        load_dotenv(_parent / ".env")
        break

mcp = FastMCP(
    "hy3-knowledge-base",
    instructions=(
        "You are a knowledge base Q&A assistant powered by Tencent Hunyuan Hy3. "
        "You can read local documents, answer questions based on their content, "
        "summarize documents, search across files to find relevant information, "
        "search the web for up-to-date information, and compare documents. "
        "Always use the provided tools to access document or web content before answering."
    ),
)

# Supported text file extensions
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".log", ".py", ".js", ".ts", ".html", ".css", ".ini", ".cfg", ".toml"}


def _read_file_content(file_path: str) -> str:
    """Read file content, supporting text files, PDFs, and DOCX."""
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    suffix = path.suffix.lower()

    if suffix in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    if suffix == ".docx":
        from docx import Document
        doc = Document(str(path))
        return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())

    # Fallback: try reading as text
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        raise ValueError(f"Unsupported file format: {suffix}")


def _truncate(text: str, max_chars: int = 50000) -> str:
    """Truncate text to max_chars with an indicator."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n... [Truncated, total {len(text)} characters]"


@mcp.tool()
def read_file(file_path: str, max_chars: int = 50000) -> str:
    """Read and extract text content from a local file.

    Supports plain text (.txt, .md, .csv, .json, .py, etc.),
    PDF (.pdf), and Word (.docx) files.

    Args:
        file_path: Absolute or relative path to the file to read.
        max_chars: Maximum characters to return. Defaults to 50000.

    Returns:
        The text content of the file.
    """
    logger.info(f"TOOL CALLED: read_file(file_path={file_path!r}, max_chars={max_chars})")
    t0 = time.time()
    content = _read_file_content(file_path)
    result = _truncate(content, max_chars)
    logger.info(f"TOOL DONE: read_file -> {len(result)} chars in {time.time()-t0:.2f}s")
    return result


@mcp.tool()
def ask_about_documents(file_paths: list[str], question: str, reasoning_effort: str = "high") -> str:
    """Ask a question about the content of one or more documents, answered by Hy3.

    Reads the specified documents, then sends the content along with
    the question to the Hy3 model for an accurate, context-grounded answer.

    Args:
        file_paths: List of file paths to read as context.
        question: The question to ask about the documents.
        reasoning_effort: Reasoning depth - "no_think" (fast), "low", or "high" (deep). Defaults to "high".

    Returns:
        Hy3's answer based on the document content.
    """
    logger.info(f"TOOL CALLED: ask_about_documents(files={file_paths}, question={question!r}, reasoning={reasoning_effort})")
    t0 = time.time()
    documents = []
    for fp in file_paths:
        try:
            content = _read_file_content(fp)
            documents.append(f"--- Document: {fp} ---\n{_truncate(content, 30000)}")
        except Exception as e:
            documents.append(f"--- Document: {fp} ---\n[Error reading file: {e}]")

    combined = "\n\n".join(documents)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a knowledgeable assistant. Answer the user's question "
                "strictly based on the provided document content. "
                "If the answer cannot be found in the documents, say so clearly. "
                "Cite the relevant document name when referencing information."
            ),
        },
        {
            "role": "user",
            "content": f"Here are the documents:\n\n{combined}\n\nQuestion: {question}",
        },
    ]

    result = chat(messages, temperature=0.3, reasoning_effort=reasoning_effort)
    logger.info(f"TOOL DONE: ask_about_documents -> {len(result)} chars in {time.time()-t0:.2f}s")
    return result


@mcp.tool()
def summarize_document(file_path: str, summary_type: str = "comprehensive", max_length: int = 500) -> str:
    """Summarize a document using Hy3.

    Reads a document and generates a summary with customizable style and length.

    Args:
        file_path: Path to the document to summarize.
        summary_type: Type of summary - "comprehensive" (detailed), "brief" (key points only), or "bullet" (bullet points). Defaults to "comprehensive".
        max_length: Target maximum word count for the summary. Defaults to 500.

    Returns:
        A summary of the document generated by Hy3.
    """
    logger.info(f"TOOL CALLED: summarize_document(file_path={file_path!r}, type={summary_type}, max_length={max_length})")
    t0 = time.time()
    content = _read_file_content(file_path)

    type_instructions = {
        "comprehensive": "Provide a comprehensive summary covering all major topics and key details.",
        "brief": "Provide a brief summary focusing only on the most important key points.",
        "bullet": "Provide a bullet-point summary listing the key takeaways.",
    }

    instruction = type_instructions.get(summary_type, type_instructions["comprehensive"])

    messages = [
        {
            "role": "system",
            "content": f"You are a skilled summarizer. {instruction} Target length: around {max_length} words. Write in the same language as the source document.",
        },
        {
            "role": "user",
            "content": f"Please summarize the following document:\n\n{_truncate(content, 50000)}",
        },
    ]

    result = chat(messages, temperature=0.5, reasoning_effort="low")
    logger.info(f"TOOL DONE: summarize_document -> {len(result)} chars in {time.time()-t0:.2f}s")
    return result


@mcp.tool()
def search_files_and_answer(directory: str, query: str, file_pattern: str = "*", max_files: int = 10) -> str:
    """Search for files in a directory and answer a question based on their content.

    Scans a directory for files matching a pattern, reads their content,
    and uses Hy3 to answer the query based on relevant findings.

    Args:
        directory: Directory path to search in.
        query: The question or topic to search for and answer.
        file_pattern: Glob pattern to filter files (e.g. "*.py", "*.md", "*.txt"). Defaults to "*".
        max_files: Maximum number of files to read. Defaults to 10.

    Returns:
        Hy3's answer based on the relevant files found.
    """
    logger.info(f"TOOL CALLED: search_files_and_answer(directory={directory!r}, query={query!r}, pattern={file_pattern!r})")
    t0 = time.time()
    dir_path = Path(directory).expanduser().resolve()

    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {dir_path}")

    # Collect matching files
    all_extensions = list(TEXT_EXTENSIONS | {".pdf", ".docx"})
    if file_pattern != "*":
        matched = list(dir_path.rglob(file_pattern))
    else:
        matched = []
        for ext in all_extensions:
            matched.extend(dir_path.rglob(f"*{ext}"))

    # Sort by modification time (most recent first)
    matched.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    matched = matched[:max_files]

    if not matched:
        logger.info(f"TOOL DONE: search_files_and_answer -> no files found in {time.time()-t0:.2f}s")
        return f"No matching files found in {dir_path} with pattern '{file_pattern}'"

    logger.info(f"  Found {len(matched)} files, reading content...")
    # Read file contents
    documents = []
    for fpath in matched:
        try:
            content = _read_file_content(str(fpath))
            # Truncate each file to save context window
            documents.append(f"--- {fpath.relative_to(dir_path)} ---\n{_truncate(content, 5000)}")
        except Exception as e:
            documents.append(f"--- {fpath.relative_to(dir_path)} ---\n[Error: {e}]")

    combined = "\n\n".join(documents)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a research assistant. Based on the files found in the directory, "
                "answer the user's query. Focus on the most relevant information. "
                "If the files don't contain relevant information, say so."
            ),
        },
        {
            "role": "user",
            "content": f"Files from directory '{directory}':\n\n{combined}\n\nQuery: {query}",
        },
    ]

    result = chat(messages, temperature=0.3, reasoning_effort="high")
    logger.info(f"TOOL DONE: search_files_and_answer -> {len(result)} chars in {time.time()-t0:.2f}s")
    return result


@mcp.tool()
def web_search_and_answer(query: str, max_results: int = 5, reasoning_effort: str = "high") -> str:
    """Search the web for information and use Hy3 to answer a question.

    Performs a web search using Tavily Search API, then sends the search
    results along with the query to Hy3 for a comprehensive, up-to-date answer.
    This tool is ideal for questions about current events, recent developments,
    or topics where local documents may not have the latest information.

    Args:
        query: The question or topic to search for on the web.
        max_results: Maximum number of search results to include (1-10). Defaults to 5.
        reasoning_effort: Reasoning depth - "no_think" (fast), "low", or "high" (deep). Defaults to "high".

    Returns:
        Hy3's answer based on the web search results.
    """
    logger.info(f"TOOL CALLED: web_search_and_answer(query={query!r}, max_results={max_results})")
    t0 = time.time()
    results = web_search(query, max_results=max_results)

    if not results:
        logger.info(f"TOOL DONE: web_search_and_answer -> no results in {time.time()-t0:.2f}s")
        return f"No web search results found for: {query}"

    logger.info(f"  Got {len(results)} search results, sending to Hy3...")
    # Format search results
    snippets = []
    for i, r in enumerate(results, 1):
        snippets.append(
            f"[{i}] {r['title']}\n"
            f"URL: {r['url']}\n"
            f"{r['content']}"
        )
    combined = "\n\n".join(snippets)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a research assistant with access to web search results. "
                "Answer the user's question based on the provided search results. "
                "Cite the source URL when referencing information. "
                "If the search results don't contain enough information, say so and suggest what to search for. "
                "Always indicate when information comes from web sources versus your training data."
            ),
        },
        {
            "role": "user",
            "content": f"Web search results for '{query}':\n\n{combined}\n\nQuestion: {query}",
        },
    ]

    result = chat(messages, temperature=0.3, reasoning_effort=reasoning_effort)
    logger.info(f"TOOL DONE: web_search_and_answer -> {len(result)} chars in {time.time()-t0:.2f}s")
    return result


@mcp.tool()
def compare_documents(file_paths: list[str], aspect: str = "general", reasoning_effort: str = "high") -> str:
    """Compare two or more documents and analyze their differences using Hy3.

    Reads the specified documents, then uses Hy3 to compare them from a
    specified perspective. Useful for finding contradictions, identifying
    unique points in each document, or tracking changes across versions.

    Args:
        file_paths: List of file paths to compare (minimum 2 files).
        aspect: What aspect to compare - "general" (overall comparison), "differences" (focus on differences), "agreements" (focus on commonalities), or "contradictions" (focus on conflicting information). Defaults to "general".
        reasoning_effort: Reasoning depth - "no_think" (fast), "low", or "high" (deep). Defaults to "high".

    Returns:
        Hy3's comparative analysis of the documents.
    """
    logger.info(f"TOOL CALLED: compare_documents(files={file_paths}, aspect={aspect!r})")
    t0 = time.time()
    if len(file_paths) < 2:
        raise ValueError("At least 2 file paths are required for comparison.")

    documents = []
    for fp in file_paths:
        try:
            content = _read_file_content(fp)
            documents.append(f"--- Document: {fp} ---\n{_truncate(content, 20000)}")
        except Exception as e:
            documents.append(f"--- Document: {fp} ---\n[Error reading file: {e}]")

    combined = "\n\n".join(documents)

    aspect_instructions = {
        "general": "Provide a general comparison covering similarities, differences, and unique points of each document.",
        "differences": "Focus on identifying and explaining the key differences between the documents.",
        "agreements": "Focus on identifying the common points and agreements across the documents.",
        "contradictions": "Focus on finding any contradictory or conflicting information between the documents.",
    }

    instruction = aspect_instructions.get(aspect, aspect_instructions["general"])

    messages = [
        {
            "role": "system",
            "content": (
                f"You are an analytical assistant skilled at document comparison. {instruction} "
                "Always reference which document specific information comes from. "
                "Structure your comparison clearly with sections."
            ),
        },
        {
            "role": "user",
            "content": f"Please compare the following documents:\n\n{combined}",
        },
    ]

    result = chat(messages, temperature=0.3, reasoning_effort=reasoning_effort)
    logger.info(f"TOOL DONE: compare_documents -> {len(result)} chars in {time.time()-t0:.2f}s")
    return result


def main():
    """Entry point for the MCP server."""
    logger.info("=" * 50)
    logger.info("Hy3 Knowledge Base MCP Server starting (stdio mode)...")
    logger.info(f"  Hy3 API Key: {'set' if os.environ.get('HY3_API_KEY') else 'MISSING'}")
    logger.info(f"  Tavily API Key: {'set' if os.environ.get('TAVILY_API_KEY') else 'not set (web search disabled)'}")
    logger.info(f"  Log file: {_log_file}")
    logger.info("=" * 50)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
