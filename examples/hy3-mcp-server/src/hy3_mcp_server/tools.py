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


def review_diff(diff: str, focus: str = "correctness and regressions", client: Hy3Client | None = None) -> dict[str, Any]:
    """Review a source diff with Hy3 and return prioritized findings."""
    hy3 = client or Hy3Client()
    prompt = (
        f"Review focus: {focus}\n\n"
        "Diff:\n"
        "```diff\n"
        f"{diff.strip()}\n"
        "```\n\n"
        "Respond with: Findings, Suggested patch direction, Missing tests."
    )
    return {
        "tool": "hy3_code_review",
        "focus": focus,
        "result": hy3.chat(CODE_REVIEW_SYSTEM, prompt, reasoning_effort="high"),
    }


def answer_question(
    question: str,
    documents: list[dict[str, str]],
    client: Hy3Client | None = None,
) -> dict[str, Any]:
    """Answer a question from provided documents with source citations."""
    hy3 = client or Hy3Client()
    normalized_docs = normalize_documents(documents)
    prompt = (
        f"Question: {question.strip()}\n\n"
        "Documents:\n"
        f"{json.dumps(normalized_docs, ensure_ascii=True, indent=2)}\n\n"
        "Return: Answer, Citations, Confidence, Missing evidence."
    )
    return {
        "tool": "hy3_document_qa",
        "document_count": len(normalized_docs),
        "result": hy3.chat(DOCUMENT_QA_SYSTEM, prompt, reasoning_effort="high"),
    }


def inspect_data(
    data: str,
    question: str = "What should I know about this dataset?",
    client: Hy3Client | None = None,
) -> dict[str, Any]:
    """Inspect CSV or JSON data and ask Hy3 for analytical takeaways."""
    hy3 = client or Hy3Client()
    profile = profile_tabular_data(data)
    prompt = (
        f"Analysis question: {question.strip()}\n\n"
        "Data profile:\n"
        f"{json.dumps(profile, ensure_ascii=True, indent=2)}\n\n"
        "Return: Key takeaways, Caveats, Recommended chart or query, Next action."
    )
    return {
        "tool": "hy3_data_insight",
        "profile": profile,
        "result": hy3.chat(DATA_INSIGHT_SYSTEM, prompt, reasoning_effort="high"),
    }


def normalize_documents(documents: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = []
    for index, doc in enumerate(documents, start=1):
        doc_id = str(doc.get("id") or f"doc-{index}")
        title = str(doc.get("title") or doc_id)
        text = str(doc.get("text") or "")
        normalized.append({"id": doc_id, "title": title, "text": text[:6000]})
    return normalized


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
