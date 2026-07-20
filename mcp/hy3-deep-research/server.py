"""Hy3 Deep Research MCP Server
"""

from __future__ import annotations

import json
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from openai import OpenAI

# Key 优先来自 MCP 客户端 config 的 env（Cursor / WorkBuddy 注入）。
# .env 仅作本地/CLI 兜底，且不覆盖已存在的环境变量。
load_dotenv(override=False)

mcp = FastMCP(
    "hy3-deep-research",
    instructions=(
        "深度研究助手（Hy3）。检索默认仅使用学术源（arXiv / OpenAlex / Crossref）。\n"
        "报告重点：方法脉络与创新（范式演进、架构/训练相对前代差异）。\n"
        "推荐流程：\n"
        "1) clarify_or_plan 生成研究计划\n"
        "2) run_deep_research 执行多轮检索/反思\n"
        "3) critique_and_finalize 审稿并输出带引用终稿\n"
        "也可单独调用 web_search / fetch_url 做细粒度控制。"
    ),
)

DEFAULT_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
DEFAULT_MODEL = "hy3"
ACADEMIC_UA = "Hy3DeepResearchMCP/2.0 (academic-research; +https://github.com/Tencent-Hunyuan/Hy3)"


# ---------- session state ----------


@dataclass
class Evidence:
    eid: str
    url: str
    title: str
    snippet: str
    quote: str = ""
    sub_question: str = ""


@dataclass
class ResearchSession:
    session_id: str
    query: str
    plan: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    draft: str = ""
    report: str = ""
    iteration: int = 0


SESSIONS: dict[str, ResearchSession] = {}


def _mock() -> bool:
    return os.getenv("HY3_MOCK", "").lower() in {"1", "true", "yes"}


def _hy3_client() -> tuple[OpenAI, str]:
    api_key = os.getenv("HY3_API_KEY", "").strip()
    if not api_key and not _mock():
        raise RuntimeError(
            "缺少环境变量 HY3_API_KEY。"
            "请在 Cursor / WorkBuddy 的 MCP config env 中配置，或本地 export / .env。"
        )
    base_url = os.getenv("HY3_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.getenv("HY3_MODEL", DEFAULT_MODEL)
    return OpenAI(api_key=api_key or "mock", base_url=base_url, timeout=180.0), model


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", text)
        if m:
            return json.loads(m.group(0))
        raise


def _call_hy3(
    *,
    system: str,
    user: str,
    enable_thinking: bool = True,
    reasoning_effort: str = "medium",
    max_tokens: int = 4096,
    expect_json: bool = False,
) -> dict[str, Any]:
    if _mock():
        return {
            "content": f"（MOCK）{user[:180]}…",
            "reasoning": "（mock thinking）先拆解问题，再对齐证据，最后给结论与缺口。",
            "mock": True,
            "parsed": None,
        }

    client, model = _hy3_client()
    extra_body: dict[str, Any] = {
        "thinking": {"type": "enabled" if enable_thinking else "disabled"},
    }
    if enable_thinking:
        extra_body["reasoning_effort"] = reasoning_effort

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )
    msg = resp.choices[0].message
    content = msg.content or ""
    parsed = None
    if expect_json:
        try:
            parsed = _extract_json(content)
        except Exception:  # noqa: BLE001
            parsed = None
    return {
        "content": content,
        "reasoning": getattr(msg, "reasoning_content", None),
        "mock": False,
        "parsed": parsed,
        "usage": {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
            "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            "total_tokens": getattr(resp.usage, "total_tokens", None),
        }
        if resp.usage
        else None,
    }


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&\w+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _http_client(timeout: float = 30.0, *, accept: str = "application/json,text/xml,text/html,*/*") -> httpx.Client:
    # trust_env=False：避免继承 Cursor/系统代理导致误走不可达出口
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        trust_env=False,
        headers={
            "User-Agent": ACADEMIC_UA,
            "Accept": accept,
            "Accept-Language": "en,zh-CN;q=0.8",
        },
    )


