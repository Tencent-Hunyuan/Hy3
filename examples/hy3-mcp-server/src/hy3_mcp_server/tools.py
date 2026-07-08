"""Tool implementations shared by the MCP server and tests."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from .hy3_client import Hy3Client


CODE_REVIEW_SYSTEM = (
    "You are Hy3 acting as a senior code reviewer. "
    "Prioritize correctness bugs, security risks, regressions, and missing tests. "
    "Return concise Markdown with severity labels and concrete suggestions."
)

DOCUMENT_QA_SYSTEM = (
    "You are Hy3 acting as a grounded document QA assistant. "
    "Answer only from the supplied documents, cite document ids, and say when evidence is missing."
)

DATA_INSIGHT_SYSTEM = (
    "You are Hy3 acting as a data analyst. "
    "Use the schema and sample rows to explain likely patterns, risks, and next analyses. "
    "Do not invent rows or metrics that are not present."
)

AGENT_PLAN_SYSTEM = (
    "You are Hy3 acting as an MCP task planner. "
    "Turn the user's goal into a compact plan that an AI client can execute with tools. "
    "Call out needed context, suggested MCP tools, risks, and a clear done condition."
)


def review_diff(
    diff: str,
    focus: str = "correctness and regressions",
    thinking_mode: str = "deep",
    client: Hy3Client | None = None,
) -> dict[str, Any]:
    """Review a source diff with Hy3 and return prioritized findings."""
    hy3 = client or Hy3Client()
    prompt = (
        f"Review focus: {focus}\n\n"
        f"Hy3 thinking mode: {thinking_mode}\n\n"
        "Diff:\n"
        "```diff\n"
        f"{diff.strip()}\n"
        "```\n\n"
        "Respond with: Findings, Suggested patch direction, Missing tests."
    )
    return {
        "tool": "hy3_code_review",
        "focus": focus,
        "thinking_mode": normalize_thinking_mode(thinking_mode),
        "result": hy3.chat(CODE_REVIEW_SYSTEM, prompt, reasoning_effort=reasoning_effort_for(thinking_mode)),
    }


def answer_question(
    question: str,
    documents: list[dict[str, str]],
    thinking_mode: str = "deep",
    client: Hy3Client | None = None,
) -> dict[str, Any]:
    """Answer a question from provided documents with source citations."""
    hy3 = client or Hy3Client()
    normalized_docs = normalize_documents(documents)
    prompt = (
        f"Question: {question.strip()}\n\n"
        f"Hy3 thinking mode: {thinking_mode}\n\n"
        "Documents:\n"
        f"{json.dumps(normalized_docs, ensure_ascii=True, indent=2)}\n\n"
        "Return: Answer, Citations, Confidence, Missing evidence."
    )
    return {
        "tool": "hy3_document_qa",
        "document_count": len(normalized_docs),
        "thinking_mode": normalize_thinking_mode(thinking_mode),
        "result": hy3.chat(DOCUMENT_QA_SYSTEM, prompt, reasoning_effort=reasoning_effort_for(thinking_mode)),
    }


def inspect_data(
    data: str,
    question: str = "What should I know about this dataset?",
    thinking_mode: str = "deep",
    client: Hy3Client | None = None,
) -> dict[str, Any]:
    """Inspect CSV or JSON data and ask Hy3 for analytical takeaways."""
    hy3 = client or Hy3Client()
    profile = profile_tabular_data(data)
    prompt = (
        f"Analysis question: {question.strip()}\n\n"
        f"Hy3 thinking mode: {thinking_mode}\n\n"
        "Data profile:\n"
        f"{json.dumps(profile, ensure_ascii=True, indent=2)}\n\n"
        "Return: Key takeaways, Caveats, Recommended chart or query, Next action."
    )
    return {
        "tool": "hy3_data_insight",
        "thinking_mode": normalize_thinking_mode(thinking_mode),
        "profile": profile,
        "result": hy3.chat(DATA_INSIGHT_SYSTEM, prompt, reasoning_effort=reasoning_effort_for(thinking_mode)),
    }


def build_agent_plan(
    goal: str,
    available_context: str = "",
    client: Hy3Client | None = None,
) -> dict[str, Any]:
    """Use Hy3 to turn a complex goal into an MCP-client execution plan."""
    hy3 = client or Hy3Client()
    prompt = (
        f"Goal: {goal.strip()}\n\n"
        f"Available context: {available_context.strip() or 'none'}\n\n"
        "Return Markdown sections: Intent, Context needed, Suggested tool sequence, "
        "Quality checks, Done condition."
    )
    return {
        "tool": "hy3_agent_plan",
        "thinking_mode": "deep",
        "result": hy3.chat(AGENT_PLAN_SYSTEM, prompt, reasoning_effort="high"),
    }


def normalize_documents(documents: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = []
    for index, doc in enumerate(documents, start=1):
        doc_id = str(doc.get("id") or f"doc-{index}")
        title = str(doc.get("title") or doc_id)
        text = str(doc.get("text") or "")
        normalized.append({"id": doc_id, "title": title, "text": text[:6000]})
    return normalized


def normalize_thinking_mode(mode: str) -> str:
    value = mode.strip().lower()
    if value in {"fast", "no_think", "quick"}:
        return "fast"
    if value in {"deep", "high", "slow"}:
        return "deep"
    return "deep"


def reasoning_effort_for(mode: str) -> str:
    return "no_think" if normalize_thinking_mode(mode) == "fast" else "high"


def profile_tabular_data(data: str) -> dict[str, Any]:
    text = data.strip()
    if not text:
        return {"format": "empty", "row_count": 0, "columns": [], "sample_rows": []}

    if text[0] in "[{":
        parsed = json.loads(text)
        rows = parsed if isinstance(parsed, list) else [parsed]
        if not all(isinstance(row, dict) for row in rows):
            rows = [{"value": row} for row in rows]
        return profile_rows("json", rows)

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return profile_rows("csv", rows)


def profile_rows(data_format: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({str(key) for row in rows for key in row.keys()})
    null_counts = {
        column: sum(1 for row in rows if row.get(column) in {None, ""})
        for column in columns
    }
    return {
        "format": data_format,
        "row_count": len(rows),
        "columns": columns,
        "null_counts": null_counts,
        "sample_rows": rows[:8],
    }
