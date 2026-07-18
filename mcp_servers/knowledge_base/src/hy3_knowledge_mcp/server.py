"""Hy3 本地知识库 MCP stdio server。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Annotated

import anyio
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.session import ServerSession
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BeforeValidator, Field, ValidationError, WithJsonSchema

from .config import Settings
from .errors import KnowledgeBaseError
from .models import (
    COLLECTION_PATTERN,
    AskRequest,
    AskResult,
    IndexDocumentsRequest,
    IndexDocumentsResult,
    ListSourcesRequest,
    ListSourcesResult,
    ReasoningEffort,
    ResponseFormat,
    SearchRequest,
    SearchResult,
    StrictModel,
    SummarizeSourceRequest,
    SummaryResult,
)
from .paths import build_allowed_roots
from .renderers import (
    render_ask_markdown,
    render_index_markdown,
    render_list_sources_markdown,
    render_search_markdown,
    render_summary_markdown,
)
from .services import KnowledgeBaseService
from .store import SQLiteStore


def _reject_source_path_controls(value: object) -> object:
    """在 FastMCP 调用工具函数前拒绝来源路径控制字符。"""
    if isinstance(value, str) and any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise ValueError("来源路径不得包含控制字符")
    return value


ToolSourcePath = Annotated[
    str,
    BeforeValidator(_reject_source_path_controls),
    Field(min_length=1, max_length=4096),
    WithJsonSchema({"type": "string", "minLength": 1, "maxLength": 4096}),
]


@dataclass
class AppContext:
    """单个 MCP session 独占的配置与业务服务。"""

    settings: Settings
    service: KnowledgeBaseService


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    """在 session 生命周期内初始化并可靠关闭业务服务。"""
    settings = Settings.from_env()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    store = SQLiteStore(settings.storage_dir / "index.sqlite3")
    store.initialize()
    service = KnowledgeBaseService(
        settings=settings,
        roots=build_allowed_roots(settings.allowed_root_paths),
        store=store,
    )
    try:
        yield AppContext(settings=settings, service=service)
    finally:
        # MCP server teardown 会取消所属 task, 关闭远端 client 必须完整执行。
        with anyio.CancelScope(shield=True):
            await service.close()


mcp = FastMCP(
    "hy3_knowledge_mcp",
    lifespan=app_lifespan,
    log_level="WARNING",
)


def _tool_result(payload: StrictModel, text: str) -> CallToolResult:
    """同时返回人类可读文本和严格结构化业务载荷。"""
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structuredContent=payload.model_dump(mode="json"),
    )


def _service(ctx: Context[ServerSession, AppContext]) -> KnowledgeBaseService:
    """取得当前 session 的业务服务。"""
    return ctx.request_context.lifespan_context.service


def _safe_error(exc: KnowledgeBaseError) -> ToolError:
    """将领域错误转换为无异常链泄露的 MCP 工具错误。"""
    return ToolError(str(exc))


def _invalid_arguments() -> ToolError:
    """隐藏业务请求模型的内部校验细节与原始输入。"""
    return ToolError("Invalid tool arguments")


@mcp.tool(
    name="hy3_kb_index_documents",
    title="Index local documents for Hy3 knowledge retrieval",
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def hy3_kb_index_documents(
    collection: Annotated[str, Field(pattern=COLLECTION_PATTERN)],
    path: Annotated[str, Field(min_length=1, max_length=4096)],
    ctx: Context[ServerSession, AppContext],
    recursive: bool = True,
    replace: bool = False,
    include_globs: Annotated[list[str] | None, Field(max_length=20)] = None,
) -> Annotated[CallToolResult, IndexDocumentsResult]:
    """索引本地文档, 但不修改来源文件。"""
    try:
        payload = await _service(ctx).index(
            IndexDocumentsRequest(
                collection=collection,
                path=path,
                recursive=recursive,
                replace=replace,
                include_globs=tuple(include_globs or ()),
            )
        )
        return _tool_result(payload, render_index_markdown(payload))
    except ValidationError:
        raise _invalid_arguments() from None
    except KnowledgeBaseError as exc:
        raise _safe_error(exc) from None


@mcp.tool(
    name="hy3_kb_search",
    title="Search indexed Hy3 knowledge sources",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def hy3_kb_search(
    collection: Annotated[str, Field(pattern=COLLECTION_PATTERN)],
    query: Annotated[str, Field(min_length=1, max_length=1000)],
    ctx: Context[ServerSession, AppContext],
    limit: Annotated[int, Field(ge=1, le=20)] = 8,
    offset: Annotated[int, Field(ge=0)] = 0,
    source_paths: Annotated[list[ToolSourcePath] | None, Field(max_length=20)] = None,
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> Annotated[CallToolResult, SearchResult]:
    """完全在本地索引中检索, 不向 Hy3 发送文档内容。"""
    try:
        payload = await _service(ctx).search(
            SearchRequest(
                collection=collection,
                query=query,
                limit=limit,
                offset=offset,
                source_paths=tuple(PurePosixPath(item) for item in source_paths or ()),
                response_format=response_format,
            )
        )
        text = (
            render_search_markdown(payload)
            if response_format is ResponseFormat.MARKDOWN
            else payload.model_dump_json(indent=2)
        )
        return _tool_result(payload, text)
    except ValidationError:
        raise _invalid_arguments() from None
    except KnowledgeBaseError as exc:
        raise _safe_error(exc) from None


@mcp.tool(
    name="hy3_kb_ask",
    title="Ask Hy3 using indexed evidence",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def hy3_kb_ask(
    collection: Annotated[str, Field(pattern=COLLECTION_PATTERN)],
    question: Annotated[str, Field(min_length=1, max_length=4000)],
    ctx: Context[ServerSession, AppContext],
    top_k: Annotated[int, Field(ge=1, le=12)] = 8,
    source_paths: Annotated[list[ToolSourcePath] | None, Field(max_length=20)] = None,
    reasoning_effort: ReasoningEffort | None = None,
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> Annotated[CallToolResult, AskResult]:
    """检索证据并请求 Hy3 生成经过引用校验的回答。"""
    try:
        payload = await _service(ctx).ask(
            AskRequest(
                collection=collection,
                question=question,
                top_k=top_k,
                source_paths=tuple(PurePosixPath(item) for item in source_paths or ()),
                reasoning_effort=reasoning_effort,
                response_format=response_format,
            )
        )
        text = (
            render_ask_markdown(payload)
            if response_format is ResponseFormat.MARKDOWN
            else payload.model_dump_json(indent=2)
        )
        return _tool_result(payload, text)
    except ValidationError:
        raise _invalid_arguments() from None
    except KnowledgeBaseError as exc:
        raise _safe_error(exc) from None


@mcp.tool(
    name="hy3_kb_summarize_source",
    title="Summarize one indexed source with Hy3",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def hy3_kb_summarize_source(
    collection: Annotated[str, Field(pattern=COLLECTION_PATTERN)],
    source_path: ToolSourcePath,
    ctx: Context[ServerSession, AppContext],
    focus: Annotated[str | None, Field(max_length=2000)] = None,
    reasoning_effort: ReasoningEffort | None = None,
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> Annotated[CallToolResult, SummaryResult]:
    """总结单一来源并校验模型返回的全部证据编号。"""
    try:
        payload = await _service(ctx).summarize(
            SummarizeSourceRequest(
                collection=collection,
                source_path=PurePosixPath(source_path),
                focus=focus,
                reasoning_effort=reasoning_effort,
                response_format=response_format,
            )
        )
        text = (
            render_summary_markdown(payload)
            if response_format is ResponseFormat.MARKDOWN
            else payload.model_dump_json(indent=2)
        )
        return _tool_result(payload, text)
    except ValidationError:
        raise _invalid_arguments() from None
    except KnowledgeBaseError as exc:
        raise _safe_error(exc) from None


@mcp.tool(
    name="hy3_kb_list_sources",
    title="List indexed knowledge sources",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def hy3_kb_list_sources(
    collection: Annotated[str, Field(pattern=COLLECTION_PATTERN)],
    ctx: Context[ServerSession, AppContext],
    query: Annotated[str | None, Field(max_length=1000)] = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
    offset: Annotated[int, Field(ge=0)] = 0,
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> Annotated[CallToolResult, ListSourcesResult]:
    """列出本地索引来源, 不联系 Hy3。"""
    try:
        payload = await _service(ctx).list_sources(
            ListSourcesRequest(
                collection=collection,
                query=query,
                limit=limit,
                offset=offset,
                response_format=response_format,
            )
        )
        text = (
            render_list_sources_markdown(payload)
            if response_format is ResponseFormat.MARKDOWN
            else payload.model_dump_json(indent=2)
        )
        return _tool_result(payload, text)
    except ValidationError:
        raise _invalid_arguments() from None
    except KnowledgeBaseError as exc:
        raise _safe_error(exc) from None


def main() -> None:
    """以 stdio transport 启动 MCP server。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