_CJK_EN_REPLACEMENTS: list[tuple[str, str]] = [
    (r"视觉语言模型|视觉语言大模型|视觉\-语言模型", " vision language model "),
    (r"多模态大模型|多模态语言模型", " multimodal large language model "),
    (r"多模态", " multimodal "),
    (r"具身智能|具身", " embodied AI "),
    (r"大语言模型", " large language model "),
    (r"大模型", " foundation model "),
    (r"计算机视觉", " computer vision "),
    (r"自然语言", " natural language "),
    (r"综述|调研", " survey "),
    (r"进展|前沿", " progress "),
    (r"研究", " research "),
    (r"关键争议|争议", " debate "),
    (r"风险|缺口|局限", " limitations "),
    (r"主流做法|方法", " methods "),
    (r"定义与背景|背景", " background "),
    (r"评测|基准", " benchmark "),
    (r"开源", " open source "),
    (r"年", " "),
]


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _to_english_academic_query(query: str) -> str:
    """中文问题 → 适合 arXiv 的英文关键词（规则替换，失败则回退通用词）。"""
    en = f" {query} "
    for pat, rep in _CJK_EN_REPLACEMENTS:
        en = re.sub(pat, rep, en)
    en = re.sub(r"[\u4e00-\u9fff]+", " ", en)
    en = re.sub(r"[^\w\s\-.:\"']+", " ", en)
    # 裸年份易命中同名会议噪声，检索时去掉（写作仍可讨论年份）
    en = re.sub(r"\b20\d{2}\b", " ", en)
    en = re.sub(r"\s+", " ", en).strip()
    if len(en) < 6:
        return "vision language model multimodal survey"
    return en


def _is_vlm_topic(text: str) -> bool:
    t = text.lower()
    return any(
        k in t
        for k in (
            "vision language",
            "vision-language",
            "vlm",
            "lvlm",
            "mllm",
            "multimodal large",
            "视觉语言",
            "多模态",
        )
    )


def _academic_query_variants(query: str) -> list[str]:
    """生成偏「方法/架构/训练范式」的检索变体。"""
    variants: list[str] = []
    q = (query or "").strip()
    en = _to_english_academic_query(q) if _has_cjk(q) else _to_english_academic_query(q)
    # 去停用噪声词
    core = re.sub(
        r"\b(progress|research|study|overview|review)\b",
        " ",
        en,
        flags=re.I,
    )
    core = re.sub(r"\s+", " ", core).strip() or en

    method_variants = [
        f"{core} survey architecture paradigm",
        f"{core} visual encoder connector projector LLM",
        f"{core} instruction tuning alignment training",
        f"{core} hallucination grounding limitations",
    ]
    if _is_vlm_topic(q + " " + en):
        method_variants = [
            'survey "vision-language" OR "multimodal large language" architecture paradigm',
            "vision-language model visual encoder connector projector LLaVA",
            "multimodal large language model instruction tuning RLHF alignment",
            "large vision-language model hallucination grounding survey",
            "vision-language pre-training to MLLM evolution survey",
        ]

    for v in method_variants:
        if v and v.lower() not in {x.lower() for x in variants}:
            variants.append(v)
    return variants[:5]


def _result_dedupe_key(item: dict[str, str]) -> str:
    if item.get("arxiv_id"):
        return f"arxiv:{item['arxiv_id']}"
    if item.get("doi"):
        return f"doi:{item['doi'].lower()}"
    url = (item.get("url") or "").lower().rstrip("/")
    return f"url:{url}"


_METHOD_BOOST = (
    "survey",
    "architecture",
    "paradigm",
    "connector",
    "projector",
    "visual encoder",
    "instruction tuning",
    "alignment",
    "hallucination",
    "vision-language",
    "vision language",
    "multimodal large",
    "mllm",
    "lvlm",
    "pre-training",
    "pretraining",
    "llava",
    "qwen",
    "grounding",
)
_NOISE_PENALTY = (
    "rip current",
    "interspeech",
    "audio encoder",
    "open-ended survey responses",
    "one billion word",
    "statistical language modeling",
    "german",
    "beach",
)


def _relevance_score(item: dict[str, str], query: str) -> float:
    text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
    score = 0.0
    for term in _METHOD_BOOST:
        if term in text:
            score += 3.0 if term in {"survey", "architecture", "paradigm", "vision-language"} else 1.2
    for noise in _NOISE_PENALTY:
        if noise in text:
            score -= 6.0
    q = _to_english_academic_query(query).lower()
    for tok in q.split():
        if len(tok) > 3 and tok in text:
            score += 0.4
    year = item.get("year") or ""
    if year.isdigit():
        y = int(year)
        if y >= 2025:
            score += 2.0
        elif y >= 2023:
            score += 1.0
        elif y < 2018:
            score -= 2.0
    if "survey" in (item.get("title") or "").lower():
        score += 4.0
    return score


