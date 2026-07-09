from __future__ import annotations

import json
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .config import ReasoningEffort, load_settings
from .hy3_client import Hy3Client

settings = load_settings()
hy3 = Hy3Client(settings)
mcp = FastMCP(
    "hy3-mcp-server",
    instructions=(
        "Use Tencent Hunyuan Hy3 through an OpenAI-compatible endpoint. "
        "Choose high reasoning effort for complex coding, math, and planning tasks."
    ),
)


def _system_message(text: str | None) -> list[dict[str, str]]:
    if not text:
        return []
    return [{"role": "system", "content": text}]


@mcp.tool()
async def hy3_chat(
    prompt: Annotated[str, Field(description="The user request to send to Hy3.")],
    system_prompt: Annotated[
        str | None,
        Field(description="Optional system instruction for tone, role, or constraints."),
    ] = None,
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        Field(description="Hy3 thinking mode: no_think, low, or high."),
    ] = None,
    temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.9,
    top_p: Annotated[float, Field(gt=0.0, le=1.0)] = 1.0,
    max_tokens: Annotated[int | None, Field(gt=0)] = None,
) -> str:
    """Ask Hy3 a general question through the configured inference endpoint."""
    messages = _system_message(system_prompt) + [{"role": "user", "content": prompt}]
    return await hy3.chat(
        messages,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )


@mcp.tool()
async def hy3_code_review(
    code: Annotated[str, Field(description="Code snippet or diff to review.")],
    language: Annotated[str, Field(description="Programming language or framework name.")] = "unknown",
    focus: Annotated[
        str,
        Field(description="Review focus, such as correctness, security, performance, or API design."),
    ] = "correctness, maintainability, and missing tests",
    severity_threshold: Annotated[
        Literal["low", "medium", "high"],
        Field(description="Minimum severity to include in the review."),
    ] = "medium",
    reasoning_effort: ReasoningEffort = "high",
) -> str:
    """Review code or a patch and return actionable findings first."""
    prompt = f"""Review this {language} code.

Focus: {focus}
Minimum severity: {severity_threshold}

Return findings first. For each finding include severity, location if available, impact, and a concrete fix. If no issues meet the threshold, say so clearly and mention residual risks.

```{language}
{code}
```"""
    return await hy3.chat(
        [
            {
                "role": "system",
                "content": "You are a senior code reviewer. Be concise, specific, and evidence-based.",
            },
            {"role": "user", "content": prompt},
        ],
        reasoning_effort=reasoning_effort,
    )


@mcp.tool()
async def hy3_repo_qa(
    question: Annotated[str, Field(description="Question about a repository, architecture, or files.")],
    context: Annotated[
        str,
        Field(description="Relevant file contents, grep output, logs, or architecture notes."),
    ],
    answer_style: Annotated[
        Literal["brief", "detailed", "step_by_step"],
        Field(description="Preferred answer format."),
    ] = "detailed",
    reasoning_effort: ReasoningEffort = "high",
) -> str:
    """Answer repository questions from supplied context without inventing missing facts."""
    prompt = f"""Answer the repository question using only the supplied context.

Question:
{question}

Answer style: {answer_style}

Context:
{context}

If the context is insufficient, state exactly what is missing and what to inspect next."""
    return await hy3.chat(
        [
            {
                "role": "system",
                "content": "You explain codebases accurately and do not fabricate file contents.",
            },
            {"role": "user", "content": prompt},
        ],
        reasoning_effort=reasoning_effort,
    )


@mcp.tool()
async def hy3_long_context_summarize(
    content: Annotated[str, Field(description="Long text, logs, documentation, or transcript to summarize.")],
    goal: Annotated[
        str,
        Field(description="What the summary should optimize for."),
    ] = "extract decisions, risks, action items, and important details",
    output_format: Annotated[
        Literal["bullets", "executive", "action_items", "technical_notes"],
        Field(description="Summary format."),
    ] = "technical_notes",
    reasoning_effort: ReasoningEffort = "low",
) -> str:
    """Summarize long content while preserving decisions, constraints, and follow-ups."""
    prompt = f"""Summarize the content for this goal: {goal}

Output format: {output_format}

Content:
{content}"""
    return await hy3.chat(
        [
            {
                "role": "system",
                "content": "You compress long context faithfully and preserve actionable details.",
            },
            {"role": "user", "content": prompt},
        ],
        reasoning_effort=reasoning_effort,
    )


@mcp.tool()
async def hy3_health_check() -> str:
    """Check whether the configured Hy3 OpenAI-compatible endpoint is reachable."""
    result = await hy3.health_check()
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def hy3_client_config(
    client: Annotated[
        Literal["codebuddy", "workbuddy", "codex", "trae"],
        Field(description="Target MCP client config snippet."),
    ],
    server_path: Annotated[
        str,
        Field(description="Absolute path to the MCP_Server directory."),
    ],
) -> str:
    """Generate a ready-to-paste MCP client configuration snippet."""
    command = "uv"
    args = ["--directory", server_path, "run", "hy3-mcp-server"]
    env = {
        "HY3_BASE_URL": settings.base_url,
        "HY3_API_KEY": settings.api_key,
        "HY3_MODEL": settings.model,
        "HY3_DEFAULT_REASONING_EFFORT": settings.default_reasoning_effort,
        "HY3_ENABLE_REASONING_EFFORT": str(settings.enable_reasoning_effort).lower(),
    }
    snippet = {"mcpServers": {"hy3": {"command": command, "args": args, "env": env}}}
    heading = {
        "codebuddy": "CodeBuddy / WorkBuddy",
        "workbuddy": "CodeBuddy / WorkBuddy",
        "codex": "Codex",
        "trae": "Trae",
    }[client]
    return f"{heading} MCP configuration:\n\n```json\n{json.dumps(snippet, ensure_ascii=False, indent=2)}\n```"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
