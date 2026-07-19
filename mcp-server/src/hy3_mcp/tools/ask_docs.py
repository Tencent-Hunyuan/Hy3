# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""ask_docs — knowledge-base Q&A grounded in sandboxed local documents."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from ..prompts import docs_prompts
from ..schemas import Citation, DocAnswer
from ..sources.files import Chunk, chunk_text, rank_chunks
from . import ToolDeps, safe_info

__all__ = ["register"]


def register(app: FastMCP, deps: ToolDeps) -> None:
    @app.tool(
        name="ask_docs",
        description=(
            "知识库问答：在沙箱内的本地文档（.md/.txt/.rst）中检索相关片段，"
            "由 Hy3 仅依据片段作答并给出引用；检索不到时明确说明而不编造。 "
            "Knowledge-base Q&A: retrieves relevant chunks from local documents inside the "
            "sandbox and asks Hy3 to answer strictly from them with citations; says so "
            "honestly when nothing relevant is found."
        ),
    )
    async def ask_docs(
        question: Annotated[
            str,
            Field(description="要询问知识库的问题。 The question to ask the knowledge base."),
        ],
        docs_path: Annotated[
            str,
            Field(
                description=(
                    "文档目录（相对沙箱根）；留空则使用 HY3_MCP_DOCS_DIR（默认沙箱根）。 "
                    "Documents directory relative to the sandbox root; empty = "
                    "HY3_MCP_DOCS_DIR (defaults to the sandbox root)."
                )
            ),
        ] = "",
        top_k: Annotated[
            int,
            Field(
                ge=1,
                le=10,
                description="检索片段数（1-10）。 Number of chunks to retrieve (1-10).",
            ),
        ] = 3,
        ctx: Context = None,  # type: ignore[assignment]
    ) -> DocAnswer:
        if not question.strip():
            raise ToolError("question must not be empty")

        base = docs_path.strip() or str(deps.settings.docs_dir)
        files = deps.reader.list_docs(base)
        chunks: list[Chunk] = []
        for f in files:
            try:
                text = deps.reader.read_text(str(f))
            except ToolError:
                continue  # skip oversized/unreadable files, keep scanning
            chunks.extend(chunk_text(text, source=deps.reader.relative(f)))

        ranked = rank_chunks(question, chunks, top_k=top_k)
        await safe_info(
            ctx,
            f"ask_docs: scanned {len(files)} file(s), {len(chunks)} chunk(s), "
            f"{len(ranked)} hit(s)",
        )

        if not ranked:
            return DocAnswer(
                markdown=(
                    "知识库中未找到与问题相关的内容（不做无依据的猜测）。 "
                    f"No relevant content found in the knowledge base for: {question!r}. "
                    f"Searched {len(files)} file(s) under {base!r}. "
                    "Try different keywords or point docs_path at another directory."
                ),
                citations=[],
                searched_files=len(files),
                mode=deps.settings.mode,
            )

        system, user = docs_prompts(question, ranked)
        reply = await deps.client.chat(
            task="docs", system=system, user=user, reasoning_effort="no_think"
        )
        return DocAnswer(
            markdown=reply.text,
            citations=[
                Citation(
                    file=sc.chunk.source,
                    chunk_id=sc.chunk.chunk_id,
                    snippet=sc.chunk.text[:160],
                )
                for sc in ranked
            ],
            searched_files=len(files),
            mode=deps.settings.mode,
        )