def _filter_and_rank(results: list[dict[str, str]], query: str, limit: int) -> list[dict[str, str]]:
    ranked = sorted(results, key=lambda x: _relevance_score(x, query), reverse=True)
    kept: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in ranked:
        key = _result_dedupe_key(item)
        if key in seen or not item.get("url"):
            continue
        # 丢弃明显跑题
        if _relevance_score(item, query) < 1.0 and len(kept) >= max(2, limit // 2):
            continue
        if _relevance_score(item, query) < -2.0:
            continue
        seen.add(key)
        item = dict(item)
        item["relevance"] = f"{_relevance_score(item, query):.1f}"
        kept.append(item)
        if len(kept) >= limit:
            break
    return kept


def _merge_academic_results(*batches: list[dict[str, str]], limit: int, query: str = "") -> list[dict[str, str]]:
    pooled: list[dict[str, str]] = []
    seen: set[str] = set()
    for batch in batches:
        for item in batch:
            key = _result_dedupe_key(item)
            if not item.get("url") or key in seen:
                continue
            seen.add(key)
            pooled.append(item)
    if query:
        return _filter_and_rank(pooled, query, limit)
    return pooled[:limit]


def _arxiv_search_expr(query: str) -> str:
    """构造更贴方法/综述的 arXiv boolean 查询。"""
    q = query.strip()
    if re.search(r"\b(AND|OR|ti:|abs:|all:)\b", q):
        # 已是表达式：仍去掉裸年份
        return re.sub(r"\b20\d{2}\b", " ", q).strip()
    en = _to_english_academic_query(q)
    if _is_vlm_topic(q + " " + en):
        low = en.lower()
        if "hallucination" in low or "limitation" in low or "grounding" in low:
            return (
                '(all:"vision-language" OR all:"large vision-language" OR all:LVLM OR all:MLLM)'
                " AND (all:hallucination OR all:grounding OR all:alignment OR all:survey)"
            )
        if "training" in low or "instruction" in low or "alignment" in low or "rlhf" in low:
            return (
                '(all:"multimodal large language" OR all:"vision-language model" OR all:MLLM)'
                " AND (all:training OR all:\"instruction tuning\" OR all:alignment OR all:RLHF OR all:survey)"
            )
        if "encoder" in low or "connector" in low or "projector" in low or "architecture" in low:
            return (
                '(ti:"vision-language" OR all:"vision language model" OR all:MLLM)'
                " AND (all:architecture OR all:connector OR all:projector OR all:encoder OR all:survey)"
            )
        # 默认：综述 + 范式演进
        return (
            '(ti:survey OR all:survey) AND '
            '(all:"vision-language" OR all:"vision language model" OR all:"multimodal large language" OR all:MLLM)'
        )
    # 通用：短语化
    words = [w for w in en.split() if len(w) > 2][:8]
    if len(words) >= 2:
        phrase = " ".join(words[:4])
        rest = " AND ".join(f"all:{w}" for w in words[4:7]) if len(words) > 4 else ""
        base = f'all:"{phrase}"'
        return f"({base})" + (f" AND ({rest})" if rest else "") + " AND (all:survey OR all:method OR all:architecture)"
    return f"all:{en}"


def _search_arxiv(client: httpx.Client, query: str, max_results: int) -> list[dict[str, str]]:
    expr = _arxiv_search_expr(query)
    # 多取一些再本地排序过滤
    fetch_n = min(max(max_results * 3, 8), 20)
    resp = client.get(
        "https://export.arxiv.org/api/query",
        params={
            "search_query": expr,
            "start": 0,
            "max_results": fetch_n,
            "sortBy": "relevance",
            "sortOrder": "descending",
        },
    )
    resp.raise_for_status()
    entries = re.findall(r"<entry>([\s\S]*?)</entry>", resp.text)
    results: list[dict[str, str]] = []
    for block in entries:
        def _tag(name: str) -> str:
            m = re.search(rf"<{name}[^>]*>([\s\S]*?)</{name}>", block)
            return _strip_html(m.group(1)).strip() if m else ""

        aid = _tag("id")
        arxiv_id = ""
        m_id = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+)(v\d+)?", aid)
        if m_id:
            arxiv_id = m_id.group(1)
        title = _tag("title")
        summary = _tag("summary")
        published = _tag("published")[:10]
        url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else aid
        if not title or not url:
            continue
        snippet = summary[:500]
        if published:
            snippet = f"[{published}] {snippet}"
        results.append(
            {
                "title": title[:200],
                "url": url,
                "snippet": snippet,
                "source": "arxiv",
                "venue": "arXiv",
                "arxiv_id": arxiv_id,
                "doi": "",
                "year": published[:4] if published else "",
            }
        )
    return _filter_and_rank(results, query, max_results)


def _openalex_abstract(inv: dict[str, list[int]] | None) -> str:
    if not inv:
        return ""
    pairs: list[tuple[int, str]] = []
    for word, positions in inv.items():
        for pos in positions:
            pairs.append((int(pos), str(word)))
    pairs.sort()
    return " ".join(w for _, w in pairs)


