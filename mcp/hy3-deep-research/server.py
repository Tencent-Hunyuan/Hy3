"""Hy3 Deep Research MCP Server

业界常见流水线：澄清/计划 → 并行检索与精读 → 反思补洞 → 带引用终稿。
参考 OpenAI / Gemini Deep Research 与 LangChain Open Deep Research 的编排思路，
将研究闭环收进 Server，同时保留原子 search/fetch 供细控。
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
from mcp.server.fastmcp import FastMCP
from openai import OpenAI

mcp = FastMCP(
    "hy3-deep-research",
    instructions=(
        "深度研究助手（Hy3）。推荐流程：\n"
        "1) clarify_or_plan 生成研究计划\n"
        "2) run_deep_research 执行多轮检索/反思\n"
        "3) critique_and_finalize 审稿并输出带引用终稿\n"
        "也可单独调用 web_search / fetch_url 做细粒度控制。"
    ),
)

DEFAULT_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
DEFAULT_MODEL = "hy3"
USER_AGENT = "Hy3DeepResearchMCP/2.0 (+https://github.com/Tencent-Hunyuan/Hy3)"


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
            "缺少环境变量 HY3_API_KEY。请在 MCP 客户端配置 env，或 export HY3_API_KEY=..."
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


def _do_web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    max_results = max(1, min(int(max_results), 10))
    if _mock():
        return [
            {
                "title": f"（mock）{query} — 来源 {i}",
                "url": f"https://example.com/research/{abs(hash(query + str(i))) % 10000}",
                "snippet": f"与「{query}」相关的模拟摘要 #{i}，含可引用观点与背景。",
            }
            for i in range(1, max_results + 1)
        ]

    headers = {"User-Agent": USER_AGENT}
    results: list[dict[str, str]] = []
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
        resp = client.get("https://html.duckduckgo.com/html/", params={"q": query})
        resp.raise_for_status()
        blocks = re.findall(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</(?:a|td|div)',
            resp.text,
            flags=re.S | re.I,
        )
        for href, title, snippet in blocks[:max_results]:
            results.append(
                {
                    "title": _strip_html(title)[:200],
                    "url": href,
                    "snippet": _strip_html(snippet)[:400],
                }
            )
        if results:
            return results
        ia = client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
        )
        ia.raise_for_status()
        data = ia.json()
        if data.get("AbstractText"):
            results.append(
                {
                    "title": data.get("Heading") or query,
                    "url": data.get("AbstractURL") or "",
                    "snippet": data.get("AbstractText", "")[:400],
                }
            )
        for topic in (data.get("RelatedTopics") or [])[: max_results - len(results)]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(
                    {
                        "title": topic.get("Text", "")[:80],
                        "url": topic.get("FirstURL") or "",
                        "snippet": topic.get("Text", "")[:400],
                    }
                )
    return results[:max_results]


def _do_fetch_url(url: str, max_chars: int = 6000) -> dict[str, Any]:
    max_chars = max(500, min(int(max_chars), 20000))
    if _mock():
        return {
            "url": url,
            "title": "（mock）页面标题",
            "text": f"模拟正文来自 {url}。" + f"关键论点：关于该主题的可引用陈述。 " * 20,
            "chars": 200,
        }
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=40.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text
    title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    title = _strip_html(title_m.group(1)) if title_m else ""
    text = _strip_html(html)[:max_chars]
    return {"url": url, "title": title, "text": text, "chars": len(text)}


def _mock_plan(query: str) -> dict[str, Any]:
    return {
        "clarifying_questions": [],
        "research_brief": f"围绕「{query}」做多角度调研，区分事实与观点，给出可执行结论。",
        "sub_questions": [
            {"id": "SQ1", "question": f"{query} 的定义与背景是什么？", "angle": "背景"},
            {"id": "SQ2", "question": f"{query} 的主流做法与关键争议？", "angle": "现状"},
            {"id": "SQ3", "question": f"{query} 的证据缺口与风险？", "angle": "批判"},
        ],
        "stop_criteria": ["每个子问题至少 1 条可用来源", "明确写出不确定项"],
        "outline": ["执行摘要", "关键发现", "证据", "风险与缺口", "建议"],
    }


def _build_plan(query: str, extra_context: str = "") -> dict[str, Any]:
    if _mock():
        return _mock_plan(query)

    system = (
        "你是深度研究规划器。只输出 JSON，不要 Markdown 围栏。字段："
        "clarifying_questions(string[]),"
        "research_brief(string),"
        "sub_questions({id,question,angle}[] 3到6个),"
        "stop_criteria(string[]),"
        "outline(string[])。"
        "子问题应可并行检索，彼此少重叠。"
    )
    user = f"用户问题：{query}\n补充：{extra_context or '无'}"
    out = _call_hy3(
        system=system,
        user=user,
        enable_thinking=True,
        reasoning_effort="medium",
        max_tokens=2048,
        expect_json=True,
    )
    if isinstance(out.get("parsed"), dict):
        return out["parsed"]
    return _mock_plan(query)


def _reflect(session: ResearchSession) -> dict[str, Any]:
    evidence_brief = [
        {"eid": e.eid, "title": e.title, "url": e.url, "snippet": e.snippet[:180]}
        for e in session.evidence
    ]
    if _mock():
        # 第一轮制造缺口，第二轮足够
        if session.iteration < 1:
            return {
                "enough": False,
                "score": 0.45,
                "gaps": [f"缺少对「{session.query}」对立观点的一手来源"],
                "followup_queries": [f"{session.query} 争议 批评 风险"],
            }
        return {"enough": True, "score": 0.82, "gaps": [], "followup_queries": []}

    system = (
        "你是研究质量评审。只输出 JSON："
        "enough(bool), score(0-1), gaps(string[]), followup_queries(string[] 0到3个)。"
        "若证据不足或单一来源，enough=false 并给出跟进检索词。"
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
            f"## 执行摘要\n（MOCK）基于 {len(session.evidence)} 条证据完成多轮研究。\n\n"
            f"## 关键发现\n- 发现 A（引用 {cites}）\n- 发现 B\n\n"
            f"## 证据与引用\n{evidence_block}\n\n"
            f"## 风险与缺口\n" + ("；".join(session.gaps) or "暂无") + "\n\n"
            f"## 建议下一步\n补充一手资料并交叉验证。\n"
        )

    system = (
        "你是深度研究主笔。输出 Markdown 报告，章节含："
        "执行摘要、关键发现、证据与引用、风险与缺口、建议下一步。"
        "每条关键论断后用 [E#] 标注来自证据 id；禁止编造未出现的 URL/数据。"
    )
    user = (
        f"主题：{session.query}\n"
        f"研究简报：{session.plan.get('research_brief', '')}\n"
        f"大纲：{session.plan.get('outline', [])}\n\n"
        f"证据库：\n{evidence_block}"
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
        "1) 删除无引用支撑的硬断言或改为「待证实」；"
        "2) 保留 [E#] 引用；"
        "3) 增加「不确定性」小节；"
        "4) 不要新增虚假来源。"
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
    """对每个子查询：搜索 → 取前 N 条抓取正文 → 写入证据库。"""

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
            # 去重
            if any(e.url == url for e in session.evidence):
                continue
            quote = hit.get("snippet", "")
            title = hit.get("title", "")
            try:
                page = _do_fetch_url(url, max_chars=4000)
                title = page.get("title") or title
                quote = (page.get("text") or quote)[:600]
            except Exception as exc:  # noqa: BLE001
                session.log.append(f"fetch_fail:{url}:{exc}")
            eid = f"E{len(session.evidence) + len(found) + 1}"
            found.append(
                Evidence(
                    eid=eid,
                    url=url,
                    title=title,
                    snippet=hit.get("snippet", "")[:400],
                    quote=quote,
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


# ---------- MCP tools ----------


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """原子工具：网页搜索，返回标题/链接/摘要 JSON。"""
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
    max_iterations: int = 2,
    max_results_per_query: int = 4,
    fetch_top_per_query: int = 2,
) -> str:
    """执行深度研究闭环：按计划并行检索 → 精读 → 反思缺口 → 跟进检索 → 生成带引用草稿。

    若未提供 session_id，将用 query 自动创建计划。

    Args:
        session_id: clarify_or_plan 返回的会话 id
        query: 无 session 时的研究问题
        max_iterations: 反思补洞最大轮数（含首轮），默认 2
        max_results_per_query: 每个子查询搜索条数
        fetch_top_per_query: 每个子查询精读前几条
    """
    max_iterations = max(1, min(int(max_iterations), 4))
    max_results_per_query = max(1, min(int(max_results_per_query), 8))
    fetch_top_per_query = max(1, min(int(fetch_top_per_query), 4))

    if session_id and session_id in SESSIONS:
        session = SESSIONS[session_id]
    elif query.strip():
        plan = _build_plan(query)
        sid = uuid.uuid4().hex[:12]
        session = ResearchSession(session_id=sid, query=query, plan=plan)
        SESSIONS[sid] = session
    else:
        return json.dumps({"error": "需要 session_id 或 query"}, ensure_ascii=False)

    # 初始子查询
    sub_qs = [
        sq.get("question", "")
        for sq in (session.plan.get("sub_questions") or [])
        if isinstance(sq, dict) and sq.get("question")
    ]
    if not sub_qs:
        sub_qs = [session.query]

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
