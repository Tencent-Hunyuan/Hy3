"""五个 MCP 工具共享的业务服务。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Protocol

from .citations import validate_answer_payload, validate_evidence_ids
from .config import Settings
from .errors import (
    CitationValidationError,
    Hy3ResponseError,
    LimitExceededError,
    SourceNotFoundError,
)
from .hy3_client import Hy3Client, answer_schema_chars, summary_schema_chars
from .indexing import IndexingService
from .models import (
    AllowedRoot,
    AskRequest,
    AskResult,
    Evidence,
    Hy3AnswerPayload,
    Hy3SummaryPayload,
    IndexDocumentsRequest,
    IndexDocumentsResult,
    ListSourcesRequest,
    ListSourcesResult,
    ReasoningEffort,
    RetrievedChunk,
    RetrievedPage,
    SearchRequest,
    SearchResult,
    SummarizeSourceRequest,
    SummaryResult,
)
from .prompts import (
    build_answer_messages,
    build_summary_messages,
    build_summary_reduction_messages,
)
from .retrieval import assign_evidence, build_query_plan, build_search_result
from .store import SQLiteStore


class Hy3Port(Protocol):
    """服务层依赖的最小 Hy3 接口。"""

    async def answer(
        self,
        messages: list[dict[str, str]],
        *,
        reasoning_effort: ReasoningEffort,
    ) -> Hy3AnswerPayload: ...

    async def summarize(
        self,
        messages: list[dict[str, str]],
        *,
        reasoning_effort: ReasoningEffort,
    ) -> Hy3SummaryPayload: ...

    async def close(self) -> None: ...


@dataclass(frozen=True)
class DerivedSummary:
    """已验证引用的模型派生摘要。"""

    summary: str
    evidence_ids: tuple[str, ...]


def _message_chars(messages: Sequence[dict[str, str]]) -> int:
    """计算完整消息角色与内容的字符成本。"""
    return sum(len(message["role"]) + len(message["content"]) for message in messages)


def _messages_fit(
    messages: Sequence[dict[str, str]],
    schema_chars: int,
    settings: Settings,
) -> bool:
    """按消息、Schema、提示预留和输出上界判断请求是否可发送。"""
    conservative_output_chars = settings.max_output_tokens * 8
    total = (
        _message_chars(messages)
        + schema_chars
        + settings.prompt_reserve_chars
        + conservative_output_chars
    )
    return total <= settings.max_context_chars


def _select_answer_chunks(
    question: str,
    chunks: tuple[RetrievedChunk, ...],
    settings: Settings,
) -> tuple[RetrievedChunk, ...]:
    """选择能以完整序列化消息发送的连续检索结果。"""
    selected: list[RetrievedChunk] = []
    for chunk in chunks:
        candidate = (*selected, chunk)
        messages = build_answer_messages(question, assign_evidence(candidate))
        if _messages_fit(messages, answer_schema_chars(), settings):
            selected.append(chunk)
            continue
        if not selected:
            raise LimitExceededError(
                "Question and one evidence chunk cannot fit the configured context budget"
            )
        break
    return tuple(selected)


def _partition_evidence(
    evidence: tuple[Evidence, ...],
    focus: str | None,
    settings: Settings,
) -> tuple[tuple[Evidence, ...], ...]:
    """在不截断来源内容的前提下划分首层摘要请求。"""
    batches: list[tuple[Evidence, ...]] = []
    current: list[Evidence] = []
    for item in evidence:
        candidate = (*current, item)
        if _messages_fit(
            build_summary_messages(focus, candidate),
            summary_schema_chars(),
            settings,
        ):
            current.append(item)
            continue
        if current:
            batches.append(tuple(current))
            current = [item]
        else:
            raise LimitExceededError(
                "One evidence chunk cannot fit the configured summary context budget"
            )
        if not _messages_fit(
            build_summary_messages(focus, tuple(current)),
            summary_schema_chars(),
            settings,
        ):
            raise LimitExceededError(
                "One evidence chunk cannot fit the configured summary context budget"
            )
    if current:
        batches.append(tuple(current))
    return tuple(batches)


def _partition_derived(
    values: tuple[DerivedSummary, ...],
    settings: Settings,
) -> tuple[tuple[DerivedSummary, ...], ...]:
    """划分归并请求, 并确保每轮至少能合并两个摘要。"""
    groups: list[tuple[DerivedSummary, ...]] = []
    current: list[DerivedSummary] = []
    for value in values:
        candidate = (*current, value)
        if _messages_fit(
            build_summary_reduction_messages(candidate),
            summary_schema_chars(),
            settings,
        ):
            current.append(value)
            continue
        if len(current) < 2:
            raise LimitExceededError(
                "Intermediate summaries cannot be reduced within the context budget"
            )
        groups.append(tuple(current))
        current = [value]
    if current:
        groups.append(tuple(current))
    if len(groups) >= len(values):
        raise LimitExceededError("Intermediate summaries cannot make reduction progress")
    return tuple(groups)


class KnowledgeBaseService:
    """组合本地索引、离线检索与有引用的远端生成。"""

    def __init__(
        self,
        *,
        settings: Settings,
        roots: tuple[AllowedRoot, ...],
        store: SQLiteStore,
        hy3_factory: Callable[[], Hy3Port] | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.indexer = IndexingService(settings, roots, store)
        self.hy3_factory = hy3_factory or (lambda: Hy3Client(settings))
        self._hy3: Hy3Port | None = None
        self._state_lock = asyncio.Lock()
        self._client_closed = False
        self._active_remote_operations = 0
        self._remote_idle = asyncio.Event()
        self._remote_idle.set()
        self._close_task: asyncio.Task[None] | None = None

    @asynccontextmanager
    async def _remote_client(self) -> AsyncIterator[Hy3Port]:
        """租用唯一客户端, 使完整远端工作流与关闭互斥。"""
        async with self._state_lock:
            if self._client_closed:
                raise Hy3ResponseError("Knowledge base service is closed")
            if self._hy3 is None:
                self._hy3 = self.hy3_factory()
            client = self._hy3
            self._active_remote_operations += 1
            self._remote_idle.clear()
        try:
            yield client
        finally:
            release_task = asyncio.create_task(self._release_remote_operation())
            await asyncio.shield(release_task)

    async def _release_remote_operation(self) -> None:
        """不可取消地释放远端操作计数。"""
        async with self._state_lock:
            self._active_remote_operations -= 1
            if self._active_remote_operations == 0:
                self._remote_idle.set()

    async def _close_when_idle(self, client: Hy3Port) -> None:
        """等待所有已获租约的工作流结束后关闭底层客户端。"""
        await self._remote_idle.wait()
        await client.close()

    async def close(self) -> None:
        """永久停止新远端工作, 等待租约并以可重试尝试关闭客户端。"""
        async with self._state_lock:
            self._client_closed = True
            if self._hy3 is None:
                return
            if self._close_task is None or self._close_task.done():
                if self._close_task is not None:
                    try:
                        self._close_task.result()
                    except BaseException:
                        pass
                    else:
                        return
                self._close_task = asyncio.create_task(self._close_when_idle(self._hy3))
            close_task = self._close_task
        await asyncio.shield(close_task)

    async def index(self, request: IndexDocumentsRequest) -> IndexDocumentsResult:
        return await self.indexer.index(request)

    async def search(self, request: SearchRequest) -> SearchResult:
        plan = build_query_plan(request.query)
        if plan.fts_query is None and not plan.like_terms:
            await asyncio.to_thread(self.store.ensure_collection_exists, request.collection)
            page = RetrievedPage(total=0, items=(), has_more=False)
        else:
            page = await asyncio.to_thread(
                self.store.search,
                request.collection,
                plan.fts_query,
                plan.like_terms,
                request.source_paths,
                request.limit,
                request.offset,
            )
        return build_search_result(request, page, snippet_chars=240)

    async def list_sources(self, request: ListSourcesRequest) -> ListSourcesResult:
        return await asyncio.to_thread(
            self.store.list_sources,
            request.collection,
            request.query,
            request.limit,
            request.offset,
        )

    async def ask(self, request: AskRequest) -> AskResult:
        plan = build_query_plan(request.question)
        if plan.fts_query is None and not plan.like_terms:
            await asyncio.to_thread(self.store.ensure_collection_exists, request.collection)
            page = RetrievedPage(total=0, items=(), has_more=False)
        else:
            page = await asyncio.to_thread(
                self.store.search,
                request.collection,
                plan.fts_query,
                plan.like_terms,
                request.source_paths,
                request.top_k,
                0,
            )
        selected = _select_answer_chunks(request.question, page.items, self.settings)
        evidence = assign_evidence(selected)
        if not evidence:
            return AskResult(
                answer="The knowledge base does not contain enough evidence.",
                grounded=False,
                insufficient_evidence=True,
                citations=(),
            )

        messages = build_answer_messages(request.question, evidence)
        effort = request.reasoning_effort or self.settings.reasoning_effort
        async with self._remote_client() as client:
            for attempt in range(2):
                payload = await client.answer(messages, reasoning_effort=effort)
                try:
                    return validate_answer_payload(payload, evidence)
                except CitationValidationError:
                    if attempt == 1:
                        raise
                    allowed = ", ".join(item.evidence_id for item in evidence)
                    repair_messages = [
                        *messages,
                        {
                            "role": "user",
                            "content": (
                                "Your previous structured response used invalid citations. "
                                "Return a corrected response using only these evidence IDs: "
                                f"{allowed}."
                            ),
                        },
                    ]
                    if not _messages_fit(repair_messages, answer_schema_chars(), self.settings):
                        raise LimitExceededError(
                            "Citation repair cannot fit the configured context budget"
                        ) from None
                    messages = repair_messages
        raise AssertionError("unreachable")

    async def summarize(self, request: SummarizeSourceRequest) -> SummaryResult:
        if request.focus:
            plan = build_query_plan(request.focus)
            if plan.fts_query is None and not plan.like_terms:
                chunks = await asyncio.to_thread(
                    self.store.get_source_chunks,
                    request.collection,
                    request.source_path,
                )
            else:
                chunks = await asyncio.to_thread(
                    self.store.search_source_chunks,
                    request.collection,
                    plan.fts_query,
                    plan.like_terms,
                    request.source_path,
                )
        else:
            chunks = await asyncio.to_thread(
                self.store.get_source_chunks,
                request.collection,
                request.source_path,
            )
        if not chunks:
            raise SourceNotFoundError("No indexed chunks matched the requested summary focus")

        evidence = assign_evidence(tuple(chunks))
        batches = _partition_evidence(evidence, request.focus, self.settings)
        if len(batches) > self.settings.max_summary_requests:
            raise LimitExceededError(
                "Source summary exceeds the configured remote request budget; narrow the focus"
            )

        effort = request.reasoning_effort or self.settings.reasoning_effort
        request_count = 0
        partials: list[DerivedSummary] = []
        async with self._remote_client() as client:
            for batch in batches:
                payload = await client.summarize(
                    build_summary_messages(request.focus, batch),
                    reasoning_effort=effort,
                )
                request_count += 1
                citations = validate_evidence_ids(payload.used_evidence_ids, batch)
                if not citations:
                    raise CitationValidationError(
                        "A Hy3 source summary must cite supplied evidence"
                    )
                partials.append(
                    DerivedSummary(
                        summary=payload.summary,
                        evidence_ids=tuple(item.evidence_id for item in citations),
                    )
                )

            while len(partials) > 1:
                groups = _partition_derived(tuple(partials), self.settings)
                required_calls = sum(len(group) > 1 for group in groups)
                if request_count + required_calls > self.settings.max_summary_requests:
                    raise LimitExceededError(
                        "Source summary exceeds the configured remote request budget; "
                        "narrow the focus"
                    )
                reduced: list[DerivedSummary] = []
                for group in groups:
                    if len(group) == 1:
                        reduced.append(group[0])
                        continue
                    allowed = tuple(
                        dict.fromkeys(
                            identifier for item in group for identifier in item.evidence_ids
                        )
                    )
                    payload = await client.summarize(
                        build_summary_reduction_messages(group),
                        reasoning_effort=effort,
                    )
                    request_count += 1
                    if any(identifier not in allowed for identifier in payload.used_evidence_ids):
                        raise CitationValidationError(
                            "Hy3 summary cited evidence outside validated intermediate summaries"
                        )
                    citations = validate_evidence_ids(payload.used_evidence_ids, evidence)
                    if not citations:
                        raise CitationValidationError(
                            "A synthesized Hy3 summary must cite supplied evidence"
                        )
                    reduced.append(
                        DerivedSummary(
                            summary=payload.summary,
                            evidence_ids=tuple(item.evidence_id for item in citations),
                        )
                    )
                partials = reduced

        final = partials[0]
        citations = validate_evidence_ids(final.evidence_ids, evidence)
        return SummaryResult(
            summary=final.summary,
            coverage="focused" if request.focus else "full",
            used_evidence_ids=final.evidence_ids,
            citations=citations,
        )