def _search_openalex(client: httpx.Client, query: str, max_results: int) -> list[dict[str, str]]:
    resp = client.get(
        "https://api.openalex.org/works",
        params={
            "search": query,
            "per_page": max_results,
            "sort": "relevance_score:desc",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    results: list[dict[str, str]] = []
    for work in data.get("results") or []:
        title = (work.get("display_name") or "").strip()
        loc = work.get("primary_location") or {}
        oa = work.get("open_access") or {}
        ids = work.get("ids") or {}
        doi = (ids.get("doi") or work.get("doi") or "").replace("https://doi.org/", "")
        arxiv_id = ""
        for loc_i in work.get("locations") or []:
            src = (loc_i.get("source") or {}).get("display_name") or ""
            land = loc_i.get("landing_page_url") or ""
            if "arxiv" in src.lower() or "arxiv.org" in land:
                m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+)", land)
                if m:
                    arxiv_id = m.group(1)
                    break
        url = (
            (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "")
            or oa.get("oa_url")
            or loc.get("landing_page_url")
            or (f"https://doi.org/{doi}" if doi else "")
            or ids.get("openalex")
            or ""
        )
        if not title or not url:
            continue
        # 跳过明显 PDF 直链作为唯一入口时仍保留；抓取阶段会跳过 PDF
        abstract = _openalex_abstract(work.get("abstract_inverted_index"))
        year = str(work.get("publication_year") or "")
        venue = ((loc.get("source") or {}).get("display_name") or "OpenAlex")[:120]
        snippet = abstract[:400] or f"{venue} ({year})".strip()
        results.append(
            {
                "title": title[:200],
                "url": url,
                "snippet": snippet,
                "source": "openalex",
                "venue": venue,
                "arxiv_id": arxiv_id,
                "doi": doi,
                "year": year,
            }
        )
    return results


def _search_crossref(client: httpx.Client, query: str, max_results: int) -> list[dict[str, str]]:
    q = _to_english_academic_query(query) if _has_cjk(query) else query
    resp = client.get(
        "https://api.crossref.org/works",
        params={
            "query": q,
            "rows": max_results,
            "sort": "relevance",
            "select": "DOI,title,abstract,URL,container-title,published-print,published-online,type",
        },
    )
    resp.raise_for_status()
    items = (resp.json().get("message") or {}).get("items") or []
    results: list[dict[str, str]] = []
    for it in items:
        titles = it.get("title") or []
        title = titles[0] if titles else ""
        doi = it.get("DOI") or ""
        url = it.get("URL") or (f"https://doi.org/{doi}" if doi else "")
        if not title or not url:
            continue
        # 过滤明显非学术条目可在此扩展；当前保留 Crossref 相关性排序结果
        containers = it.get("container-title") or []
        venue = containers[0] if containers else "Crossref"
        abstract = _strip_html(it.get("abstract") or "")[:400]
        year = ""
        for key in ("published-print", "published-online"):
            parts = ((it.get(key) or {}).get("date-parts") or [[]])[0]
            if parts:
                year = str(parts[0])
                break
        results.append(
            {
                "title": _strip_html(title)[:200],
                "url": url,
                "snippet": abstract or f"{venue} ({year})".strip(),
                "source": "crossref",
                "venue": str(venue)[:120],
                "arxiv_id": "",
                "doi": doi,
                "year": year,
            }
        )
    return results


def _do_web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """学术检索：arXiv → OpenAlex → Crossref（合并去重）。

    可选环境变量 HY3_SEARCH_ALLOW_WEB=1 时，才回退通用网页搜索（默认关闭）。
    """
    max_results = max(1, min(int(max_results), 10))
    if _mock():
        return [
            {
                "title": f"（mock arXiv）{query} — Paper {i}",
                "url": f"https://arxiv.org/abs/2401.{10000 + i}",
                "snippet": f"Abstract (mock): academic evidence about 「{query}」 #{i}.",
                "source": "arxiv",
                "venue": "arXiv",
                "arxiv_id": f"2401.{10000 + i}",
                "doi": "",
                "year": "2024",
            }
            for i in range(1, max_results + 1)
        ]

    errors: list[str] = []
    batches: list[list[dict[str, str]]] = []
    variants = _academic_query_variants(query)
    with _http_client(timeout=35.0) as client:
        arxiv_hits: list[dict[str, str]] = []
        for v in variants[:3]:
            try:
                arxiv_hits.extend(_search_arxiv(client, v, max_results=max_results))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"arxiv({v[:40]}): {exc}")
        batches.append(arxiv_hits)

        oa_hits: list[dict[str, str]] = []
        for v in variants[:2]:
            try:
                # OpenAlex 用不含 boolean 的简化词
                oa_q = re.sub(r"\b(AND|OR|ti:|abs:|all:)\b", " ", v)
                oa_q = re.sub(r'[()"]', " ", oa_q)
                oa_q = re.sub(r"\s+", " ", oa_q).strip()
                oa_hits.extend(_search_openalex(client, oa_q or query, max_results=max_results))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"openalex({v[:40]}): {exc}")
        batches.append(oa_hits)

        try:
            cr_q = _to_english_academic_query(query)
            batches.append(_search_crossref(client, cr_q, max_results=max_results))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"crossref: {exc}")

    merged = _merge_academic_results(*batches, limit=max_results, query=query)
    if merged:
        return merged

    if os.getenv("HY3_SEARCH_ALLOW_WEB", "").lower() in {"1", "true", "yes"}:
        # 显式开启时才用通用搜索；默认学术-only
        raise RuntimeError(
            "学术源无结果，且通用网页回退未实现为默认路径。"
            f" errors={'; '.join(errors)}"
        )

    raise RuntimeError(
        "学术检索失败（arXiv / OpenAlex / Crossref 均无可用结果）。详情: "
        + ("; ".join(errors) or "empty")
    )


