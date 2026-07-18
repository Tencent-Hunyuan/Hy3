"""
RAG engine - retrieval + Hy3 generation with streaming and source citations.
"""
import logging
from typing import List, Dict, AsyncIterator, Optional

import config
from vector_store import VectorStore
from hy3_client import get_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个基于 Hy3 模型的多语言检索增强问答助手（Hy3 RAG）。
你会收到一组从用户文档中检索到的上下文片段，以及用户的问题。
请严格依据提供的上下文回答，并在答案中用 [文件名] 的形式标注引用来源。
如果上下文不包含答案，请明确告知用户“文档中没有相关信息”，不要编造。
回答应准确、简洁，保留原文的关键数据与术语。"""


class RAGEngine:
    def __init__(self, vector_store: VectorStore):
        self.vs = vector_store
        self.client = get_client()

    async def answer_stream(
        self,
        query: str,
        top_k: int = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        source_filters: Optional[List[str]] = None,
    ) -> AsyncIterator[dict]:
        top_k = top_k or config.TOP_K_CHUNKS

        # 1) Retrieve relevant chunks
        contexts = self.vs.search(
            query, top_k=top_k, source_filters=source_filters
        )
        source_names = [c["doc_name"] for c in contexts if c.get("doc_name")]
        yield {"type": "context", "sources": source_names}

        # 2) Build the message list
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        for turn in conversation_history or []:
            messages.append(turn)

        context_text = "\n\n".join(
            f"[Source: {c['doc_name']}]\n{c['text']}"
            for c in contexts
            if c.get("doc_name")
        )
        if context_text:
            user_content = (
                f"以下是检索到的文档上下文：\n\n{context_text}\n\n"
                f"用户问题：{query}"
            )
        else:
            user_content = query
        messages.append({"role": "user", "content": user_content})

        # 3) Stream the answer
        answer_parts: List[str] = []
        try:
            for delta in self.client.chat_stream(messages):
                answer_parts.append(delta)
                yield {"type": "token", "content": delta}
        except Exception as e:
            logger.error("Generation error: %s", e)
            yield {"type": "error", "message": str(e)}
            return

        full_answer = "".join(answer_parts)
        yield {
            "type": "done",
            "answer": full_answer,
            "sources": contexts,
        }
