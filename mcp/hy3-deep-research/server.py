"""Hy3 Deep Research MCP Server — 搜索 + 读页 + Hy3 分析 / 结论文档。"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from openai import OpenAI

mcp = FastMCP(
    "hy3-deep-research",
    instructions=(
        "深度研究助手：先用 web_search / fetch_url 收集资料，"
        "再用 hy3_analyze 与 hy3_research_report 调用混元 Hy3 完成分析与结论文档。"
    ),
)

DEFAULT_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
DEFAULT_MODEL = "hy3"


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


def _call_hy3(
    *,
    system: str,
    user: str,
    enable_thinking: bool = True,
    reasoning_effort: str = "high",
    max_tokens: int = 4096,
) -> dict[str, Any]:
    if _mock():
        return {
            "content": f"（MOCK）已根据输入生成分析草稿。\n\n用户问题摘要：{user[:200]}…",
            "reasoning": "（mock）先归纳来源要点，再对照问题作答，最后给风险与待查项。",
            "mock": True,
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
        temperature=0.3,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )
    msg = resp.choices[0].message
    return {
        "content": msg.content or "",
        "reasoning": getattr(msg, "reasoning_content", None),
        "mock": False,
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
    text = re.sub(r"\s+", " ", text).strip()
    return text


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """在网页上搜索与研究主题相关的结果（标题、链接、摘要）。

    Args:
        query: 搜索关键词或自然语言问题
        max_results: 返回条数，默认 5，最大 10
    """
    max_results = max(1, min(int(max_results), 10))
    if _mock():
        return json.dumps(
            {
                "query": query,
                "results": [
                    {
                        "title": f"（mock）关于「{query}」的资料 {i}",
                        "url": f"https://example.com/mock/{i}",
                        "snippet": f"这是与 {query} 相关的模拟摘要 #{i}。",
                    }
                    for i in range(1, max_results + 1)
                ],
                "note": "HY3_MOCK=1，未发起真实搜索",
            },
            ensure_ascii=False,
            indent=2,
        )

    # DuckDuckGo HTML（无需 API Key）；失败时回退到 Instant Answer API
    headers = {
        "User-Agent": "Hy3DeepResearchMCP/1.0 (+https://github.com/Tencent-Hunyuan/Hy3)"
    }
    results: list[dict[str, str]] = []
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
            )
            resp.raise_for_status()
            html = resp.text
            # 简易解析结果块
            blocks = re.findall(
                r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</(?:a|td|div)',
                html,
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
            if not results:
                # Instant Answer 兜底
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
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {"query": query, "error": str(exc), "results": []},
            ensure_ascii=False,
            indent=2,
        )

    return json.dumps(
        {"query": query, "results": results[:max_results]},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def fetch_url(url: str, max_chars: int = 8000) -> str:
    """抓取指定 URL 页面并提取纯文本，供后续 Hy3 分析使用。

    Args:
        url: 完整 http(s) 链接
        max_chars: 返回正文最大字符数，默认 8000
    """
    max_chars = max(500, min(int(max_chars), 20000))
    if _mock():
        return json.dumps(
            {
                "url": url,
                "title": "（mock）示例页面",
                "text": f"这是从 {url} 抓取的模拟正文，用于演示深度研究流水线。" * 3,
                "mock": True,
            },
            ensure_ascii=False,
            indent=2,
        )

    headers = {
        "User-Agent": "Hy3DeepResearchMCP/1.0 (+https://github.com/Tencent-Hunyuan/Hy3)"
    }
    try:
        with httpx.Client(timeout=40.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"url": url, "error": str(exc)}, ensure_ascii=False, indent=2)

    title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    title = _strip_html(title_m.group(1)) if title_m else ""
    text = _strip_html(html)[:max_chars]
    return json.dumps(
        {"url": url, "title": title, "text": text, "chars": len(text)},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def hy3_analyze(
    question: str,
    materials: str,
    enable_thinking: bool = True,
    reasoning_effort: str = "high",
) -> str:
    """用混元 Hy3 对已收集资料做深度分析（支持 thinking）。

    Args:
        question: 研究问题或分析目标
        materials: 资料文本（可粘贴搜索结果 / 页面正文 / 笔记）
        enable_thinking: 是否开启 Hy3 深度思考
        reasoning_effort: low / medium / high
    """
    system = (
        "你是深度研究分析助手，基于腾讯混元 Hy3。"
        "根据用户提供的资料回答问题：区分事实与推断，标注不确定处，"
        "必要时指出还缺哪些证据。使用简体中文。"
    )
    user = f"【研究问题】\n{question}\n\n【资料】\n{materials[:24000]}"
    out = _call_hy3(
        system=system,
        user=user,
        enable_thinking=enable_thinking,
        reasoning_effort=reasoning_effort,
        max_tokens=8192 if enable_thinking else 2048,
    )
    return json.dumps(out, ensure_ascii=False, indent=2)


@mcp.tool()
def hy3_research_report(
    topic: str,
    evidence: str,
    audience: str = "工程师 / 研究者",
    enable_thinking: bool = True,
) -> str:
    """基于证据生成结构化深度研究报告（结论、论据、风险、下一步）。

    Args:
        topic: 研究主题
        evidence: 证据汇总（搜索摘要、页面摘录、先前分析结果）
        audience: 报告读者画像
        enable_thinking: 是否开启深度思考
    """
    system = (
        "你是深度研究主笔，基于腾讯混元 Hy3。"
        "输出结构化 Markdown 报告，章节至少包含："
        "1) 执行摘要 2) 关键发现 3) 证据与引用提示 4) 不确定性与风险 5) 建议的下一步。"
        "不要编造未在证据中出现的具体数据；若证据不足请明确写出。"
        "使用简体中文。"
    )
    user = (
        f"【主题】{topic}\n"
        f"【读者】{audience}\n\n"
        f"【证据】\n{evidence[:28000]}"
    )
    out = _call_hy3(
        system=system,
        user=user,
        enable_thinking=enable_thinking,
        reasoning_effort="high",
        max_tokens=8192,
    )
    return json.dumps(out, ensure_ascii=False, indent=2)


def main() -> None:
    # stdio：由 Cursor / WorkBuddy / Cline 等客户端拉起
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
