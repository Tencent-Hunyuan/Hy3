"""Core retrieval and Hy3 tool-calling loop for Evidence Board."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


QUESTION_MIN_LENGTH = 10
QUESTION_MAX_LENGTH = 500
SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": "Search the bundled Hy3 knowledge base and return grounded excerpts.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A focused search query derived from the user's question.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


class EvidenceBoardError(Exception):
    """Base exception with a user-safe message."""


class ValidationError(EvidenceBoardError):
    """Raised when user input is invalid."""


class ProviderError(EvidenceBoardError):
    """Raised when the upstream model API fails."""


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    path: str
    url: str
    content: str

    def public(self, excerpt: str) -> dict[str, str]:
        return {
            "id": self.source_id,
            "title": self.title,
            "path": self.path,
            "url": self.url,
            "excerpt": excerpt,
        }


def normalize_question(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("问题必须是字符串。")
    question = " ".join(value.split())
    if len(question) < QUESTION_MIN_LENGTH:
        raise ValidationError(f"问题至少需要 {QUESTION_MIN_LENGTH} 个字符。")
    if len(question) > QUESTION_MAX_LENGTH:
        raise ValidationError(f"问题不能超过 {QUESTION_MAX_LENGTH} 个字符。")
    return question


def tokenize(text: str) -> list[str]:
    """Tokenize ASCII words plus individual CJK characters without dependencies."""
    return re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]", text.lower())


class KnowledgeBase:
    def __init__(self, sources: list[Source]):
        if not sources:
            raise ValueError("knowledge base must contain at least one source")
        self.sources = sources

    @classmethod
    def from_directory(cls, root: Path) -> "KnowledgeBase":
        sources: list[Source] = []
        for path in sorted(root.glob("*.md")):
            raw = path.read_text(encoding="utf-8")
            title_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
            url_match = re.search(r"^Source:\s*(https?://\S+)\s*$", raw, re.MULTILINE)
            sources.append(
                Source(
                    source_id=path.stem,
                    title=title_match.group(1).strip() if title_match else path.stem,
                    path=f"knowledge/{path.name}",
                    url=url_match.group(1) if url_match else "",
                    content=raw,
                )
            )
        return cls(sources)

    def search(self, query: str, limit: int = 4) -> list[dict[str, str]]:
        query_tokens = set(tokenize(query))
        if not query_tokens:
            return []
        ranked: list[tuple[int, str, Source, str]] = []
        for source in self.sources:
            best_score = 0
            best_excerpt = ""
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", source.content) if p.strip()]
            for paragraph in paragraphs:
                paragraph_tokens = tokenize(paragraph)
                overlap = sum(1 for token in paragraph_tokens if token in query_tokens)
                unique_overlap = len(query_tokens.intersection(paragraph_tokens))
                score = overlap + unique_overlap * 3
                if score > best_score:
                    best_score = score
                    best_excerpt = re.sub(r"\s+", " ", paragraph)[:700]
            if best_score:
                ranked.append((best_score, source.source_id, source, best_excerpt))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        return [source.public(excerpt) for _, _, source, excerpt in ranked[:limit]]


class ChatProvider(Protocol):
    mode: str

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Return an OpenAI-compatible assistant message."""


class OpenAICompatibleProvider:
    mode = "live"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        provider_kind: str = "selfhost",
        reasoning_effort: str = "low",
        timeout: float = 120.0,
    ):
        if not base_url or not api_key or not model:
            raise ValueError("base_url, api_key, and model are required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider_kind = provider_kind
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout

    def build_payload(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.9,
            "top_p": 1.0,
            "max_tokens": 4096,
        }
        if self.provider_kind == "openrouter":
            payload["reasoning"] = {"effort": self.reasoning_effort}
        else:
            payload["chat_template_kwargs"] = {"reasoning_effort": self.reasoning_effort}
        return payload

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = self.build_payload(messages, tools)
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "hy3-evidence-board/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ProviderError(f"Hy3 API 返回 HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderError(f"无法连接 Hy3 API: {exc}") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("Hy3 API 返回了无法解析的响应。") from exc
        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Hy3 API 响应缺少 choices[0].message。") from exc


class DemoProvider:
    """Deterministic provider for offline tests; never impersonates Hy3."""

    mode = "demo"

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        tool_messages = [message for message in messages if message.get("role") == "tool"]
        if not tool_messages:
            question = next(message["content"] for message in reversed(messages) if message.get("role") == "user")
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": f"demo_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": "search_knowledge_base",
                            "arguments": json.dumps({"query": question}, ensure_ascii=False),
                        },
                    }
                ],
            }
        evidence = json.loads(tool_messages[-1]["content"])
        lines = [
            "## 离线链路检查结果",
            "",
            "> 此内容由确定性 DemoProvider 生成，未调用 Hy3。",
            "",
        ]
        for item in evidence:
            lines.append(f"- **{item['title']}**：{item['excerpt']} [{item['id']}]")
        lines.append("")
        lines.append("配置真实端点后，Hy3 会基于同一批工具证据生成正式报告。")
        return {"role": "assistant", "content": "\n".join(lines)}