def _do_fetch_url(url: str, max_chars: int = 6000) -> dict[str, Any]:
    max_chars = max(500, min(int(max_chars), 20000))
    if _mock():
        return {
            "url": url,
            "title": "（mock）学术论文标题",
            "text": f"模拟论文摘要来自 {url}。" + f"关键论点：关于该主题的可引用学术陈述。 " * 20,
            "chars": 200,
        }
    if re.search(r"\.pdf(\?|$)", url, flags=re.I):
        raise RuntimeError("跳过 PDF 直链抓取；请使用 arXiv abs / DOI 落地页或摘要字段")

    # arXiv abs → 优先拉 abstract 页
    m = re.search(r"arxiv\.org/(?:pdf|html)/([0-9]+\.[0-9]+)", url)
    if m:
        url = f"https://arxiv.org/abs/{m.group(1)}"

    with _http_client(timeout=40.0, accept="text/html,application/xhtml+xml,*/*") as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text
        final_url = str(resp.url)
    title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    title = _strip_html(title_m.group(1)) if title_m else ""
    # arXiv 摘要块
    abs_m = re.search(
        r'(?is)<blockquote[^>]*class="abstract"[^>]*>(.*?)</blockquote>',
        html,
    ) or re.search(r'(?is)<meta[^>]+name="citation_abstract"[^>]+content="([^"]+)"', html)
    if abs_m:
        text = _strip_html(abs_m.group(1))[:max_chars]
    else:
        text = _strip_html(html)[:max_chars]
    return {"url": final_url, "title": title, "text": text, "chars": len(text)}


def _mock_plan(query: str) -> dict[str, Any]:
    en = _to_english_academic_query(query) if _has_cjk(query) else query
    return {
        "clarifying_questions": [],
        "research_brief": (
            f"围绕「{query}」做方法中心的学术调研：梳理范式演进、架构/训练创新点与未解决问题；"
            "优先同行评审与高质量预印本综述。"
        ),
        "sub_questions": [
            {
                "id": "SQ1",
                "question": f"{query}：方法脉络如何从早期范式演进到当前主流？",
                "angle": "方法脉络",
                "search_query": f"{en} survey architecture paradigm evolution",
            },
            {
                "id": "SQ2",
                "question": f"{query}：近期架构与连接器/编码器侧有哪些关键创新？",
                "angle": "架构创新",
                "search_query": f"{en} visual encoder connector projector architecture",
            },
            {
                "id": "SQ3",
                "question": f"{query}：训练与对齐范式有哪些变化（指令微调/RLHF 等）？",
                "angle": "训练范式",
                "search_query": f"{en} instruction tuning alignment RLHF training",
            },
            {
                "id": "SQ4",
                "question": f"{query}：仍存的方法局限、幻觉与评测争议？",
                "angle": "局限",
                "search_query": f"{en} hallucination grounding limitations survey",
            },
        ],
        "stop_criteria": [
            "至少覆盖 2 个以上方法代际/范式，并说明相对前代的创新点",
            "每个子问题至少 1 条学术来源（arXiv/期刊/会议）",
            "明确写出不确定项与证据缺口",
        ],
        "outline": [
            "执行摘要",
            "方法脉络与创新",
            "关键发现",
            "证据与引用",
            "风险与缺口",
            "建议下一步",
        ],
    }


def _build_plan(query: str, extra_context: str = "") -> dict[str, Any]:
    if _mock():
        return _mock_plan(query)

    system = (
        "你是深度研究规划器（方法史/范式演进视角）。只输出 JSON，不要 Markdown 围栏。字段："
        "clarifying_questions(string[]),"
        "research_brief(string),"
        "sub_questions({id,question,angle,search_query}[] 4到6个),"
        "stop_criteria(string[]),"
        "outline(string[])。"
        "硬性要求："
        "1) 至少一半子问题聚焦方法脉络、架构创新、训练/对齐范式，而不是新闻热点；"
        "2) outline 必须包含「方法脉络与创新」且置于靠前位置；"
        "3) 每个 search_query 为英文学术语，优先含 survey/architecture/training/alignment 等；"
        "4) 不要用自媒体词；证据偏好 arXiv、CVPR/NeurIPS/ICML/ACL、期刊 DOI。"
    )
    user = (
        f"用户问题：{query}\n补充：{extra_context or '无'}\n"
        "约束：报告读者是研究者，最关心「方法怎么演进、相对前代创新在哪」。"
    )
    out = _call_hy3(
        system=system,
        user=user,
        enable_thinking=True,
        reasoning_effort="medium",
        max_tokens=2048,
        expect_json=True,
    )
    if isinstance(out.get("parsed"), dict):
        plan = out["parsed"]
        outline = plan.get("outline") or []
        if isinstance(outline, list) and not any("方法" in str(x) for x in outline):
            plan["outline"] = [
                "执行摘要",
                "方法脉络与创新",
                *[str(x) for x in outline if str(x) not in {"执行摘要", "方法脉络与创新"}],
            ]
        return plan
    return _mock_plan(query)


