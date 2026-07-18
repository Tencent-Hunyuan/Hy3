"""查询计划、搜索结果与上下文预算。"""

from __future__ import annotations

import asyncio
import re
import unicodedata

from .models import (
    Evidence,
    QueryPlan,
    RetrievedChunk,
    RetrievedPage,
    SearchHit,
    SearchRequest,
    SearchResult,
)
from .store import SQLiteStore

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u3400-\u9fff]+", re.UNICODE)
RESPONSE_INSTRUCTION = re.compile(
    r"(?:"
    r"^仅(?:回复|回答|输出)[\s\S]*$"
    r"|(?<=[!?])[ \t]*仅(?:回复|回答|输出)[\s\S]*$"
    r"|(?:^|(?<=[。!?;\n]))[ \t]*请仅(?:回复|回答|输出)[\s\S]*$"
    r"|(?:^|(?<=[.!?;\n]))[ \t]*respond\s+with\s+only\b[\s\S]*$"
    r")",
    re.IGNORECASE,
)
ASCII_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "did",
    "do",
    "does",
    "for",
    "how",
    "in",
    "is",
    "of",
    "on",
    "only",
    "or",
    "respond",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}
MAX_FTS_TERMS = 64
MAX_LIKE_TERMS = 32
CONTEXT_SEPARATOR = "\n\n"


def _quote_fts_term(term: str) -> str:
    """将单一词项编译为不具操作符语义的 FTS5 短语。"""
    return f'"{term.replace(chr(34), chr(34) * 2)}"'


def _ordered_unique(values: list[str], *, case_insensitive: bool = False) -> tuple[str, ...]:
    """按首次出现顺序去重, 并可使用 Unicode casefold 比较。"""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold() if case_insensitive else value
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


def _cjk_trigrams(value: str) -> tuple[str, ...]:
    """生成连续中文文本的重叠三元组。"""
    if len(value) < 3:
        return ()
    return _ordered_unique([value[index : index + 3] for index in range(len(value) - 2)])


def build_query_plan(query: str) -> QueryPlan:
    """将自然语言查询编译为有界、安全且可复现的 FTS/LIKE 计划。"""
    normalized_unicode = unicodedata.normalize("NFKC", query)
    without_instruction = RESPONSE_INSTRUCTION.sub("", normalized_unicode)
    normalized = " ".join(without_instruction.strip().split())
    terms = tuple(TOKEN_PATTERN.findall(normalized))
    fts_terms: list[str] = []
    cjk_short_terms: list[str] = []
    ascii_short_terms: list[str] = []
    for term in terms:
        if term.isascii():
            if term.casefold() in ASCII_STOPWORDS:
                continue
            if len(term) >= 3:
                fts_terms.append(term)
            else:
                ascii_short_terms.append(term)
        elif len(term) >= 3:
            fts_terms.extend(_cjk_trigrams(term))
        else:
            cjk_short_terms.append(term)

    unique_fts = _ordered_unique(fts_terms, case_insensitive=True)[:MAX_FTS_TERMS]
    short_terms = cjk_short_terms + ([] if unique_fts else ascii_short_terms)
    unique_short = _ordered_unique(short_terms, case_insensitive=True)[:MAX_LIKE_TERMS]
    fts_query = " OR ".join(_quote_fts_term(term) for term in unique_fts) or None
    return QueryPlan(
        normalized_query=normalized,
        fts_query=fts_query,
        like_terms=unique_short,
    )


def select_context_chunks(
    chunks: tuple[RetrievedChunk, ...],
    *,
    max_context_chars: int,
) -> tuple[RetrievedChunk, ...]:
    """按真实分隔符成本选择证据, 并安全截断首个超限分块。"""
    if max_context_chars <= 0:
        return ()
    selected: list[RetrievedChunk] = []
    used = 0
    for chunk in chunks:
        if not chunk.text:
            continue
        separator_cost = len(CONTEXT_SEPARATOR) if selected else 0
        cost = separator_cost + len(chunk.text)
        if selected and used + cost > max_context_chars:
            break
        if not selected and cost > max_context_chars:
            truncated = chunk.text[:max_context_chars]
            if truncated:
                selected.append(chunk.model_copy(update={"text": truncated}))
            break
        selected.append(chunk)
        used += cost
    return tuple(selected)


def assign_evidence(chunks: tuple[RetrievedChunk, ...]) -> tuple[Evidence, ...]:
    """仅对预算内分块按最终顺序分配稳定证据编号。"""
    return tuple(
        Evidence(
            evidence_id=f"S{index}",
            chunk_id=chunk.chunk_id,
            source_path=chunk.source_path,
            text=chunk.text,
            page_number=chunk.page_number,
            line_start=chunk.line_start,
            line_end=chunk.line_end,
        )
        for index, chunk in enumerate(chunks, start=1)
    )


def build_search_result(
    request: SearchRequest,
    page: RetrievedPage,
    *,
    snippet_chars: int,
) -> SearchResult:
    """将本地分页转换为稳定编号、固定摘要长度的公开结果。"""
    evidence = assign_evidence(page.items)
    hits = tuple(
        SearchHit(
            evidence_id=item.evidence_id,
            source_path=item.source_path,
            page_number=item.page_number,
            line_start=item.line_start,
            line_end=item.line_end,
            score=page.items[index].rank,
            snippet=item.text[:snippet_chars],
        )
        for index, item in enumerate(evidence)
    )
    return SearchResult(
        query=request.query,
        total=page.total,
        count=len(hits),
        offset=request.offset,
        has_more=page.has_more,
        next_offset=page.next_offset,
        results=hits,
    )


async def search_store(request: SearchRequest, store: SQLiteStore) -> SearchResult:
    """在线程中执行只读 SQLite 检索, 并返回公开搜索结果。"""
    plan = build_query_plan(request.query)
    if plan.fts_query is None and not plan.like_terms:
        await asyncio.to_thread(store.ensure_collection_exists, request.collection)
        page = RetrievedPage(total=0, items=(), has_more=False)
    else:
        page = await asyncio.to_thread(
            store.search,
            request.collection,
            plan.fts_query,
            plan.like_terms,
            request.source_paths,
            request.limit,
            request.offset,
        )
    return build_search_result(request, page, snippet_chars=240)