class ResearchAgent:
    def __init__(self, provider: ChatProvider, knowledge_base: KnowledgeBase, max_rounds: int = 3):
        self.provider = provider
        self.knowledge_base = knowledge_base
        self.max_rounds = max_rounds

    def run(self, raw_question: Any) -> dict[str, Any]:
        question = normalize_question(raw_question)
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "你是严谨的 Hy3 资料研究助手。必须先调用 search_knowledge_base；"
                    "只根据工具返回的材料回答，每条关键结论以 [source_id] 标注。"
                    "证据不足时明确说明，不得编造。"
                ),
            },
            {"role": "user", "content": question},
        ]
        trace: list[dict[str, Any]] = []
        evidence_by_id: dict[str, dict[str, str]] = {}
        for round_number in range(1, self.max_rounds + 1):
            assistant = self.provider.complete(messages, [SEARCH_TOOL])
            tool_calls = assistant.get("tool_calls") or []
            if not tool_calls:
                content = assistant.get("content")
                if not isinstance(content, str) or not content.strip():
                    raise ProviderError("模型既未返回文本，也未请求工具。")
                return {
                    "mode": self.provider.mode,
                    "question": question,
                    "answer": content,
                    "evidence": list(evidence_by_id.values()),
                    "trace": trace,
                }
            messages.append(assistant)
            for call in tool_calls:
                function = call.get("function") or {}
                if function.get("name") != "search_knowledge_base":
                    raise ProviderError(f"模型请求了未授权工具: {function.get('name', '<missing>')}")
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError as exc:
                    raise ProviderError("工具参数不是有效 JSON。") from exc
                query = arguments.get("query")
                if not isinstance(query, str) or not query.strip():
                    raise ProviderError("search_knowledge_base 缺少 query。")
                results = self.knowledge_base.search(query)
                for item in results:
                    evidence_by_id[item["id"]] = item
                trace.append(
                    {
                        "round": round_number,
                        "tool": "search_knowledge_base",
                        "query": query,
                        "result_count": len(results),
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id", f"call_{round_number}"),
                        "content": json.dumps(results, ensure_ascii=False),
                    }
                )
        raise ProviderError("达到最大工具调用轮数，仍未得到最终回答。")


def provider_from_environment() -> ChatProvider:
    if os.getenv("HY3_DEMO_MODE", "").lower() in {"1", "true", "yes"}:
        return DemoProvider()
    provider_kind = os.getenv("HY3_PROVIDER", "selfhost").lower()
    defaults = {
        "openrouter": ("https://openrouter.ai/api/v1", "tencent/hy3"),
        "selfhost": ("http://127.0.0.1:8000/v1", "hy3"),
    }
    if provider_kind not in defaults:
        raise ValueError("HY3_PROVIDER must be 'openrouter' or 'selfhost'")
    default_url, default_model = defaults[provider_kind]
    return OpenAICompatibleProvider(
        base_url=os.getenv("HY3_BASE_URL", default_url),
        api_key=os.getenv("HY3_API_KEY", ""),
        model=os.getenv("HY3_MODEL", default_model),
        provider_kind=provider_kind,
        reasoning_effort=os.getenv("HY3_REASONING_EFFORT", "low"),
    )
