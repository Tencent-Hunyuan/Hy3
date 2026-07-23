"""Hy3 OpenAI-compatible client with retry and mock mode."""

from __future__ import annotations

import json
import time
from typing import Any

from hy3research.config import Config


class MockClient:
    """Returns plausible synthetic responses for offline demo mode."""

    def _plan_response(self, topic: str) -> str:
        return json.dumps({
            "title": f"深度研究报告: {topic}",
            "subtopics": [
                {"query": f"{topic} 现状与发展", "key_question": f"{topic}目前的发展状况如何？"},
                {"query": f"{topic} 技术原理", "key_question": f"{topic}的核心技术原理是什么？"},
                {"query": f"{topic} 应用案例", "key_question": f"{topic}有哪些典型应用案例？"},
                {"query": f"{topic} 未来趋势", "key_question": f"{topic}的未来发展趋势是什么？"},
            ],
            "report_outline": [
                "1. 引言",
                "2. 发展现状",
                "3. 核心技术原理",
                "4. 典型应用案例",
                "5. 未来发展趋势",
                "6. 结论",
            ],
        }, ensure_ascii=False)

    def _synthesize_response(self, key_question: str) -> str:
        return (
            f"## 综合回答\n\n"
            f"关于「{key_question}」，基于已有材料综合分析如下：\n\n"
            f"根据多项研究来源的证据[1][2]，该领域在近年取得了显著进展。"
            f"核心发现包括技术路线的多元化发展和应用场景的持续扩展[3]。\n\n"
            f"**关键要点：**\n\n"
            f"- 第一点：技术成熟度不断提升，多个指标达到实用水平\n"
            f"- 第二点：产业界投入持续增加，形成良性循环\n"
            f"- 第三点：仍存在关键挑战需要突破\n\n"
            f"*引用来源: [1] Source A, [2] Source B, [3] Source C*"
        )

    def _report_response(self, topic: str, outline: list[str] | None = None) -> str:
        if outline is None:
            outline = ["1. 引言", "2. 发展现状", "3. 核心技术", "4. 应用案例", "5. 结论"]
        sections = "\n\n".join(
            f"## {o.split('. ', 1)[-1] if '. ' in o else o}\n\n"
            f"这是关于{o.split('. ', 1)[-1] if '. ' in o else o}的深入分析内容。"
            f"基于对多个来源的综合研究，我们在此部分详细探讨了相关要点和发现。"
            for o in outline
        )
        return (
            f"# {topic}\n\n"
            f"## 摘要\n\n"
            f"本报告深入研究了「{topic}」，通过系统化的信息收集和分析，"
            f"从多个维度呈现了该主题的全貌。研究发现，该领域正处于快速发展阶段，"
            f"值得持续关注和深入研究。\n\n"
            f"{sections}\n\n"
            f"## 结论\n\n"
            f"综合以上分析，「{topic}」是一个具有重要研究价值和实践意义的领域。"
            f"建议持续跟踪最新进展，并结合具体应用场景进行深化研究。\n\n"
            f"---\n\n"
            f"## 参考文献\n\n"
            f"[1] Example Source A. https://example.com/a\n\n"
            f"[2] Example Source B. https://example.com/b\n\n"
            f"[3] Example Source C. https://example.com/c\n"
        )

    def chat(self, messages: list[dict], **kwargs: Any) -> str:
        """Return mock response based on system prompt content."""
        system = ""
        user = ""
        for m in messages:
            if m["role"] == "system":
                system += m.get("content", "")
            elif m["role"] == "user":
                user += m.get("content", "")

        if "研究计划" in system or "plan" in system.lower():
            # Extract just the topic from instructions like "请为以下主题生成研究计划：XXX"
            topic = user.strip() or "指定主题"
            for prefix in ("请为以下主题生成研究计划：", "请为以下主题生成研究计划:"):
                if prefix in topic:
                    topic = topic.split(prefix, 1)[1].strip()
                    break
            return self._plan_response(topic)
        elif "综合" in system or "synthesize" in system.lower():
            return self._synthesize_response(user[:100])
        else:
            topic = user.strip() or "指定主题"
            return self._report_response(topic)


class RealClient:
    """Hy3 API client with retry logic."""

    def __init__(self, api_key: str, base_url: str, max_retries: int = 3):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._max_retries = max_retries
        self._model = Config.HY3_MODEL

    def chat(self, messages: list[dict], max_tokens: int = 0, **kwargs: Any) -> str:
        tokens = max_tokens or Config.HY3_MAX_TOKENS
        last_error = None
        for attempt in range(self._max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=tokens,
                    temperature=kwargs.get("temperature", 0.3),
                )
                content = response.choices[0].message.content
                if content and len(content.strip()) > 0:
                    return content.strip()
                # Empty content — might be reasoning model, check reasoning_content
                if hasattr(response.choices[0].message, "reasoning_content"):
                    rc = response.choices[0].message.reasoning_content
                    if rc:
                        return str(rc).strip()
                last_error = Exception("Hy3 returned empty response")
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)  # 1s, 2s, 4s
        raise RuntimeError(
            f"Hy3 API call failed after {self._max_retries} attempts: {last_error}"
        )


def get_client(mock: bool = False) -> MockClient | RealClient:
    """Factory: return MockClient or RealClient based on config/mode."""
    if mock or Config.is_mock:
        return MockClient()
    return RealClient(
        api_key=Config.HY3_API_KEY,
        base_url=Config.HY3_BASE_URL,
    )


def call_hy3(
    messages: list[dict],
    max_tokens: int = 0,
    temperature: float = 0.3,
    mock: bool = False,
) -> str:
    """Convenience: get client and call chat. Returns response text."""
    client = get_client(mock=mock)
    return client.chat(messages, max_tokens=max_tokens, temperature=temperature)
