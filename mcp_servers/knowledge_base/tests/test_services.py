import asyncio
from pathlib import Path, PurePosixPath

import pytest

from hy3_knowledge_mcp.config import Settings
from hy3_knowledge_mcp.errors import (
    CitationValidationError,
    Hy3ResponseError,
    KnowledgeBaseError,
    LimitExceededError,
    SourceNotFoundError,
)
from hy3_knowledge_mcp.hy3_client import (
    answer_schema_chars,
    summary_schema_chars,
)
from hy3_knowledge_mcp.models import (
    AskRequest,
    ChunkDraft,
    Hy3AnswerPayload,
    Hy3SummaryPayload,
    ListSourcesRequest,
    SearchRequest,
    SourceFormat,
    SummarizeSourceRequest,
)
from hy3_knowledge_mcp.paths import build_allowed_roots
from hy3_knowledge_mcp.prompts import build_answer_messages, build_summary_messages
from hy3_knowledge_mcp.retrieval import assign_evidence
from hy3_knowledge_mcp.services import KnowledgeBaseService, _message_chars
from hy3_knowledge_mcp.store import SQLiteStore


class FakeHy3:
    def __init__(
        self,
        *,
        answers: list[Hy3AnswerPayload] | None = None,
        summaries: list[Hy3SummaryPayload] | None = None,
    ) -> None:
        self.answers = answers or []
        self.summaries = summaries or []
        self.answer_messages: list[list[dict[str, str]]] = []
        self.summary_messages: list[list[dict[str, str]]] = []
        self.closed = 0

    async def answer(self, messages, *, reasoning_effort):
        self.answer_messages.append(messages)
        return self.answers[len(self.answer_messages) - 1]

    async def summarize(self, messages, *, reasoning_effort):
        self.summary_messages.append(messages)
        return self.summaries[len(self.summary_messages) - 1]

    async def close(self) -> None:
        self.closed += 1


def make_service(
    tmp_path: Path,
    fake: FakeHy3,
) -> tuple[KnowledgeBaseService, SQLiteStore, list[int]]:
    root = tmp_path / "root"
    root.mkdir()
    settings = Settings.from_env(
        {
            "HY3_KB_ROOTS": str(root),
            "HY3_KB_STORAGE_DIR": str(tmp_path / "storage"),
            "HY3_API_KEY": "fake",
        }
    )
    settings.storage_dir.mkdir(parents=True)
    store = SQLiteStore(settings.storage_dir / "index.sqlite3")
    store.initialize()
    factory_calls: list[int] = []

    def factory() -> FakeHy3:
        factory_calls.append(1)
        return fake

    service = KnowledgeBaseService(
        settings=settings,
        roots=build_allowed_roots((root,)),
        store=store,
        hy3_factory=factory,
    )
    return service, store, factory_calls


def insert_test_source(
    store: SQLiteStore,
    *,
    chunks: tuple[str, ...] = ("Hy3 is a reasoning model.",),
) -> None:
    store.replace_source(
        collection="docs",
        root_id="0123456789ab",
        relative_path=PurePosixPath("guide.md"),
        content_sha256="a" * 64,
        mtime_ns=1,
        size_bytes=sum(map(len, chunks)),
        source_format=SourceFormat.MARKDOWN,
        page_count=None,
        chunks=tuple(
            ChunkDraft(
                ordinal=index,
                text=text,
                line_start=index + 1,
                line_end=index + 1,
                char_count=len(text),
            )
            for index, text in enumerate(chunks)
        ),
    )


@pytest.mark.anyio
async def test_offline_operations_do_not_create_remote_client(tmp_path: Path) -> None:
    service, store, factory_calls = make_service(tmp_path, FakeHy3())
    insert_test_source(store)

    search = await service.search(SearchRequest(collection="docs", query="Hy3"))
    sources = await service.list_sources(ListSourcesRequest(collection="docs"))

    assert search.count == 1
    assert sources.count == 1
    assert factory_calls == []


