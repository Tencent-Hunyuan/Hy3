"""FastMCP stdio server exposing Hy3-powered data-analysis tools."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import Settings
from .dataset import profile_dataset_file
from .hy3 import ReasoningEffort, call_hy3

mcp = FastMCP(
    "Hy3 Data Analyst",
    instructions=(
        "Inspect local CSV/JSON datasets, ask evidence-grounded questions, and generate "
        "Markdown reports with Hy3. Files are restricted to HY3_DATA_DIR."
    ),
)


@mcp.tool()
def profile_dataset(
    file_path: str,
    max_rows: int = 10_000,
    sample_rows: int = 5,
) -> dict[str, Any]:
    """Profile a CSV, JSON, JSONL, or NDJSON dataset without calling an LLM.

    Args:
        file_path: Relative path inside HY3_DATA_DIR (absolute paths inside it are also accepted).
        max_rows: Maximum rows to scan, from 1 to 100000.
        sample_rows: Number of example rows to return, from 0 to 20.
    """
    return profile_dataset_file(file_path, max_rows=max_rows, sample_rows=sample_rows)


@mcp.tool()
async def analyze_dataset(
    file_path: str,
    question: str,
    reasoning_effort: ReasoningEffort = "high",
    sample_rows: int = 10,
) -> dict[str, Any]:
    """Use Hy3 to answer a question from a bounded statistical profile and row sample.

    Args:
        file_path: Relative path inside HY3_DATA_DIR.
        question: Specific analytical question to answer from this dataset.
        reasoning_effort: Hy3 reasoning depth: no_think, low, medium, or high.
        sample_rows: Number of rows sent to Hy3, from 0 to 20.
    """
    if not question.strip():
        raise ValueError("question must not be empty")
    profile = profile_dataset_file(file_path, sample_rows=sample_rows)
    analysis = await call_hy3(
        [
            {
                "role": "system",
                "content": (
                    "You are a rigorous data analyst. Use only the supplied profile and samples. "
                    "Separate observed facts from hypotheses, mention truncation, and never invent "
                    "rows, statistics, or causal claims."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question.strip()}\n\n"
                    f"Dataset profile:\n{_profile_json(profile)}"
                ),
            },
        ],
        reasoning_effort=reasoning_effort,
    )
    return {
        "file": profile["source"]["file"],
        "question": question.strip(),
        "rows_scanned": profile["rows_scanned"],
        "truncated": profile["truncated"],
        "analysis": analysis,
    }


@mcp.tool()
async def generate_data_report(
    file_path: str,
    objective: str,
    reasoning_effort: ReasoningEffort = "high",
    sample_rows: int = 10,
) -> str:
    """Ask Hy3 to create an evidence-grounded Markdown report for a local dataset.

    Args:
        file_path: Relative path inside HY3_DATA_DIR.
        objective: Audience, decision, or business objective the report should address.
        reasoning_effort: Hy3 reasoning depth: no_think, low, medium, or high.
        sample_rows: Number of rows sent to Hy3, from 0 to 20.
    """
    if not objective.strip():
        raise ValueError("objective must not be empty")
    profile = profile_dataset_file(file_path, sample_rows=sample_rows)
    return await call_hy3(
        [
            {
                "role": "system",
                "content": (
                    "You write concise Markdown data reports. Ground every quantitative statement "
                    "in the supplied profile. State limitations prominently, especially when the "
                    "scan is truncated. Do not reveal chain-of-thought; provide conclusions and "
                    "brief supporting evidence only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Report objective: {objective.strip()}\n\n"
                    f"Dataset profile:\n{_profile_json(profile)}\n\n"
                    "Return Markdown with: title, executive summary, data quality, key findings, "
                    "recommended actions, and limitations."
                ),
            },
        ],
        reasoning_effort=reasoning_effort,
    )


def _profile_json(profile: dict[str, Any]) -> str:
    return json.dumps(profile, ensure_ascii=False, indent=2)


def main() -> None:
    """Run the local stdio MCP transport."""
    Settings.from_env()  # Fail fast on malformed environment values.
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
