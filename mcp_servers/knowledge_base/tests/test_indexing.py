"""增量索引编排契约测试。"""

import asyncio
import hashlib
import threading
import time
from pathlib import Path, PurePosixPath

import pytest

from hy3_knowledge_mcp import indexing
from hy3_knowledge_mcp.config import Settings
from hy3_knowledge_mcp.errors import (
    KnowledgeBaseError,
    LimitExceededError,
    PathNotAllowedError,
    UnsupportedFileError,
)
from hy3_knowledge_mcp.indexing import IndexingService, prepare_source
from hy3_knowledge_mcp.models import (
    IndexDocumentsRequest,
    StoredFingerprint,
)
from hy3_knowledge_mcp.paths import build_allowed_roots
from hy3_knowledge_mcp.store import SQLiteStore


def make_indexer(tmp_path: Path, root: Path) -> tuple[IndexingService, SQLiteStore]:
    """创建使用真实 SQLite 与受限路径层的索引器。"""
    storage = tmp_path / "storage"
    storage.mkdir(exist_ok=True)
    settings = Settings.from_env(
        {
            "HY3_KB_ROOTS": str(root),
            "HY3_KB_STORAGE_DIR": str(storage),
        }
    )
    store = SQLiteStore(storage / "index.sqlite3")
    store.initialize()
    return IndexingService(settings, build_allowed_roots((root,)), store), store


@pytest.mark.anyio
async def test_incremental_index_updates_metadata_without_rewriting_equal_digest(
    tmp_path: Path,
) -> None:
    """内容摘要相同仅更新元数据。内容变化原子替换旧分块。"""
    root = tmp_path / "root"
    root.mkdir()
    guide = root / "guide.md"
    guide.write_text("# Guide\n\nold term", encoding="utf-8")
    indexer, store = make_indexer(tmp_path, root)
    request = IndexDocumentsRequest(collection="docs", path=str(root))

    first = await indexer.index(request)
    guide.write_text("# Guide\n\nold term", encoding="utf-8")
    second = await indexer.index(request)
    source_path = store.list_sources("docs", None, 10, 0).sources[0].source_path
    after = store.get_source_fingerprint("docs", source_path)

    assert first.indexed_sources == 1
    assert first.chunk_count > 0
    assert second.unchanged_sources == 1
    assert second.chunk_count == 0
    assert isinstance(after, StoredFingerprint)
    assert after.size_bytes == guide.stat().st_size

    guide.write_text("# Guide\n\nnew term", encoding="utf-8")
    updated = await indexer.index(request)
    assert updated.updated_sources == 1
    assert store.search("docs", '"old term"', (), (), 10, 0).total == 0
    assert store.search("docs", '"new term"', (), (), 10, 0).total == 1
    assert source_path == PurePosixPath(source_path)


@pytest.mark.anyio
async def test_incremental_failure_preserves_old_source_and_commits_other_sources(
    tmp_path: Path,
) -> None:
    """每个来源独立提交。失败来源保留旧版本且不阻塞其他来源。"""
    root = tmp_path / "root"
    root.mkdir()
    good = root / "good.txt"
    bad = root / "bad.txt"
    good.write_text("good old", encoding="utf-8")
    bad.write_text("bad old", encoding="utf-8")
    indexer, store = make_indexer(tmp_path, root)
    request = IndexDocumentsRequest(collection="docs", path=str(root))
    await indexer.index(request)

    good.write_text("good new", encoding="utf-8")
    bad.write_bytes(b"\xff")
    result = await indexer.index(request)

    assert result.updated_sources == 1
    assert result.failed_sources == 1
    assert result.chunk_count == 1
    assert store.search("docs", '"good new"', (), (), 10, 0).total == 1
    assert store.search("docs", '"bad old"', (), (), 10, 0).total == 1
    assert tuple(error.source_path.name for error in result.errors) == ("bad.txt",)
    assert str(root) not in result.errors[0].reason


@pytest.mark.anyio
async def test_replace_is_all_or_nothing_and_empty_replace_clears_final_source(
    tmp_path: Path,
) -> None:
    """replace 仅在全部准备成功后重建。空发现会留下真实空集合。"""
    root = tmp_path / "root"
    root.mkdir()
    first = root / "first.txt"
    second = root / "second.txt"
    first.write_text("first old", encoding="utf-8")
    second.write_text("second old", encoding="utf-8")
    indexer, store = make_indexer(tmp_path, root)
    request = IndexDocumentsRequest(collection="docs", path=str(root))
    await indexer.index(request)

    first.write_text("first candidate", encoding="utf-8")
    second.write_bytes(b"\xff")
    failed = await indexer.index(
        IndexDocumentsRequest(collection="docs", path=str(root), replace=True)
    )

    assert failed.failed_sources == 1
    assert failed.indexed_sources == 0
    assert failed.chunk_count == 0
    assert store.search("docs", '"first old"', (), (), 10, 0).total == 1
    assert store.search("docs", '"first candidate"', (), (), 10, 0).total == 0
    assert store.search("docs", '"second old"', (), (), 10, 0).total == 1

    first.unlink()
    second.unlink()
    emptied = await indexer.index(
        IndexDocumentsRequest(collection="docs", path=str(root), replace=True)
    )
    assert emptied.discovered_sources == 0
    assert emptied.indexed_sources == 0
    assert store.list_sources("docs", None, 10, 0).total == 0
    assert store.search("docs", None, (), (), 10, 0).total == 0