@pytest.mark.anyio
async def test_ask_returns_insufficient_without_remote_call(tmp_path: Path) -> None:
    service, store, factory_calls = make_service(tmp_path, FakeHy3())
    insert_test_source(store)

    result = await service.ask(AskRequest(collection="docs", question="zzzunmatched"))

    assert result.insufficient_evidence is True
    assert result.citations == ()
    assert factory_calls == []


@pytest.mark.anyio
async def test_ask_repairs_invalid_citations_once_with_same_evidence(tmp_path: Path) -> None:
    fake = FakeHy3(
        answers=[
            Hy3AnswerPayload(
                answer="bad",
                used_evidence_ids=("S9",),
                insufficient_evidence=False,
            ),
            Hy3AnswerPayload(
                answer="fixed",
                used_evidence_ids=("S1",),
                insufficient_evidence=False,
            ),
        ]
    )
    service, store, factory_calls = make_service(tmp_path, fake)
    insert_test_source(store)

    result = await service.ask(AskRequest(collection="docs", question="What is Hy3?"))

    assert result.answer == "fixed"
    assert [item.evidence_id for item in result.citations] == ["S1"]
    assert len(fake.answer_messages) == 2
    assert fake.answer_messages[1][:2] == fake.answer_messages[0]
    assert factory_calls == [1]


@pytest.mark.anyio
async def test_full_summary_uses_ordered_chunks_and_validated_citations(tmp_path: Path) -> None:
    fake = FakeHy3(
        summaries=[Hy3SummaryPayload(summary="combined", used_evidence_ids=("S2", "S1"))]
    )
    service, store, _factory_calls = make_service(tmp_path, fake)
    insert_test_source(store, chunks=("first Hy3 fact", "second Hy3 fact"))

    result = await service.summarize(
        SummarizeSourceRequest(collection="docs", source_path="0123456789ab/guide.md")
    )

    assert result.summary == "combined"
    assert result.coverage == "full"
    assert result.used_evidence_ids == ("S2", "S1")
    assert [item.line_start for item in result.citations] == [2, 1]
    sent = fake.summary_messages[0][1]["content"]
    assert sent.index("first Hy3 fact") < sent.index("second Hy3 fact")


@pytest.mark.anyio
async def test_focused_summary_without_matches_does_not_call_remote(tmp_path: Path) -> None:
    service, store, factory_calls = make_service(tmp_path, FakeHy3())
    insert_test_source(store)

    with pytest.raises(SourceNotFoundError):
        await service.summarize(
            SummarizeSourceRequest(
                collection="docs",
                source_path="0123456789ab/guide.md",
                focus="zzzunmatched",
            )
        )

    assert factory_calls == []


@pytest.mark.anyio
async def test_focused_summary_paginates_all_matching_chunks_from_the_real_store(
    tmp_path: Path,
) -> None:
    fake = FakeHy3(
        summaries=[Hy3SummaryPayload(summary="late evidence", used_evidence_ids=("S45",))]
    )
    service, store, _factory_calls = make_service(tmp_path, fake)
    insert_test_source(store, chunks=tuple(f"Hy3 fact {index}" for index in range(45)))
    original_search = store._search_with_fts
    calls: list[tuple[tuple[str, ...], int, int]] = []

    def recording_search(
        connection,
        collection,
        fts_query,
        like_terms,
        source_paths,
        limit,
        offset,
    ):
        calls.append((tuple(source_paths), limit, offset))
        return original_search(
            connection,
            collection,
            fts_query,
            like_terms,
            source_paths,
            limit,
            offset,
        )

    store._search_with_fts = recording_search  # type: ignore[method-assign]

    result = await service.summarize(
        SummarizeSourceRequest(
            collection="docs",
            source_path="0123456789ab/guide.md",
            focus="Hy3",
        )
    )

    assert result.used_evidence_ids == ("S45",)
    assert result.citations[0].line_start == 45
    assert [offset for _paths, _limit, offset in calls] == [0, 40]
    assert all(limit == 40 for _paths, limit, _offset in calls)
    assert all(paths == ("0123456789ab/guide.md",) for paths, _limit, _offset in calls)
    assert "Hy3 fact 44" in fake.summary_messages[0][1]["content"]


