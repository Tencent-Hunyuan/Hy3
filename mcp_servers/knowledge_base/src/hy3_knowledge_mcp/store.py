"""SQLite 外部内容 FTS5 知识库存储。"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, NoReturn

from .errors import (
    FtsUnavailableError,
    IndexNotFoundError,
    KnowledgeBaseError,
    SourceNotFoundError,
)
from .models import (
    COLLECTION_PATTERN,
    ChunkDraft,
    ListSourcesResult,
    PreparedSource,
    RetrievedChunk,
    RetrievedPage,
    SourceFormat,
    SourceInfo,
    StoredFingerprint,
)

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    root_id TEXT NOT NULL CHECK(length(root_id) = 12),
    relative_path TEXT NOT NULL CHECK(length(relative_path) > 0),
    content_sha256 TEXT NOT NULL
        CHECK(length(content_sha256) = 64 AND content_sha256 NOT GLOB '*[^0-9a-f]*'),
    mtime_ns INTEGER NOT NULL CHECK(mtime_ns >= 0),
    size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
    format TEXT NOT NULL CHECK(format IN ('markdown', 'text', 'rst', 'pdf')),
    page_count INTEGER CHECK(page_count IS NULL OR page_count >= 1),
    status TEXT NOT NULL DEFAULT 'ready' CHECK(status = 'ready'),
    indexed_at TEXT NOT NULL,
    UNIQUE(collection_id, root_id, relative_path)
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
    text TEXT NOT NULL CHECK(length(text) > 0),
    page_number INTEGER CHECK(page_number IS NULL OR page_number >= 1),
    line_start INTEGER CHECK(line_start IS NULL OR line_start >= 1),
    line_end INTEGER CHECK(line_end IS NULL OR line_end >= 1),
    char_count INTEGER NOT NULL CHECK(char_count > 0 AND char_count = length(text)),
    UNIQUE(source_id, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_sources_collection_path
ON sources(collection_id, root_id, relative_path);
CREATE INDEX IF NOT EXISTS idx_chunks_source_ordinal
ON chunks(source_id, ordinal);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id',
    tokenize='trigram'
);
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, text)
  VALUES ('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, text)
  VALUES ('delete', old.id, old.text);
  INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
PRAGMA user_version = 1;
"""

_COLLECTION_RE = re.compile(COLLECTION_PATTERN)
_ROOT_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_FTS_UNAVAILABLE_MARKERS = (
    "no such module: fts5",
    "no such tokenizer",
    "error in tokenizer constructor",
)
_INDEX_NOT_FOUND_MESSAGE = "知识库集合不存在; 请先调用 hy3_kb_index_documents 创建本地索引"


class SourceRefreshState(Enum):
    """增量来源在单一数据库事务快照中的分类。"""

    MISSING = auto()
    UNCHANGED = auto()
    CHANGED = auto()


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符与转义符本身。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _validate_collection(collection: str) -> None:
    """在任何 SQL 执行前验证集合名。"""
    if not isinstance(collection, str) or _COLLECTION_RE.fullmatch(collection) is None:
        raise ValueError("collection 格式无效")


def _validate_relative_path(path: PurePosixPath, *, public: bool) -> PurePosixPath:
    """验证内部相对路径或带 root_id 的公开路径。"""
    if not isinstance(path, PurePosixPath):
        path = PurePosixPath(path)
    windows_path = PureWindowsPath(str(path))
    if (
        path == PurePosixPath(".")
        or path.is_absolute()
        or ".." in path.parts
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or bool(windows_path.root)
        or ".." in windows_path.parts
    ):
        raise ValueError("source path 格式无效")
    if public and (len(path.parts) < 2 or _ROOT_ID_RE.fullmatch(path.parts[0]) is None):
        raise ValueError("source path 格式无效")
    return path


def _split_source_path(source_path: PurePosixPath) -> tuple[str, str]:
    """拆分稳定的 root_id/relative_path 公开键。"""
    path = _validate_relative_path(source_path, public=True)
    return path.parts[0], PurePosixPath(*path.parts[1:]).as_posix()


