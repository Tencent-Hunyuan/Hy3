"""SQLite/FTS5 存储层契约测试。"""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from threading import Event

import pytest

from hy3_knowledge_mcp.errors import (
    FtsUnavailableError,
    IndexNotFoundError,
    KnowledgeBaseError,
    SourceNotFoundError,
)
from hy3_knowledge_mcp.models import (
    ChunkDraft,
    PreparedSource,
    ResolvedSource,
    SourceFormat,
    StoredFingerprint,
)
from hy3_knowledge_mcp.store import SourceRefreshState, SQLiteStore

_DEFAULT_RELATIVE_PATH = PurePosixPath("guide.md")


def chunks(*texts: str) -> tuple[ChunkDraft, ...]:
    """生成顺序稳定的测试分块。"""
    return tuple(
        ChunkDraft(
            ordinal=index,
            text=text,
            line_start=index + 1,
            line_end=index + 1,
            char_count=len(text),
        )
        for index, text in enumerate(texts)
    )


def replace(
    store: SQLiteStore,
    digest: str,
    values: tuple[ChunkDraft, ...],
    *,
    relative_path: PurePosixPath = _DEFAULT_RELATIVE_PATH,
    root_id: str = "0123456789ab",
    mtime_ns: int = 1,
    size_bytes: int = 10,
    page_count: int | None = None,
) -> None:
    """写入一个测试来源。"""
    store.replace_source(
        collection="docs",
        root_id=root_id,
        relative_path=relative_path,
        content_sha256=digest,
        mtime_ns=mtime_ns,
        size_bytes=size_bytes,
        source_format=SourceFormat.MARKDOWN,
        page_count=page_count,
        chunks=values,
    )


def replace_in_collection(
    store: SQLiteStore,
    collection: str,
    relative_path: PurePosixPath,
    digest: str,
    values: tuple[ChunkDraft, ...],
) -> PurePosixPath:
    """向指定集合写入来源并返回公开路径。"""
    store.replace_source(
        collection=collection,
        root_id="0123456789ab",
        relative_path=relative_path,
        content_sha256=digest,
        mtime_ns=1,
        size_bytes=sum(item.char_count for item in values),
        source_format=SourceFormat.MARKDOWN,
        page_count=None,
        chunks=values,
    )
    return PurePosixPath("0123456789ab") / relative_path


def create_empty_collection(store: SQLiteStore) -> None:
    """创建一个真实存在但尚无来源的集合。"""
    with store.connect() as connection, connection:
        connection.execute(
            "INSERT INTO collections(name, created_at, updated_at) VALUES (?, ?, ?)",
            ("docs", "2026-07-11T00:00:00+00:00", "2026-07-11T00:00:00+00:00"),
        )


def prepared_source(
    tmp_path: Path,
    relative_path: str,
    digest: str,
    values: tuple[ChunkDraft, ...],
) -> PreparedSource:
    """构造用于集合级事务测试的已准备来源。"""
    source_path = PurePosixPath(relative_path)
    return PreparedSource(
        source=ResolvedSource(
            absolute_path=tmp_path / relative_path,
            root_path=tmp_path,
            root_id="0123456789ab",
            relative_path=source_path,
            source_path=PurePosixPath("0123456789ab") / source_path,
            size_bytes=10,
            mtime_ns=1,
            device_id=1,
            file_id=1,
        ),
        content_sha256=digest,
        source_format=SourceFormat.TEXT,
        chunks=values,
    )


def test_initialize_maps_missing_trigram_support_without_leaking_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SQLiteStore(tmp_path / "private-index.sqlite3")

    def unavailable() -> sqlite3.Connection:
        raise sqlite3.OperationalError("no such tokenizer: trigram at private-index.sqlite3")

    monkeypatch.setattr(store, "connect", unavailable)

    with pytest.raises(FtsUnavailableError) as error:
        store.initialize()

    assert "private-index.sqlite3" not in str(error.value)


