"""MCP 工具结果的确定性文本渲染。"""

from pydantic import BaseModel

from .models import (
    AskResult,
    IndexDocumentsResult,
    ListSourcesResult,
    SearchResult,
    SummaryResult,
)


def render_json(result: BaseModel) -> str:
    """使用 Pydantic 的稳定 JSON 序列化。"""
    return result.model_dump_json(indent=2)


def render_search_markdown(result: SearchResult) -> str:
    lines = [f"# Search results for: {result.query}", ""]
    for item in result.results:
        location = item.source_path.as_posix()
        if item.page_number is not None:
            location += f":page-{item.page_number}"
        elif item.line_start is not None:
            location += f":lines-{item.line_start}-{item.line_end or item.line_start}"
        lines.extend([f"## [{item.evidence_id}] {location}", "", item.snippet, ""])
    return "\n".join(lines).rstrip()


def render_ask_markdown(result: AskResult) -> str:
    lines = [result.answer, "", "## Citations"]
    if not result.citations:
        lines.append("- No supporting source was found.")
    for item in result.citations:
        location = item.source_path.as_posix()
        if item.page_number is not None:
            location += f", page {item.page_number}"
        elif item.line_start is not None:
            location += f", lines {item.line_start}-{item.line_end or item.line_start}"
        lines.append(f"- [{item.evidence_id}] {location}")
    return "\n".join(lines)


def render_index_markdown(result: IndexDocumentsResult) -> str:
    lines = [
        f"# Indexed collection: {result.collection}",
        "",
        f"- Discovered: {result.discovered_sources}",
        f"- Indexed: {result.indexed_sources}",
        f"- Updated: {result.updated_sources}",
        f"- Unchanged: {result.unchanged_sources}",
        f"- Skipped: {result.skipped_sources}",
        f"- Failed: {result.failed_sources}",
        f"- Chunks: {result.chunk_count}",
    ]
    for error in result.errors:
        lines.append(f"- Error {error.source_path.as_posix()}: {error.reason}")
    return "\n".join(lines)


def render_summary_markdown(result: SummaryResult) -> str:
    lines = [result.summary, "", f"Coverage: {result.coverage}", "", "## Citations"]
    for item in result.citations:
        location = item.source_path.as_posix()
        if item.page_number is not None:
            location += f", page {item.page_number}"
        elif item.line_start is not None:
            location += f", lines {item.line_start}-{item.line_end or item.line_start}"
        lines.append(f"- [{item.evidence_id}] {location}")
    return "\n".join(lines)


def render_list_sources_markdown(result: ListSourcesResult) -> str:
    lines = [
        f"# Indexed sources ({result.total})",
        "",
        f"Offset: {result.offset}; count: {result.count}; has_more: {result.has_more}",
        "",
    ]
    for source in result.sources:
        lines.append(
            f"- {source.source_path.as_posix()} "
            f"({source.source_format.value}, {source.size_bytes} bytes, "
            f"{source.chunk_count} chunks, pages={source.page_count or '-'}, "
            f"sha256-prefix={source.content_sha256_prefix}, indexed={source.indexed_at})"
        )
    return "\n".join(lines)