def _reflect(session: ResearchSession) -> dict[str, Any]:
    evidence_brief = [
        {"eid": e.eid, "title": e.title, "url": e.url, "snippet": e.snippet[:180]}
        for e in session.evidence
    ]
    if _mock():
        # 第一轮制造缺口，第二轮足够
        if session.iteration < 1:
            en = _to_english_academic_query(session.query)
            return {
                "enough": False,
                "score": 0.45,
                "gaps": ["缺少方法脉络（范式代际）与架构创新的学术综述"],
                "followup_queries": [
                    f"{en} survey architecture paradigm",
                    f"{en} visual encoder connector training",
                ],
            }
        return {"enough": True, "score": 0.82, "gaps": [], "followup_queries": []}

    system = (
        "你是学术研究质量评审（偏方法脉络）。只输出 JSON："
        "enough(bool), score(0-1), gaps(string[]), followup_queries(string[] 0到3个)。"
        "若缺少：方法代际/范式演进、架构或训练创新点、相对前代差异，则 enough=false。"
        "followup_queries 必须是英文学术语，优先 survey/architecture/training/alignment；"
        "禁止新闻/自媒体词，禁止只用年份关键词。"
    )
    user = json.dumps(
        {
            "query": session.query,
            "plan": session.plan,
            "evidence": evidence_brief,
            "iteration": session.iteration,
        },
        ensure_ascii=False,
    )
    out = _call_hy3(
        system=system,
        user=user,
        enable_thinking=True,
        reasoning_effort="medium",
        max_tokens=1500,
        expect_json=True,
    )
    if isinstance(out.get("parsed"), dict):
        return out["parsed"]
    return {"enough": True, "score": 0.7, "gaps": [], "followup_queries": []}


def _draft_report(session: ResearchSession) -> str:
    ev_lines = []
    for e in session.evidence:
        ev_lines.append(f"[{e.eid}] {e.title} | {e.url}\n摘要：{e.snippet}\n摘录：{e.quote[:400]}")
    evidence_block = "\n\n".join(ev_lines) or "（无证据）"

    if _mock():
        cites = ", ".join(e.eid for e in session.evidence[:5]) or "E1"
        return (
            f"# 研究报告：{session.query}\n\n"
            f"## 执行摘要\n（MOCK）基于 {len(session.evidence)} 条证据，聚焦方法脉络与创新。\n\n"
            f"## 方法脉络与创新\n"
            f"- 代际 A → 代际 B：关键变化是…（引用 {cites}）\n"
            f"- 创新点：相对前代解决了…仍缺…\n\n"
            f"## 关键发现\n- 发现 A（引用 {cites}）\n- 发现 B\n\n"
            f"## 证据与引用\n{evidence_block}\n\n"
            f"## 风险与缺口\n" + ("；".join(session.gaps) or "暂无") + "\n\n"
            f"## 建议下一步\n补充一手资料并交叉验证方法对比实验。\n"
        )

    system = (
        "你是学术深度研究主笔。读者是机器学习研究者，最关心方法脉络与创新。"
        "输出 Markdown，章节顺序必须为："
        "1) 执行摘要；"
        "2) 方法脉络与创新（必写，且为本报告主体，篇幅应最长）："
        "   按范式/代际梳理（如对齐预训练→桥接/连接器→LLM主干指令微调→统一多模态/RL对齐等，"
        "   以证据实际支持者为准，勿编造未出现的模型名）；"
        "   每个代际写清：代表思路、相对前代改了什么、解决什么问题、遗留问题；用 [E#]；"
        "3) 关键发现（可短）；"
        "4) 证据与引用；"
        "5) 风险与缺口；"
        "6) 建议下一步。"
        "禁止编造未出现的 URL/数据；弱相关证据明确降权；不要把会议同名噪声当作主题进展。"
    )
    user = (
        f"主题：{session.query}\n"
        f"研究简报：{session.plan.get('research_brief', '')}\n"
        f"大纲：{session.plan.get('outline', [])}\n"
        f"缺口：{session.gaps}\n\n"
        f"证据库：\n{evidence_block}\n\n"
        "写作重点：把「方法怎么演进、创新点是什么」写清楚；不要写成会议新闻或职场叙事。"
    )
    out = _call_hy3(
        system=system,
        user=user,
        enable_thinking=True,
        reasoning_effort="high",
        max_tokens=8192,
    )
    return out["content"]