def test_replace_source_removes_stale_fts_terms(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(store, "a" * 64, chunks("old keyword", "stable text"))
    assert store.search("docs", '"old keyword"', (), (), 10, 0).total == 1

    replace(store, "b" * 64, chunks("new keyword"))

    assert store.search("docs", '"old keyword"', (), (), 10, 0).total == 0
    assert store.search("docs", '"new keyword"', (), (), 10, 0).total == 1


def test_fts_candidates_are_scoped_before_temp_table_insertion(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    target_path = replace_in_collection(
        store,
        "small",
        PurePosixPath("target' OR 1=1 --.md"),
        "1" * 64,
        chunks("sharedtoken target", "退款 target"),
    )
    replace_in_collection(
        store,
        "small",
        PurePosixPath("excluded.md"),
        "2" * 64,
        chunks("sharedtoken excluded", "退款 excluded"),
    )
    replace_in_collection(
        store,
        "large",
        PurePosixPath("many.md"),
        "3" * 64,
        chunks(
            *(f"sharedtoken distractor {index}" for index in range(40)),
            *(f"退款 distractor {index}" for index in range(40)),
        ),
    )

    with store.connect() as connection:
        inserted = store._populate_search_candidates(
            connection,
            "small",
            '"sharedtoken"',
            ("退款",),
            (target_path.as_posix(),),
        )
        candidate_count = connection.execute("SELECT COUNT(*) FROM search_candidates").fetchone()[0]

    first = store.search("small", '"sharedtoken"', ("退款",), (target_path,), 1, 0)
    second = store.search("small", '"sharedtoken"', ("退款",), (target_path,), 1, 1)

    assert inserted == 2
    assert candidate_count == 2
    assert first.total == second.total == 2
    assert first.items[0].source_path == second.items[0].source_path == target_path
    assert first.items[0].rank > second.items[0].rank == 0
    assert first.has_more is True
    assert first.next_offset == 1
    assert second.has_more is False


def test_like_terms_escape_percent_underscore_and_backslash(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(store, "d" * 64, chunks(r"100%_safe\path", "100xxsafeXpath", "unrelated"))

    page = store.search("docs", None, (r"100%_safe\path",), (), 10, 0)

    assert [item.text for item in page.items] == [r"100%_safe\path"]
    assert page.items[0].rank == 0.0


def test_failed_chunk_insert_rolls_back_source_chunks_and_fts(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(store, "1" * 64, chunks("previous content"))
    duplicate_ordinals = (
        ChunkDraft(ordinal=0, text="replacement one", char_count=15),
        ChunkDraft(ordinal=0, text="replacement two", char_count=15),
    )

    with pytest.raises(ValueError) as error:
        replace(store, "2" * 64, duplicate_ordinals)

    assert "UNIQUE" not in str(error.value)
    assert "index.sqlite3" not in str(error.value)
    assert store.search("docs", '"previous content"', (), (), 10, 0).total == 1
    assert store.search("docs", '"replacement one"', (), (), 10, 0).total == 0
    assert store.get_source_fingerprint("docs", PurePosixPath("0123456789ab/guide.md")) == (
        StoredFingerprint(content_sha256="1" * 64, mtime_ns=1, size_bytes=10)
    )


def test_fts_update_and_delete_triggers_synchronize_external_content(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(store, "3" * 64, chunks("before trigger"))

    with store.connect() as connection, connection:
        chunk_id = connection.execute("SELECT id FROM chunks").fetchone()[0]
        connection.execute(
            "UPDATE chunks SET text=?, char_count=? WHERE id=?",
            ("after trigger", len("after trigger"), chunk_id),
        )

    assert store.search("docs", '"before trigger"', (), (), 10, 0).total == 0
    assert store.search("docs", '"after trigger"', (), (), 10, 0).total == 1

    with store.connect() as connection, connection:
        connection.execute("DELETE FROM chunks WHERE id=?", (chunk_id,))

    assert store.search("docs", '"after trigger"', (), (), 10, 0).total == 0


def test_existing_empty_collection_differs_from_missing_collection(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    create_empty_collection(store)

    assert store.search("docs", None, (), (), 10, 0).total == 0
    assert store.list_sources("docs", None, 10, 0).total == 0
    with pytest.raises(SourceNotFoundError):
        store.get_source_chunks("docs", PurePosixPath("0123456789ab/missing.md"))

    instruction = "hy3_kb_index_documents"
    with pytest.raises(IndexNotFoundError, match=instruction):
        store.search("missing", None, (), (), 10, 0)
    with pytest.raises(IndexNotFoundError, match=instruction):
        store.list_sources("missing", None, 10, 0)
    with pytest.raises(IndexNotFoundError, match=instruction):
        store.get_source_chunks("missing", PurePosixPath("0123456789ab/missing.md"))


def test_pagination_count_and_next_offset_use_identical_predicates(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(store, "6" * 64, chunks("filter one", "filter two", "not selected"))

    page = store.search("docs", None, ("filter",), (), 1, 1)
    end = store.search("docs", None, ("filter",), (), 1, 2)

    assert page.total == 2
    assert len(page.items) == 1
    assert page.has_more is False
    assert page.next_offset is None
    assert end.total == 2
    assert end.items == ()


def test_empty_query_is_bounded_and_does_not_ignore_limit(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(store, "7" * 64, chunks("one", "two", "three"))

    page = store.search("docs", None, (), (), 2, 0)

    assert page.total == 3
    assert len(page.items) == 2
    assert page.has_more is True
    assert page.next_offset == 2


def test_sql_injection_values_are_bound_parameters(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(
        store,
        "9" * 64,
        chunks("literal ' OR 1=1 -- marker", "safe row"),
        relative_path=PurePosixPath("odd' OR 1=1 --.md"),
    )

    like_page = store.search("docs", None, ("' OR 1=1 --",), (), 10, 0)
    path_page = store.search(
        "docs",
        None,
        (),
        (PurePosixPath("0123456789ab/odd' OR 1=1 --.md"),),
        10,
        0,
    )

    assert [item.text for item in like_page.items] == ["literal ' OR 1=1 -- marker"]
    assert path_page.total == 2
    with store.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 1


def test_source_search_pages_share_one_read_snapshot_during_replacement(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    old_chunks = tuple(f"Hy3 old {index}" for index in range(45))
    new_chunks = tuple(f"Hy3 new {index}" for index in range(45))
    replace(store, "a" * 64, chunks(*old_chunks))
    assert hasattr(store, "search_source_chunks")

    first_page_read = Event()
    continue_reader = Event()
    original_search = store._search_with_fts
    calls = 0

    def pausing_search(*args, **kwargs):
        nonlocal calls
        result = original_search(*args, **kwargs)
        calls += 1
        if calls == 1:
            first_page_read.set()
            assert continue_reader.wait(timeout=5)
        return result

    store._search_with_fts = pausing_search  # type: ignore[method-assign]
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            store.search_source_chunks,
            "docs",
            '"Hy3"',
            (),
            PurePosixPath("0123456789ab/guide.md"),
        )
        assert first_page_read.wait(timeout=5)
        replace(store, "b" * 64, chunks(*new_chunks))
        continue_reader.set()
        result = future.result(timeout=5)

    texts = tuple(item.text for item in result)
    assert len(texts) == 45
    assert texts in (old_chunks, new_chunks)
    assert len({item.chunk_id for item in result}) == 45
    assert calls == 2


def test_classify_and_refresh_source_returns_three_typed_transaction_states(
    tmp_path: Path,
) -> None:
    """缺失、变化和未变化来源由显式枚举区分。仅未变化时更新元数据。"""
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    source_path = PurePosixPath("0123456789ab/guide.md")

    missing = store.classify_and_refresh_source(
        "docs",
        source_path,
        "a" * 64,
        mtime_ns=2,
        size_bytes=20,
    )
    replace(store, "a" * 64, chunks("stored"), mtime_ns=1, size_bytes=10)
    missing_in_collection = store.classify_and_refresh_source(
        "docs",
        PurePosixPath("0123456789ab/missing.md"),
        "a" * 64,
        mtime_ns=2,
        size_bytes=20,
    )
    changed = store.classify_and_refresh_source(
        "docs",
        source_path,
        "b" * 64,
        mtime_ns=3,
        size_bytes=30,
    )
    after_changed = store.get_source_fingerprint("docs", source_path)
    unchanged = store.classify_and_refresh_source(
        "docs",
        source_path,
        "a" * 64,
        mtime_ns=4,
        size_bytes=40,
    )

    assert missing is SourceRefreshState.MISSING
    assert missing_in_collection is SourceRefreshState.MISSING
    assert changed is SourceRefreshState.CHANGED
    assert unchanged is SourceRefreshState.UNCHANGED
    assert after_changed == StoredFingerprint(
        content_sha256="a" * 64,
        mtime_ns=1,
        size_bytes=10,
    )
    assert store.get_source_fingerprint("docs", source_path) == StoredFingerprint(
        content_sha256="a" * 64,
        mtime_ns=4,
        size_bytes=40,
    )


def test_list_sources_filters_and_paginates_public_metadata(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(
        store,
        "b" * 64,
        chunks("first"),
        relative_path=PurePosixPath("alpha.md"),
        size_bytes=12,
        page_count=2,
    )
    replace(
        store,
        "c" * 64,
        chunks("second", "third"),
        relative_path=PurePosixPath("nested/beta.md"),
        size_bytes=34,
    )

    page = store.list_sources("docs", "beta", 1, 0)

    assert page.total == 1
    assert page.count == 1
    assert page.offset == 0
    assert page.has_more is False
    assert page.next_offset is None
    assert page.sources[0].source_path == PurePosixPath("0123456789ab/nested/beta.md")
    assert page.sources[0].chunk_count == 2
    assert page.sources[0].content_sha256_prefix == "c" * 12


def test_sqlite_errors_are_not_exposed_after_database_corruption(tmp_path: Path) -> None:
    database = tmp_path / "private-index.sqlite3"
    store = SQLiteStore(database)
    database.write_bytes(b"not sqlite")

    with pytest.raises(KnowledgeBaseError) as error:
        store.initialize()

    assert not isinstance(error.value, sqlite3.Error)
    assert "private-index.sqlite3" not in str(error.value)


def test_replace_collection_rolls_back_all_sources_and_fts_on_late_failure(
    tmp_path: Path,
) -> None:
    """集合重建后段失败时回滚先前删除和插入的全部内容。"""
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(store, "a" * 64, chunks("old collection"))
    first = prepared_source(tmp_path, "first.txt", "b" * 64, chunks("first candidate"))
    invalid_chunks = (
        ChunkDraft(ordinal=0, text="bad one", char_count=7),
        ChunkDraft(ordinal=0, text="bad two", char_count=7),
    )
    second = prepared_source(tmp_path, "second.txt", "c" * 64, invalid_chunks)

    with pytest.raises(ValueError, match="约束"):
        store.replace_collection("docs", (first, second))

    assert store.list_sources("docs", None, 10, 0).total == 1
    assert store.search("docs", '"old collection"', (), (), 10, 0).total == 1
    assert store.search("docs", '"first candidate"', (), (), 10, 0).total == 0
    assert store.search("docs", '"bad one"', (), (), 10, 0).total == 0


def test_replace_collection_empty_requires_explicit_permission_and_clears_fts(
    tmp_path: Path,
) -> None:
    """仅显式允许的空集合替换可删除最终来源及其 FTS 行。"""
    store = SQLiteStore(tmp_path / "index.sqlite3")
    store.initialize()
    replace(store, "d" * 64, chunks("final stale term"))

    with pytest.raises(ValueError, match="不得意外为空"):
        store.replace_collection("docs", ())
    assert store.search("docs", '"final stale term"', (), (), 10, 0).total == 1

    store.replace_collection("docs", (), allow_empty=True)

    assert store.list_sources("docs", None, 10, 0).total == 0
    assert store.search("docs", '"final stale term"', (), (), 10, 0).total == 0