@pytest.mark.anyio
async def test_focused_summary_rejects_non_progressing_pagination(tmp_path: Path) -> None:
    fake = FakeHy3(summaries=[Hy3SummaryPayload(summary="partial", used_evidence_ids=("S1",))])
    service, store, factory_calls = make_service(tmp_path, fake)
    insert_test_source(store)

    def broken_search(*_args, **_kwargs):
        return [], 2

    store._search_with_fts = broken_search  # type: ignore[method-assign]

    with pytest.raises(KnowledgeBaseError, match="pagination"):
        await service.summarize(
            SummarizeSourceRequest(
                collection="docs",
                source_path="0123456789ab/guide.md",
                focus="Hy3",
            )
        )

    assert factory_calls == []


@pytest.mark.anyio
async def test_focused_summary_rejects_chunks_from_another_source(tmp_path: Path) -> None:
    fake = FakeHy3(summaries=[Hy3SummaryPayload(summary="bad", used_evidence_ids=("S1",))])
    service, store, factory_calls = make_service(tmp_path, fake)
    insert_test_source(store)
    original_search = store._search_with_fts

    def foreign_search(*args, **kwargs):
        rows, _total = original_search(*args, **kwargs)
        foreign_row = dict(rows[0])
        foreign_row["source_path"] = "0123456789ab/other.md"
        return [foreign_row], 1

    store._search_with_fts = foreign_search  # type: ignore[method-assign]

    with pytest.raises(KnowledgeBaseError, match="pagination"):
        await service.summarize(
            SummarizeSourceRequest(
                collection="docs",
                source_path="0123456789ab/guide.md",
                focus="Hy3",
            )
        )

    assert factory_calls == []


@pytest.mark.anyio
async def test_close_before_client_creation_permanently_rejects_remote_work(
    tmp_path: Path,
) -> None:
    fake = FakeHy3(
        answers=[
            Hy3AnswerPayload(answer="Hy3", used_evidence_ids=("S1",), insufficient_evidence=False)
        ]
    )
    service, store, factory_calls = make_service(tmp_path, fake)
    insert_test_source(store)

    await service.close()
    assert factory_calls == []

    with pytest.raises(Hy3ResponseError, match="closed"):
        await service.ask(AskRequest(collection="docs", question="What is Hy3?"))

    await service.close()

    assert factory_calls == []
    assert fake.closed == 0


def answer_budget(service: KnowledgeBaseService, question: str, chunks) -> int:
    messages = build_answer_messages(question, assign_evidence(chunks))
    return (
        _message_chars(messages)
        + answer_schema_chars()
        + service.settings.prompt_reserve_chars
        + service.settings.max_output_tokens * 8
    )


def summary_budget(service: KnowledgeBaseService, focus: str | None, chunks) -> int:
    messages = build_summary_messages(focus, assign_evidence(chunks))
    return (
        _message_chars(messages)
        + summary_schema_chars()
        + service.settings.prompt_reserve_chars
        + service.settings.max_output_tokens * 8
    )


@pytest.mark.anyio
async def test_repair_budget_is_rechecked_before_second_call(tmp_path: Path) -> None:
    fake = FakeHy3(
        answers=[
            Hy3AnswerPayload(answer="bad", used_evidence_ids=("S9",), insufficient_evidence=False)
        ]
    )
    service, store, _factory_calls = make_service(tmp_path, fake)
    insert_test_source(store)
    chunks = store.get_source_chunks("docs", PurePosixPath("0123456789ab/guide.md"))
    service.settings = service.settings.model_copy(
        update={"max_context_chars": answer_budget(service, "What is Hy3?", chunks)}
    )

    with pytest.raises(LimitExceededError, match="Citation repair"):
        await service.ask(AskRequest(collection="docs", question="What is Hy3?"))

    assert len(fake.answer_messages) == 1