def _finalize(session: ResearchSession, draft: str) -> str:
    if _mock():
        return draft + "\n\n---\n（MOCK 终稿）已完成引用审计与不确定性声明。\n"

    system = (
        "你是审稿与引用审计员。在草稿基础上输出终稿 Markdown："
        "1) 必须保留并强化「方法脉络与创新」章节；若草稿缺失则根据证据补写（仍禁止虚构来源）；"
        "2) 删除无引用支撑的硬断言或改为「待证实」；"
        "3) 保留 [E#] 引用；"
        "4) 增加「不确定性」小节；"
        "5) 不要新增虚假来源；弱相关证据不得支撑主线方法结论。"
    )
    evidence_index = "\n".join(f"{e.eid}: {e.url} | {e.title}" for e in session.evidence)
    user = f"证据索引：\n{evidence_index}\n\n草稿：\n{draft[:28000]}"
    out = _call_hy3(
        system=system,
        user=user,
        enable_thinking=True,
        reasoning_effort="high",
        max_tokens=8192,
    )
    return out["content"]


def _collect_for_queries(
    session: ResearchSession,
    queries: list[str],
    *,
    max_results: int,
    fetch_top: int,
) -> None:
    """对每个子查询：学术搜索 → 取前 N 条（优先摘要，必要时抓 abs 页）→ 写入证据库。"""

    def one(q: str) -> list[Evidence]:
        found: list[Evidence] = []
        try:
            hits = _do_web_search(q, max_results=max_results)
        except Exception as exc:  # noqa: BLE001
            session.log.append(f"search_fail:{q}:{exc}")
            return found
        for hit in hits[:fetch_top]:
            url = hit.get("url") or ""
            if not url:
                continue
            # 去重（URL / arXiv / DOI）
            doi = (hit.get("doi") or "").lower()
            arxiv_id = hit.get("arxiv_id") or ""
            if any(
                e.url == url
                or (arxiv_id and arxiv_id in e.url)
                or (doi and doi in e.url.lower())
                for e in session.evidence
            ):
                continue
            quote = hit.get("snippet", "")
            title = hit.get("title", "")
            source = hit.get("source", "")
            venue = hit.get("venue", "")
            # 已有足够长摘要则不必抓页；PDF 跳过
            need_fetch = len(quote) < 120 and not re.search(r"\.pdf(\?|$)", url, flags=re.I)
            if need_fetch:
                try:
                    page = _do_fetch_url(url, max_chars=4000)
                    title = page.get("title") or title
                    quote = (page.get("text") or quote)[:600]
                    url = page.get("url") or url
                except Exception as exc:  # noqa: BLE001
                    session.log.append(f"fetch_fail:{url}:{exc}")
            if venue or source:
                title = f"{title} [{venue or source}]"
            eid = f"E{len(session.evidence) + len(found) + 1}"
            found.append(
                Evidence(
                    eid=eid,
                    url=url,
                    title=title[:240],
                    snippet=hit.get("snippet", "")[:400],
                    quote=quote[:600],
                    sub_question=q,
                )
            )
        return found

    # 并行子查询
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(queries)))) as pool:
        futs = {pool.submit(one, q): q for q in queries if q.strip()}
        for fut in as_completed(futs):
            for ev in fut.result():
                # 再次统一编号
                ev.eid = f"E{len(session.evidence) + 1}"
                session.evidence.append(ev)
                session.log.append(f"evidence:{ev.eid}:{ev.url}")


def _plan_search_queries(session: ResearchSession) -> list[str]:
    """从计划提取检索词：优先英文学术 search_query。"""
    queries: list[str] = []
    for sq in session.plan.get("sub_questions") or []:
        if not isinstance(sq, dict):
            continue
        val = (sq.get("search_query") or sq.get("question") or "").strip()
        if val and val not in queries:
            queries.append(val)
    if not queries:
        queries = [session.query]
    return queries


# ---------- MCP tools ----------


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """原子工具：学术文献搜索（arXiv / OpenAlex / Crossref），返回标题/链接/摘要 JSON。"""
    try:
        results = _do_web_search(query, max_results=max_results)
        return json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"query": query, "error": str(exc), "results": []}, ensure_ascii=False)