@pytest.mark.anyio
async def test_index_lock_serializes_concurrent_requests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同一服务实例不会并发执行两个发现、读取或写入流程。"""
    root = tmp_path / "root"
    root.mkdir()
    (root / "guide.txt").write_text("serialized", encoding="utf-8")
    indexer, _ = make_indexer(tmp_path, root)
    original_read = indexing.read_validated_bytes
    active = 0
    maximum = 0
    guard = threading.Lock()

    def slow_read(*args: object, **kwargs: object) -> bytes:
        nonlocal active, maximum
        with guard:
            active += 1
            maximum = max(maximum, active)
        try:
            time.sleep(0.05)
            return original_read(*args, **kwargs)  # type: ignore[arg-type]
        finally:
            with guard:
                active -= 1

    monkeypatch.setattr(indexing, "read_validated_bytes", slow_read)
    first, second = await asyncio.gather(
        indexer.index(IndexDocumentsRequest(collection="first", path=str(root))),
        indexer.index(IndexDocumentsRequest(collection="second", path=str(root))),
    )

    assert first.indexed_sources == 1
    assert second.indexed_sources == 1
    assert maximum == 1


@pytest.mark.anyio
async def test_cancellation_waits_for_started_store_write_before_releasing_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """取消不会遗留仍在锁外运行的写线程。也不会产生半提交。"""
    root = tmp_path / "root"
    root.mkdir()
    (root / "guide.txt").write_text("cancel boundary", encoding="utf-8")
    indexer, store = make_indexer(tmp_path, root)
    original_replace = store.replace_prepared_source
    entered = threading.Event()
    release = threading.Event()

    def blocked_replace(*args: object, **kwargs: object) -> None:
        entered.set()
        assert release.wait(timeout=5)
        original_replace(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(store, "replace_prepared_source", blocked_replace)
    task = asyncio.create_task(
        indexer.index(IndexDocumentsRequest(collection="docs", path=str(root)))
    )
    assert await asyncio.to_thread(entered.wait, 5)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert store.search("docs", '"cancel boundary"', (), (), 10, 0).total == 1
    follow_up = await indexer.index(IndexDocumentsRequest(collection="docs", path=str(root)))
    assert follow_up.unchanged_sources == 1


def test_prepare_source_hashes_and_parses_only_the_supplied_byte_snapshot(tmp_path: Path) -> None:
    """文件随后变化也不会让解析、分块或摘要读取第二份内容。"""
    root = tmp_path / "root"
    root.mkdir()
    path = root / "guide.txt"
    path.write_text("snapshot one", encoding="utf-8")
    indexer, _ = make_indexer(tmp_path, root)
    target = indexing.resolve_requested_path(path, indexer.roots)
    source = indexing.discover_source_files(
        target,
        recursive=False,
        include_globs=(),
        max_files=1,
        max_total_bytes=100,
    )[0]
    data = indexing.read_validated_bytes(source, max_bytes=100)
    path.write_text("snapshot two", encoding="utf-8")

    prepared = prepare_source(source, data, indexer.settings)

    assert prepared.content_sha256 == hashlib.sha256(data).hexdigest()
    assert "snapshot one" in prepared.chunks[0].text
    assert "snapshot two" not in prepared.chunks[0].text


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (PathNotAllowedError("C:/private/root/guide.txt"), "安全访问"),
        (UnsupportedFileError("C:/private/root/guide.txt"), "不受支持"),
        (LimitExceededError("C:/private/root/guide.txt"), "安全限制"),
        (ValueError("C:/private/root/guide.txt"), "解析或分块"),
        (OSError("C:/private/root/guide.txt"), "读取"),
    ],
)
async def test_per_file_errors_are_safe_and_do_not_expose_absolute_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
    expected: str,
) -> None:
    """路径、解析、分块与限制错误均映射为稳定且脱敏的每文件原因。"""
    root = tmp_path / "private-root"
    root.mkdir()
    (root / "guide.txt").write_text("content", encoding="utf-8")
    indexer, _ = make_indexer(tmp_path, root)

    def fail_read(*args: object, **kwargs: object) -> bytes:
        raise error

    monkeypatch.setattr(indexing, "read_validated_bytes", fail_read)
    result = await indexer.index(IndexDocumentsRequest(collection="docs", path=str(root)))

    assert result.failed_sources == 1
    assert expected in result.errors[0].reason
    assert str(root) not in result.errors[0].reason
    assert "private-root" not in result.errors[0].reason


@pytest.mark.anyio
async def test_infrastructure_store_error_propagates_without_reclassifying_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """数据库基础设施故障向上层传播。不伪装成可恢复内容错误。"""
    root = tmp_path / "root"
    root.mkdir()
    (root / "guide.txt").write_text("content", encoding="utf-8")
    indexer, store = make_indexer(tmp_path, root)

    def unavailable(*args: object, **kwargs: object) -> None:
        raise KnowledgeBaseError("本地知识库操作失败")

    monkeypatch.setattr(store, "classify_and_refresh_source", unavailable)
    with pytest.raises(KnowledgeBaseError, match="知识库操作失败"):
        await indexer.index(IndexDocumentsRequest(collection="docs", path=str(root)))
