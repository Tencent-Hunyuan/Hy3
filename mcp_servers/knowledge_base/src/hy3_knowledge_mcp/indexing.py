"""增量索引编排。"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable
from typing import TypeVar

from .chunking import chunk_document
from .config import Settings
from .errors import LimitExceededError, PathNotAllowedError, UnsupportedFileError
from .models import (
    AllowedRoot,
    IndexDocumentsRequest,
    IndexDocumentsResult,
    IndexFileError,
    PreparedSource,
    ResolvedSource,
)
from .parsers import parse_document
from .paths import discover_source_files, read_validated_bytes, resolve_requested_path
from .store import SourceRefreshState, SQLiteStore

_T = TypeVar("_T")


def prepare_source(source: ResolvedSource, data: bytes, settings: Settings) -> PreparedSource:
    """从同一不可变字节缓冲区完成解析、分块与摘要。"""
    document = parse_document(source, data, max_pdf_pages=settings.max_pdf_pages)
    chunks = chunk_document(
        document,
        max_chars=settings.chunk_chars,
        overlap_chars=settings.chunk_overlap_chars,
    )
    return PreparedSource(
        source=source,
        content_sha256=hashlib.sha256(data).hexdigest(),
        source_format=document.source_format,
        page_count=document.page_count,
        chunks=chunks,
    )


class IndexingService:
    """串行编排受限发现、准备和事务写入。"""

    def __init__(
        self,
        settings: Settings,
        roots: tuple[AllowedRoot, ...],
        store: SQLiteStore,
    ) -> None:
        self.settings = settings
        self.roots = roots
        self.store = store
        self._lock = asyncio.Lock()

    async def index(self, request: IndexDocumentsRequest) -> IndexDocumentsResult:
        """串行执行一次增量或全量替换索引。"""
        async with self._lock:
            target = await self._to_thread(resolve_requested_path, request.path, self.roots)
            sources = await self._to_thread(
                discover_source_files,
                target,
                recursive=request.recursive,
                include_globs=request.include_globs,
                max_files=self.settings.max_files_per_run,
                max_total_bytes=self.settings.max_total_bytes_per_run,
                max_entries=self.settings.max_discovery_entries,
                max_directories=self.settings.max_discovery_directories,
                max_depth=self.settings.max_discovery_depth,
            )

            prepared: list[tuple[PreparedSource, bool]] = []
            errors: list[IndexFileError] = []
            unchanged = 0
            for source in sources:
                try:
                    data = await self._to_thread(
                        read_validated_bytes,
                        source,
                        max_bytes=self.settings.max_file_bytes,
                    )
                    digest = hashlib.sha256(data).hexdigest()
                    if request.replace:
                        item = await self._to_thread(prepare_source, source, data, self.settings)
                        prepared.append((item, False))
                        continue
                    state = await self._to_thread(
                        self.store.classify_and_refresh_source,
                        request.collection,
                        source.source_path,
                        digest,
                        source.mtime_ns,
                        source.size_bytes,
                    )
                    if state is SourceRefreshState.UNCHANGED:
                        unchanged += 1
                        continue
                    item = await self._to_thread(prepare_source, source, data, self.settings)
                    prepared.append((item, state is SourceRefreshState.CHANGED))
                except (
                    PathNotAllowedError,
                    UnsupportedFileError,
                    LimitExceededError,
                    OSError,
                    ValueError,
                ) as error:
                    errors.append(self._file_error(source, self._safe_reason(error)))

            if request.replace:
                if errors:
                    return self._result(request, sources, 0, 0, unchanged, 0, errors)
                items = tuple(item for item, _ in prepared)
                try:
                    await self._to_thread(
                        self.store.replace_collection,
                        request.collection,
                        items,
                        allow_empty=True,
                    )
                except ValueError:
                    errors.extend(
                        self._file_error(item.source, "无法写入来源索引") for item in items
                    )
                    return self._result(request, sources, 0, 0, unchanged, 0, errors)
                return self._result(
                    request,
                    sources,
                    len(items),
                    0,
                    unchanged,
                    sum(len(item.chunks) for item in items),
                    errors,
                )

            indexed = 0
            updated = 0
            chunk_count = 0
            for item, existed in prepared:
                try:
                    await self._to_thread(
                        self.store.replace_prepared_source,
                        request.collection,
                        item,
                    )
                except ValueError:
                    errors.append(self._file_error(item.source, "无法写入来源索引"))
                    continue
                if existed:
                    updated += 1
                else:
                    indexed += 1
                chunk_count += len(item.chunks)
            return self._result(
                request,
                sources,
                indexed,
                updated,
                unchanged,
                chunk_count,
                errors,
            )

    @staticmethod
    async def _to_thread(function: Callable[..., _T], /, *args: object, **kwargs: object) -> _T:
        """取消时等待已启动线程结束。避免在线程仍写库时释放索引锁。"""
        task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
        cancellation: asyncio.CancelledError | None = None
        while True:
            try:
                result = await asyncio.shield(task)
            except asyncio.CancelledError as error:
                if cancellation is None:
                    cancellation = error
                if task.cancelled():
                    raise cancellation from None
                continue
            except Exception:
                if cancellation is None:
                    raise
                raise cancellation from None
            if cancellation is not None:
                raise cancellation
            return result

    @staticmethod
    def _safe_reason(error: BaseException) -> str:
        """将来源错误归一为不含绝对路径或底层实现细节的原因。"""
        if isinstance(error, PathNotAllowedError):
            return "无法安全访问来源"
        if isinstance(error, LimitExceededError):
            return "来源超过安全限制"
        if isinstance(error, UnsupportedFileError):
            return "来源格式或内容不受支持"
        if isinstance(error, OSError):
            return "无法读取来源"
        return "来源无法解析或分块"

    @staticmethod
    def _file_error(source: ResolvedSource, reason: str) -> IndexFileError:
        """创建只包含公开相对路径的错误。"""
        return IndexFileError(source_path=source.source_path, reason=reason)

    @staticmethod
    def _result(
        request: IndexDocumentsRequest,
        sources: tuple[ResolvedSource, ...],
        indexed: int,
        updated: int,
        unchanged: int,
        chunk_count: int,
        errors: list[IndexFileError],
    ) -> IndexDocumentsResult:
        """构建错误排序稳定且统计仅含成功提交的结果。"""
        ordered = tuple(sorted(errors, key=lambda item: item.source_path.as_posix()))
        return IndexDocumentsResult(
            collection=request.collection,
            discovered_sources=len(sources),
            indexed_sources=indexed,
            updated_sources=updated,
            unchanged_sources=unchanged,
            skipped_sources=0,
            failed_sources=len(ordered),
            chunk_count=chunk_count,
            errors=ordered,
        )