@mcp.tool()
def fetch_url(url: str, max_chars: int = 8000) -> str:
    """原子工具：抓取 URL 纯文本。"""
    try:
        return json.dumps(_do_fetch_url(url, max_chars=max_chars), ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"url": url, "error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def clarify_or_plan(query: str, extra_context: str = "") -> str:
    """生成深度研究计划（研究简报、可并行子问题、停止条件、报告大纲）。

    Args:
        query: 用户研究问题
        extra_context: 已知约束、读者、时限等
    """
    plan = _build_plan(query, extra_context)
    sid = uuid.uuid4().hex[:12]
    session = ResearchSession(session_id=sid, query=query, plan=plan)
    session.log.append("created_plan")
    SESSIONS[sid] = session
    return json.dumps(
        {
            "session_id": sid,
            "query": query,
            "plan": plan,
            "next": "调用 run_deep_research(session_id=...) 执行多轮检索与反思",
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def run_deep_research(
    session_id: str = "",
    query: str = "",
    max_iterations: int = 3,
    max_results_per_query: int = 6,
    fetch_top_per_query: int = 3,
) -> str:
    """执行深度研究闭环：按计划并行检索 → 精读 → 反思缺口 → 跟进检索 → 生成带引用草稿。

    若未提供 session_id，将用 query 自动创建计划。

    Args:
        session_id: clarify_or_plan 返回的会话 id
        query: 无 session 时的研究问题
        max_iterations: 反思补洞最大轮数（含首轮），默认 3
        max_results_per_query: 每个子查询搜索条数
        fetch_top_per_query: 每个子查询精读前几条
    """
    max_iterations = max(1, min(int(max_iterations), 4))
    max_results_per_query = max(1, min(int(max_results_per_query), 10))
    fetch_top_per_query = max(1, min(int(fetch_top_per_query), 5))

    if session_id and session_id in SESSIONS:
        session = SESSIONS[session_id]
    elif query.strip():
        plan = _build_plan(query)
        sid = uuid.uuid4().hex[:12]
        session = ResearchSession(session_id=sid, query=query, plan=plan)
        SESSIONS[sid] = session
    else:
        return json.dumps({"error": "需要 session_id 或 query"}, ensure_ascii=False)

    # 初始子查询：优先英文学术 search_query
    sub_qs = _plan_search_queries(session)

    followups: list[str] = []
    for i in range(max_iterations):
        session.iteration = i
        session.log.append(f"iteration_start:{i}")
        queries = sub_qs if i == 0 else followups
        if not queries:
            session.log.append("no_more_queries")
            break

        _collect_for_queries(
            session,
            queries,
            max_results=max_results_per_query,
            fetch_top=fetch_top_per_query,
        )
        reflection = _reflect(session)
        session.gaps = list(reflection.get("gaps") or [])
        session.log.append(f"reflect:{json.dumps(reflection, ensure_ascii=False)[:500]}")
        if reflection.get("enough"):
            session.log.append("enough:true")
            break
        followups = [q for q in (reflection.get("followup_queries") or []) if str(q).strip()]
        for fq in followups:
            session.log.append(f"followup:{fq}")

    session.draft = _draft_report(session)
    return json.dumps(
        {
            "session_id": session.session_id,
            "query": session.query,
            "iterations": session.iteration + 1,
            "evidence_count": len(session.evidence),
            "evidence": [asdict(e) for e in session.evidence],
            "gaps": session.gaps,
            "log": session.log[-30:],
            "draft_markdown": session.draft,
            "next": "调用 critique_and_finalize(session_id=...) 生成终稿",
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def critique_and_finalize(session_id: str, draft_markdown: str = "") -> str:
    """对草稿做引用审计与不确定性审稿，输出终稿。

    Args:
        session_id: 研究会话 id
        draft_markdown: 可选；为空则使用 run_deep_research 产生的草稿
    """
    session = SESSIONS.get(session_id)
    if not session:
        return json.dumps({"error": f"未知 session_id: {session_id}"}, ensure_ascii=False)
    draft = draft_markdown.strip() or session.draft
    if not draft:
        return json.dumps({"error": "无草稿可审，请先 run_deep_research"}, ensure_ascii=False)
    session.report = _finalize(session, draft)
    session.log.append("finalized")
    return json.dumps(
        {
            "session_id": session.session_id,
            "query": session.query,
            "evidence_index": [{"eid": e.eid, "url": e.url, "title": e.title} for e in session.evidence],
            "report_markdown": session.report,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def get_research_status(session_id: str) -> str:
    """查看研究会话状态（计划、证据数量、缺口、日志）。"""
    session = SESSIONS.get(session_id)
    if not session:
        return json.dumps({"error": f"未知 session_id: {session_id}"}, ensure_ascii=False)
    return json.dumps(
        {
            "session_id": session.session_id,
            "query": session.query,
            "plan": session.plan,
            "evidence_count": len(session.evidence),
            "gaps": session.gaps,
            "iteration": session.iteration,
            "has_draft": bool(session.draft),
            "has_report": bool(session.report),
            "log": session.log[-40:],
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