@pytest.mark.anyio
async def test_concurrent_first_remote_calls_share_one_client(tmp_path: Path) -> None:
    fake = FakeHy3(
        answers=[
            Hy3AnswerPayload(answer="one", used_evidence_ids=("S1",), insufficient_evidence=False),
            Hy3AnswerPayload(answer="two", used_evidence_ids=("S1",), insufficient_evidence=False),
        ]
    )
    service, store, factory_calls = make_service(tmp_path, fake)
    insert_test_source(store)

    await asyncio.gather(
        service.ask(AskRequest(collection="docs", question="What is Hy3?")),
        service.ask(AskRequest(collection="docs", question="What is Hy3?")),
    )

    assert factory_calls == [1]


class BlockingCloseHy3(FakeHy3):
    def __init__(self) -> None:
        super().__init__(
            answers=[
                Hy3AnswerPayload(
                    answer="one", used_evidence_ids=("S1",), insufficient_evidence=False
                )
            ]
        )
        self.close_started = asyncio.Event()
        self.release_close = asyncio.Event()

    async def close(self) -> None:
        self.close_started.set()
        await self.release_close.wait()
        self.closed += 1


class BlockingRemoteHy3(FakeHy3):
    def __init__(self) -> None:
        super().__init__(
            answers=[
                Hy3AnswerPayload(
                    answer="ok", used_evidence_ids=("S1",), insufficient_evidence=False
                )
            ],
            summaries=[Hy3SummaryPayload(summary="ok", used_evidence_ids=("S1",))],
        )
        self.remote_started = asyncio.Event()
        self.release_remote = asyncio.Event()
        self.close_started = asyncio.Event()

    async def answer(self, messages, *, reasoning_effort):
        self.answer_messages.append(messages)
        self.remote_started.set()
        await self.release_remote.wait()
        return self.answers[0]

    async def summarize(self, messages, *, reasoning_effort):
        self.summary_messages.append(messages)
        self.remote_started.set()
        await self.release_remote.wait()
        return self.summaries[0]

    async def close(self) -> None:
        self.close_started.set()
        self.closed += 1


@pytest.mark.anyio
@pytest.mark.parametrize("operation", ["answer", "summary"])
async def test_close_waits_for_active_remote_workflow(tmp_path: Path, operation: str) -> None:
    fake = BlockingRemoteHy3()
    service, store, _factory_calls = make_service(tmp_path, fake)
    insert_test_source(store)
    if operation == "answer":
        remote = asyncio.create_task(
            service.ask(AskRequest(collection="docs", question="What is Hy3?"))
        )
    else:
        remote = asyncio.create_task(
            service.summarize(
                SummarizeSourceRequest(collection="docs", source_path="0123456789ab/guide.md")
            )
        )

    await fake.remote_started.wait()
    closing = asyncio.create_task(service.close())
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(fake.close_started.wait(), timeout=0.05)

    fake.release_remote.set()
    await remote
    await closing

    assert fake.closed == 1


class FailOnceCloseHy3(FakeHy3):
    def __init__(self) -> None:
        super().__init__(
            answers=[
                Hy3AnswerPayload(
                    answer="ok", used_evidence_ids=("S1",), insufficient_evidence=False
                )
            ]
        )
        self.close_calls = 0
        self.first_close_started = asyncio.Event()
        self.release_first_close = asyncio.Event()

    async def close(self) -> None:
        self.close_calls += 1
        if self.close_calls == 1:
            self.first_close_started.set()
            await self.release_first_close.wait()
            raise RuntimeError("close failed")


def hierarchical_payloads() -> list[Hy3SummaryPayload]:
    partial = "partial " + "y" * 200
    return [
        Hy3SummaryPayload(summary=partial, used_evidence_ids=("S1",)),
        Hy3SummaryPayload(summary=partial, used_evidence_ids=("S2",)),
        Hy3SummaryPayload(summary=partial, used_evidence_ids=("S3",)),
        Hy3SummaryPayload(summary=partial, used_evidence_ids=("S4",)),
        Hy3SummaryPayload(summary=partial, used_evidence_ids=("S1", "S2")),
        Hy3SummaryPayload(summary=partial, used_evidence_ids=("S3", "S4")),
        Hy3SummaryPayload(summary="final", used_evidence_ids=("S1", "S2", "S3", "S4")),
    ]