def _is_fts_unavailable(error: sqlite3.Error) -> bool:
    """仅依据稳定能力错误标记识别 FTS5/trigram 缺失。"""
    message = str(error).lower()
    return any(marker in message for marker in _FTS_UNAVAILABLE_MARKERS)


def _raise_database_error(error: sqlite3.Error) -> NoReturn:
    """将 SQLite 细节映射为不泄露路径或 SQL 的领域异常。"""
    if _is_fts_unavailable(error):
        raise FtsUnavailableError("当前 SQLite 不支持 FTS5 trigram 检索") from None
    raise KnowledgeBaseError("本地知识库操作失败") from None


class SQLiteStore:
    """使用每方法独立连接的 SQLite 知识库存储。"""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        """创建带外键约束和 Row 行工厂的新连接。"""
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self.path, timeout=5.0)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection
        except sqlite3.Error as error:
            if connection is not None:
                connection.close()
            _raise_database_error(error)

    def initialize(self) -> None:
        """幂等创建 schema, 并显式检测 FTS5 trigram 能力。"""
        try:
            with closing(self.connect()) as connection:
                connection.executescript(SCHEMA_SQL)
        except sqlite3.Error as error:
            _raise_database_error(error)

    def replace_source(
        self,
        *,
        collection: str,
        root_id: str,
        relative_path: PurePosixPath,
        content_sha256: str,
        mtime_ns: int,
        size_bytes: int,
        source_format: SourceFormat,
        page_count: int | None,
        chunks: tuple[ChunkDraft, ...],
    ) -> None:
        """在单个事务中替换来源及其全部分块。"""
        _validate_collection(collection)
        if not isinstance(root_id, str) or _ROOT_ID_RE.fullmatch(root_id) is None:
            raise ValueError("root_id 格式无效")
        relative_path = _validate_relative_path(relative_path, public=False)
        if not isinstance(content_sha256, str) or _DIGEST_RE.fullmatch(content_sha256) is None:
            raise ValueError("digest 格式无效")
        if not isinstance(mtime_ns, int) or isinstance(mtime_ns, bool) or mtime_ns < 0:
            raise ValueError("mtime_ns 必须为非负整数")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
            raise ValueError("size_bytes 必须为非负整数")
        if page_count is not None and (
            not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1
        ):
            raise ValueError("page_count 必须为空或正整数")
        if not isinstance(source_format, SourceFormat):
            raise ValueError("source format 格式无效")
        if not chunks:
            raise ValueError("A successfully parsed source must contain at least one chunk")

        now = datetime.now(timezone.utc).isoformat()
        path_text = relative_path.as_posix()
        try:
            with closing(self.connect()) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO collections(name, created_at, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET updated_at=excluded.updated_at
                    """,
                    (collection, now, now),
                )
                collection_row = connection.execute(
                    "SELECT id FROM collections WHERE name=?",
                    (collection,),
                ).fetchone()
                assert collection_row is not None
                collection_id = collection_row["id"]
                connection.execute(
                    """
                    INSERT INTO sources(
                        collection_id, root_id, relative_path, content_sha256,
                        mtime_ns, size_bytes, format, page_count, indexed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(collection_id, root_id, relative_path) DO UPDATE SET
                        content_sha256=excluded.content_sha256,
                        mtime_ns=excluded.mtime_ns,
                        size_bytes=excluded.size_bytes,
                        format=excluded.format,
                        page_count=excluded.page_count,
                        status='ready',
                        indexed_at=excluded.indexed_at
                    """,
                    (
                        collection_id,
                        root_id,
                        path_text,
                        content_sha256,
                        mtime_ns,
                        size_bytes,
                        source_format.value,
                        page_count,
                        now,
                    ),
                )
                source_row = connection.execute(
                    """
                    SELECT id FROM sources
                    WHERE collection_id=? AND root_id=? AND relative_path=?
                    """,
                    (collection_id, root_id, path_text),
                ).fetchone()
                assert source_row is not None
                source_id = source_row["id"]
                connection.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
                connection.executemany(
                    """
                    INSERT INTO chunks(
                        source_id, ordinal, text, page_number,
                        line_start, line_end, char_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        (
                            source_id,
                            chunk.ordinal,
                            chunk.text,
                            chunk.page_number,
                            chunk.line_start,
                            chunk.line_end,
                            chunk.char_count,
                        )
                        for chunk in chunks
                    ),
                )
        except sqlite3.IntegrityError:
            raise ValueError("来源分块违反存储约束") from None
        except sqlite3.Error as error:
            _raise_database_error(error)

    def replace_prepared_source(self, collection: str, prepared: PreparedSource) -> None:
        """在单个事务中写入一个已经完成验证与分块的来源。"""
        if not isinstance(prepared, PreparedSource):
            raise ValueError("prepared source 格式无效")
        self.replace_source(
            collection=collection,
            root_id=prepared.source.root_id,
            relative_path=prepared.source.relative_path,
            content_sha256=prepared.content_sha256,
            mtime_ns=prepared.source.mtime_ns,
            size_bytes=prepared.source.size_bytes,
            source_format=prepared.source_format,
            page_count=prepared.page_count,
            chunks=prepared.chunks,
        )

    def replace_collection(
        self,
        collection: str,
        prepared_sources: tuple[PreparedSource, ...],
        *,
        allow_empty: bool = False,
    ) -> None:
        """在一个事务中清空并完整重建集合。"""
        _validate_collection(collection)
        if not isinstance(prepared_sources, tuple) or not all(
            isinstance(item, PreparedSource) for item in prepared_sources
        ):
            raise ValueError("prepared sources 格式无效")
        if not prepared_sources and not allow_empty:
            raise ValueError("集合替换不得意外为空")
        if any(not item.chunks for item in prepared_sources):
            raise ValueError("成功解析的来源必须至少包含一个分块")
        public_paths = tuple(item.source.source_path for item in prepared_sources)
        if len(set(public_paths)) != len(public_paths):
            raise ValueError("集合包含重复来源")

        now = datetime.now(timezone.utc).isoformat()
        try:
            with closing(self.connect()) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO collections(name, created_at, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET updated_at=excluded.updated_at
                    """,
                    (collection, now, now),
                )
                collection_row = connection.execute(
                    "SELECT id FROM collections WHERE name=?",
                    (collection,),
                ).fetchone()
                assert collection_row is not None
                collection_id = collection_row["id"]
                connection.execute("DELETE FROM sources WHERE collection_id=?", (collection_id,))

                for prepared in prepared_sources:
                    source = prepared.source
                    connection.execute(
                        """
                        INSERT INTO sources(
                            collection_id, root_id, relative_path, content_sha256,
                            mtime_ns, size_bytes, format, page_count, indexed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            collection_id,
                            source.root_id,
                            source.relative_path.as_posix(),
                            prepared.content_sha256,
                            source.mtime_ns,
                            source.size_bytes,
                            prepared.source_format.value,
                            prepared.page_count,
                            now,
                        ),
                    )
                    source_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
                    connection.executemany(
                        """
                        INSERT INTO chunks(
                            source_id, ordinal, text, page_number,
                            line_start, line_end, char_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            (
                                source_id,
                                chunk.ordinal,
                                chunk.text,
                                chunk.page_number,
                                chunk.line_start,
                                chunk.line_end,
                                chunk.char_count,
                            )
                            for chunk in prepared.chunks
                        ),
                    )
        except sqlite3.IntegrityError:
            raise ValueError("集合内容违反存储约束") from None
        except sqlite3.Error as error:
            _raise_database_error(error)

    def get_source_fingerprint(
        self,
        collection: str,
        source_path: PurePosixPath,
    ) -> StoredFingerprint | None:
        """按公开来源键读取指纹; 集合或来源不存在时返回 None。"""
        _validate_collection(collection)
        root_id, relative_path = _split_source_path(source_path)
        try:
            with closing(self.connect()) as connection:
                row = connection.execute(
                    """
                    SELECT sources.content_sha256, sources.mtime_ns, sources.size_bytes
                    FROM sources
                    JOIN collections ON collections.id = sources.collection_id
                    WHERE collections.name=? AND sources.root_id=? AND sources.relative_path=?
                    """,
                    (collection, root_id, relative_path),
                ).fetchone()
        except sqlite3.Error as error:
            _raise_database_error(error)
        if row is None:
            return None
        return StoredFingerprint(
            content_sha256=row["content_sha256"],
            mtime_ns=row["mtime_ns"],
            size_bytes=row["size_bytes"],
        )

    def classify_and_refresh_source(
        self,
        collection: str,
        source_path: PurePosixPath,
        content_sha256: str,
        mtime_ns: int,
        size_bytes: int,
    ) -> SourceRefreshState:
        """在单个写事务中分类来源。仅为相同摘要刷新元数据。"""
        _validate_collection(collection)
        root_id, relative_path = _split_source_path(source_path)
        if not isinstance(content_sha256, str) or _DIGEST_RE.fullmatch(content_sha256) is None:
            raise ValueError("digest 格式无效")
        if not isinstance(mtime_ns, int) or isinstance(mtime_ns, bool) or mtime_ns < 0:
            raise ValueError("mtime_ns 必须为非负整数")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
            raise ValueError("size_bytes 必须为非负整数")

        now = datetime.now(timezone.utc).isoformat()
        try:
            with closing(self.connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT sources.id, sources.collection_id, sources.content_sha256
                    FROM sources
                    JOIN collections ON collections.id = sources.collection_id
                    WHERE collections.name=? AND sources.root_id=? AND sources.relative_path=?
                    """,
                    (collection, root_id, relative_path),
                ).fetchone()
                if row is None:
                    return SourceRefreshState.MISSING
                if row["content_sha256"] != content_sha256:
                    return SourceRefreshState.CHANGED
                connection.execute(
                    """
                    UPDATE sources
                    SET mtime_ns=?, size_bytes=?, indexed_at=?
                    WHERE id=?
                    """,
                    (mtime_ns, size_bytes, now, row["id"]),
                )
                connection.execute(
                    "UPDATE collections SET updated_at=? WHERE id=?",
                    (now, row["collection_id"]),
                )
                return SourceRefreshState.UNCHANGED
        except sqlite3.Error as error:
            _raise_database_error(error)

    def update_source_metadata(
        self,
        collection: str,
        source_path: PurePosixPath,
        mtime_ns: int,
        size_bytes: int,
    ) -> None:
        """仅更新文件系统元数据, 不触碰 chunks 或 FTS。"""
        _validate_collection(collection)
        root_id, relative_path = _split_source_path(source_path)
        if not isinstance(mtime_ns, int) or isinstance(mtime_ns, bool) or mtime_ns < 0:
            raise ValueError("mtime_ns 必须为非负整数")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
            raise ValueError("size_bytes 必须为非负整数")
        now = datetime.now(timezone.utc).isoformat()
        try:
            with closing(self.connect()) as connection, connection:
                cursor = connection.execute(
                    """
                    UPDATE sources
                    SET mtime_ns=?, size_bytes=?, indexed_at=?
                    WHERE collection_id=(SELECT id FROM collections WHERE name=?)
                      AND root_id=? AND relative_path=?
                    """,
                    (mtime_ns, size_bytes, now, collection, root_id, relative_path),
                )
                if cursor.rowcount == 0:
                    raise SourceNotFoundError("指定的知识来源不存在")
                connection.execute(
                    "UPDATE collections SET updated_at=? WHERE name=?",
                    (now, collection),
                )
        except sqlite3.Error as error:
            _raise_database_error(error)

    def search(
        self,
        collection: str,
        fts_query: str | None,
        like_terms: Sequence[str],
        source_paths: Sequence[PurePosixPath],
        limit: int,
        offset: int,
    ) -> RetrievedPage:
        """执行参数化 FTS/LIKE 检索并返回稳定分页。"""
        _validate_collection(collection)
        self._validate_pagination(limit, offset)
        if fts_query is not None and not isinstance(fts_query, str):
            raise ValueError("fts_query 必须为字符串或 None")
        if any(not isinstance(term, str) for term in like_terms):
            raise ValueError("like_terms 必须只包含字符串")
        path_values = tuple(
            _validate_relative_path(path, public=True).as_posix() for path in source_paths
        )
        normalized_fts = fts_query if fts_query else None
        normalized_like = tuple(term for term in like_terms if term)
        try:
            with closing(self.connect()) as connection:
                self._require_collection(connection, collection)
                if normalized_fts:
                    rows, total = self._search_with_fts(
                        connection,
                        collection,
                        normalized_fts,
                        normalized_like,
                        path_values,
                        limit,
                        offset,
                    )
                else:
                    rows, total = self._search_without_fts(
                        connection,
                        collection,
                        normalized_like,
                        path_values,
                        limit,
                        offset,
                    )
        except sqlite3.Error as error:
            if _is_fts_unavailable(error):
                raise FtsUnavailableError("当前 SQLite 不支持 FTS5 trigram 检索") from None
            raise KnowledgeBaseError("全文检索查询无效") from None

        items = tuple(self._retrieved_chunk(row) for row in rows)
        has_more = offset + len(items) < total
        return RetrievedPage(
            total=total,
            items=items,
            has_more=has_more,
            next_offset=offset + len(items) if has_more else None,
        )

    def search_source_chunks(
        self,
        collection: str,
        fts_query: str | None,
        like_terms: Sequence[str],
        source_path: PurePosixPath,
    ) -> tuple[RetrievedChunk, ...]:
        """在单一 SQLite 读快照中分页读取目标来源的全部匹配分块。"""
        _validate_collection(collection)
        root_id, relative_path = _split_source_path(source_path)
        if fts_query is not None and not isinstance(fts_query, str):
            raise ValueError("fts_query 必须为字符串或 None")
        if any(not isinstance(term, str) for term in like_terms):
            raise ValueError("like_terms 必须只包含字符串")
        page_size = 40
        offset = 0
        expected_total: int | None = None
        items: list[RetrievedChunk] = []
        seen_chunk_ids: set[int] = set()
        try:
            with closing(self.connect()) as connection:
                connection.execute("BEGIN")
                self._require_collection(connection, collection)
                source_row = connection.execute(
                    """
                    SELECT 1 FROM sources
                    JOIN collections ON collections.id=sources.collection_id
                    WHERE collections.name=? AND sources.root_id=? AND sources.relative_path=?
                    """,
                    (collection, root_id, relative_path),
                ).fetchone()
                if source_row is None:
                    raise SourceNotFoundError("Indexed source was not found in the collection")
                while True:
                    if fts_query:
                        rows, total = self._search_with_fts(
                            connection,
                            collection,
                            fts_query,
                            like_terms,
                            (source_path.as_posix(),),
                            page_size,
                            offset,
                        )
                    else:
                        rows, total = self._search_without_fts(
                            connection,
                            collection,
                            like_terms,
                            (source_path.as_posix(),),
                            page_size,
                            offset,
                        )
                    page = tuple(self._retrieved_chunk(row) for row in rows)
                    if expected_total is None:
                        expected_total = total
                    page_ids = tuple(item.chunk_id for item in page)
                    if (
                        total != expected_total
                        or len(items) + len(page) > expected_total
                        or any(item.source_path != source_path for item in page)
                        or len(set(page_ids)) != len(page_ids)
                        or any(chunk_id in seen_chunk_ids for chunk_id in page_ids)
                    ):
                        raise KnowledgeBaseError(
                            "Focused summary pagination became inconsistent; retry"
                        )
                    seen_chunk_ids.update(page_ids)
                    items.extend(page)
                    if len(items) == expected_total:
                        return tuple(items)
                    if not page:
                        raise KnowledgeBaseError(
                            "Focused summary pagination became inconsistent; retry"
                        )
                    offset += len(page)
        except sqlite3.Error as error:
            if _is_fts_unavailable(error):
                raise FtsUnavailableError("当前 SQLite 不支持 FTS5 trigram 检索") from None
            raise KnowledgeBaseError("全文检索查询无效") from None

    def ensure_collection_exists(self, collection: str) -> None:
        """用单次轻量查询确认集合存在, 不读取来源或分块。"""
        _validate_collection(collection)
        try:
            with closing(self.connect()) as connection:
                self._require_collection(connection, collection)
        except sqlite3.Error as error:
            _raise_database_error(error)

    def list_sources(
        self,
        collection: str,
        query: str | None,
        limit: int,
        offset: int,
    ) -> ListSourcesResult:
        """按公开路径列出来源元数据。"""
        _validate_collection(collection)
        self._validate_pagination(limit, offset)
        if query is not None and not isinstance(query, str):
            raise ValueError("query 必须为字符串或 None")
        predicates = ["collections.name=?"]
        parameters: list[Any] = [collection]
        if query:
            predicates.append(
                "(sources.root_id || '/' || sources.relative_path) LIKE ? ESCAPE '\\'"
            )
            parameters.append(f"%{_escape_like(query)}%")
        where_sql = " AND ".join(predicates)
        try:
            with closing(self.connect()) as connection:
                self._require_collection(connection, collection)
                total_row = connection.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM sources
                    JOIN collections ON collections.id=sources.collection_id
                    WHERE {where_sql}
                    """,
                    parameters,
                ).fetchone()
                assert total_row is not None
                rows = connection.execute(
                    f"""
                    SELECT
                        sources.root_id || '/' || sources.relative_path AS source_path,
                        sources.format, sources.size_bytes, sources.page_count,
                        COUNT(chunks.id) AS chunk_count,
                        substr(sources.content_sha256, 1, 12) AS content_sha256_prefix,
                        sources.indexed_at
                    FROM sources
                    JOIN collections ON collections.id=sources.collection_id
                    LEFT JOIN chunks ON chunks.source_id=sources.id
                    WHERE {where_sql}
                    GROUP BY sources.id
                    ORDER BY source_path ASC
                    LIMIT ? OFFSET ?
                    """,
                    (*parameters, limit, offset),
                ).fetchall()
        except sqlite3.Error as error:
            _raise_database_error(error)
        total = total_row["total"]
        sources = tuple(
            SourceInfo(
                source_path=PurePosixPath(row["source_path"]),
                source_format=SourceFormat(row["format"]),
                size_bytes=row["size_bytes"],
                page_count=row["page_count"],
                chunk_count=row["chunk_count"],
                content_sha256_prefix=row["content_sha256_prefix"],
                indexed_at=row["indexed_at"],
            )
            for row in rows
        )
        has_more = offset + len(sources) < total
        return ListSourcesResult(
            total=total,
            count=len(sources),
            offset=offset,
            has_more=has_more,
            next_offset=offset + len(sources) if has_more else None,
            sources=sources,
        )

    def get_source_chunks(
        self,
        collection: str,
        source_path: PurePosixPath,
    ) -> tuple[RetrievedChunk, ...]:
        """按 ordinal 返回单一来源的全部分块。"""
        _validate_collection(collection)
        root_id, relative_path = _split_source_path(source_path)
        try:
            with closing(self.connect()) as connection:
                self._require_collection(connection, collection)
                source_row = connection.execute(
                    """
                    SELECT sources.id
                    FROM sources
                    JOIN collections ON collections.id=sources.collection_id
                    WHERE collections.name=? AND sources.root_id=? AND sources.relative_path=?
                    """,
                    (collection, root_id, relative_path),
                ).fetchone()
                if source_row is None:
                    raise SourceNotFoundError("指定的知识来源不存在")
                rows = connection.execute(
                    """
                    SELECT id AS chunk_id, ? AS source_path, text,
                           page_number, line_start, line_end, 0.0 AS rank
                    FROM chunks
                    WHERE source_id=?
                    ORDER BY ordinal ASC, id ASC
                    """,
                    (source_path.as_posix(), source_row["id"]),
                ).fetchall()
        except sqlite3.Error as error:
            _raise_database_error(error)
        return tuple(self._retrieved_chunk(row) for row in rows)

    def source_exists(self, collection: str, source_path: PurePosixPath) -> bool:
        """确认公开来源路径已在指定集合中建立索引。"""
        _validate_collection(collection)
        root_id, relative_path = _split_source_path(source_path)
        try:
            with closing(self.connect()) as connection:
                self._require_collection(connection, collection)
                row = connection.execute(
                    """
                    SELECT 1
                    FROM sources
                    JOIN collections ON collections.id=sources.collection_id
                    WHERE collections.name=? AND sources.root_id=? AND sources.relative_path=?
                    """,
                    (collection, root_id, relative_path),
                ).fetchone()
        except sqlite3.Error as error:
            _raise_database_error(error)
        return row is not None

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> None:
        """拒绝无界或负分页值。"""
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit 必须为正整数")
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError("offset 必须为非负整数")

    @staticmethod
    def _require_collection(connection: sqlite3.Connection, collection: str) -> None:
        """区分不存在集合与真实空集合。"""
        row = connection.execute(
            "SELECT 1 FROM collections WHERE name=?",
            (collection,),
        ).fetchone()
        if row is None:
            raise IndexNotFoundError(_INDEX_NOT_FOUND_MESSAGE)

    @staticmethod
    def _path_predicate(
        source_paths: Sequence[str],
        parameters: list[Any],
    ) -> str | None:
        """构建只含固定占位符的来源路径过滤器。"""
        if not source_paths:
            return None
        parameters.extend(source_paths)
        placeholders = ", ".join("?" for _ in source_paths)
        return f"(sources.root_id || '/' || sources.relative_path) IN ({placeholders})"

    @classmethod
    def _search_scope(
        cls,
        collection: str,
        source_paths: Sequence[str],
    ) -> tuple[list[str], list[Any]]:
        """构建集合与公开路径组成的固定参数化检索范围。"""
        predicates = ["collections.name=?"]
        parameters: list[Any] = [collection]
        path_predicate = cls._path_predicate(source_paths, parameters)
        if path_predicate:
            predicates.append(path_predicate)
        return predicates, parameters

    def _search_without_fts(
        self,
        connection: sqlite3.Connection,
        collection: str,
        like_terms: Sequence[str],
        source_paths: Sequence[str],
        limit: int,
        offset: int,
    ) -> tuple[list[sqlite3.Row], int]:
        """执行纯 LIKE 或受限全表浏览。"""
        predicates, parameters = self._search_scope(collection, source_paths)
        if like_terms:
            like_predicates = []
            for term in like_terms:
                like_predicates.append("chunks.text LIKE ? ESCAPE '\\'")
                parameters.append(f"%{_escape_like(term)}%")
            predicates.append(f"({' OR '.join(like_predicates)})")
        where_sql = " AND ".join(predicates)
        total_row = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM chunks
            JOIN sources ON sources.id=chunks.source_id
            JOIN collections ON collections.id=sources.collection_id
            WHERE {where_sql}
            """,
            parameters,
        ).fetchone()
        assert total_row is not None
        rows = connection.execute(
            f"""
            SELECT chunks.id AS chunk_id,
                   sources.root_id || '/' || sources.relative_path AS source_path,
                   chunks.text, chunks.page_number, chunks.line_start, chunks.line_end,
                   0.0 AS rank
            FROM chunks
            JOIN sources ON sources.id=chunks.source_id
            JOIN collections ON collections.id=sources.collection_id
            WHERE {where_sql}
            ORDER BY chunks.id ASC
            LIMIT ? OFFSET ?
            """,
            (*parameters, limit, offset),
        ).fetchall()
        return rows, total_row["total"]

    def _populate_search_candidates(
        self,
        connection: sqlite3.Connection,
        collection: str,
        fts_query: str,
        like_terms: Sequence[str],
        source_paths: Sequence[str],
    ) -> int:
        """仅在目标集合与来源范围内填充 FTS/LIKE 临时候选。"""
        connection.execute(
            """
            CREATE TEMP TABLE IF NOT EXISTS search_candidates (
                chunk_id INTEGER PRIMARY KEY,
                bm25_value REAL,
                fts_matched INTEGER NOT NULL
            )
            """
        )
        connection.execute("DELETE FROM search_candidates")

        fts_predicates, fts_parameters = self._search_scope(collection, source_paths)
        fts_predicates.append("chunks_fts MATCH ?")
        fts_parameters.append(fts_query)
        fts_cursor = connection.execute(
            f"""
            INSERT INTO search_candidates(chunk_id, bm25_value, fts_matched)
            SELECT chunks_fts.rowid, bm25(chunks_fts), 1
            FROM chunks_fts
            JOIN chunks ON chunks.id=chunks_fts.rowid
            JOIN sources ON sources.id=chunks.source_id
            JOIN collections ON collections.id=sources.collection_id
            WHERE {" AND ".join(fts_predicates)}
            """,
            fts_parameters,
        )
        inserted = fts_cursor.rowcount

        if like_terms:
            like_predicates = []
            scope_predicates, like_parameters = self._search_scope(collection, source_paths)
            for term in like_terms:
                like_predicates.append("chunks.text LIKE ? ESCAPE '\\'")
                like_parameters.append(f"%{_escape_like(term)}%")
            scope_predicates.append(f"({' OR '.join(like_predicates)})")
            like_cursor = connection.execute(
                f"""
                INSERT OR IGNORE INTO search_candidates(chunk_id, bm25_value, fts_matched)
                SELECT chunks.id, NULL, 0
                FROM chunks
                JOIN sources ON sources.id=chunks.source_id
                JOIN collections ON collections.id=sources.collection_id
                WHERE {" AND ".join(scope_predicates)}
                """,
                like_parameters,
            )
            inserted += like_cursor.rowcount
        return inserted

    def _search_with_fts(
        self,
        connection: sqlite3.Connection,
        collection: str,
        fts_query: str,
        like_terms: Sequence[str],
        source_paths: Sequence[str],
        limit: int,
        offset: int,
    ) -> tuple[list[sqlite3.Row], int]:
        """以 FTS 命中为主并合并短词 LIKE 回退命中。"""
        # FTS5 辅助函数必须在直接扫描虚拟表的语句中求值, 不能延后到聚合 CTE。
        self._populate_search_candidates(
            connection,
            collection,
            fts_query,
            like_terms,
            source_paths,
        )
        predicates, filter_parameters = self._search_scope(collection, source_paths)
        where_sql = " AND ".join(predicates)
        total_row = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM search_candidates
            JOIN chunks ON chunks.id=search_candidates.chunk_id
            JOIN sources ON sources.id=chunks.source_id
            JOIN collections ON collections.id=sources.collection_id
            WHERE {where_sql}
            """,
            filter_parameters,
        ).fetchone()
        assert total_row is not None
        rows = connection.execute(
            f"""
            SELECT chunks.id AS chunk_id,
                   sources.root_id || '/' || sources.relative_path AS source_path,
                   chunks.text, chunks.page_number, chunks.line_start, chunks.line_end,
                   CASE WHEN search_candidates.fts_matched=1
                        THEN -search_candidates.bm25_value ELSE 0.0 END AS rank
            FROM search_candidates
            JOIN chunks ON chunks.id=search_candidates.chunk_id
            JOIN sources ON sources.id=chunks.source_id
            JOIN collections ON collections.id=sources.collection_id
            WHERE {where_sql}
            ORDER BY search_candidates.fts_matched DESC,
                     search_candidates.bm25_value ASC,
                     chunks.id ASC
            LIMIT ? OFFSET ?
            """,
            (*filter_parameters, limit, offset),
        ).fetchall()
        return rows, total_row["total"]

    @staticmethod
    def _retrieved_chunk(row: sqlite3.Row) -> RetrievedChunk:
        """将数据库行转换为严格公共模型。"""
        return RetrievedChunk(
            chunk_id=row["chunk_id"],
            source_path=PurePosixPath(row["source_path"]),
            text=row["text"],
            page_number=row["page_number"],
            line_start=row["line_start"],
            line_end=row["line_end"],
            rank=float(row["rank"]),
        )