@pytest.mark.anyio
async def test_summary_uses_multiple_reduction_levels_without_truncation(tmp_path: Path) -> None:
    fake = FakeHy3(summaries=hierarchical_payloads())
    service, store, _factory_calls = make_service(tmp_path, fake)
    source_chunks = tuple(f"Hy3 fact {index} " + "x" * 500 for index in range(4))
    insert_test_source(store, chunks=source_chunks)
    fixed_cost = (
        summary_schema_chars()
        + service.settings.prompt_reserve_chars
        + service.settings.max_output_tokens * 8
    )
    service.settings = service.settings.model_copy(
        update={"max_context_chars": fixed_cost + 1450, "max_summary_requests": 7}
    )

    result = await service.summarize(
        SummarizeSourceRequest(collection="docs", source_path="0123456789ab/guide.md")
    )

    assert result.summary == "final"
    assert result.used_evidence_ids == ("S1", "S2", "S3", "S4")
    assert len(fake.summary_messages) == 7
    initial_messages = fake.summary_messages[:4]
    assert all(
        chunk in message[1]["content"]
        for chunk, message in zip(source_chunks, initial_messages, strict=True)
    )
    assert "Untrusted reduction data:" in fake.summary_messages[-1][1]["content"]


@pytest.mark.anyio
async def test_summary_request_ceiling_is_rechecked_before_each_reduction_level(
    tmp_path: Path,
) -> None:
    fake = FakeHy3(summaries=hierarchical_payloads())
    service, store, _factory_calls = make_service(tmp_path, fake)
    insert_test_source(
        store,
        chunks=tuple(f"Hy3 fact {index} " + "x" * 500 for index in range(4)),
    )
    fixed_cost = (
        summary_schema_chars()
        + service.settings.prompt_reserve_chars
        + service.settings.max_output_tokens * 8
    )
    service.settings = service.settings.model_copy(
        update={"max_context_chars": fixed_cost + 1450, "max_summary_requests": 6}
    )

    with pytest.raises(LimitExceededError, match="remote request budget"):
        await service.summarize(
            SummarizeSourceRequest(collection="docs", source_path="0123456789ab/guide.md")
        )

    assert len(fake.summary_messages) == 6


@pytest.mark.anyio
async def test_summary_rejects_cross_batch_citations_immediately(tmp_path: Path) -> None:
    fake = FakeHy3(
        summaries=[
            Hy3SummaryPayload(summary="bad", used_evidence_ids=("S2",)),
        ]
    )
    service, store, _factory_calls = make_service(tmp_path, fake)
    insert_test_source(store, chunks=("Hy3 " + "x" * 2000, "Hy3 " + "y" * 2000))
    fixed_cost = (
        summary_schema_chars()
        + service.settings.prompt_reserve_chars
        + service.settings.max_output_tokens * 8
    )
    service.settings = service.settings.model_copy(update={"max_context_chars": fixed_cost + 3000})

    with pytest.raises(CitationValidationError):
        await service.summarize(
            SummarizeSourceRequest(collection="docs", source_path="0123456789ab/guide.md")
        )

    assert len(fake.summary_messages) == 1


@pytest.mark.anyio
async def test_overlong_single_summary_chunk_fails_before_client_creation(tmp_path: Path) -> None:
    service, store, factory_calls = make_service(tmp_path, FakeHy3())
    insert_test_source(store, chunks=("Hy3 " + "x" * 1000,))
    chunks = store.get_source_chunks("docs", PurePosixPath("0123456789ab/guide.md"))
    service.settings = service.settings.model_copy(
        update={"max_context_chars": summary_budget(service, None, chunks) - 1}
    )

    with pytest.raises(LimitExceededError, match="One evidence chunk"):
        await service.summarize(
            SummarizeSourceRequest(collection="docs", source_path="0123456789ab/guide.md")
        )

    assert factory_calls == []
