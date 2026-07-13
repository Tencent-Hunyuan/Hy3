"""Build portable Markdown and JSON outputs from an investigation result."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .agent import AgentResult


def result_is_complete(result: AgentResult, citation_result: Mapping[str, Any]) -> bool:
    """Require both verified evidence and a non-truncated agent run."""
    return (
        bool(citation_result.get("valid"))
        and not result.budget_exhausted
        and result.finish_reason == "stop"
    )


def result_summary(
    result: AgentResult,
    citation_result: Mapping[str, Any],
    *,
    model: str,
    repository: str,
) -> dict[str, Any]:
    """Return a bounded machine-readable result without raw prompts or file contents."""
    return {
        "success": result_is_complete(result, citation_result),
        "report": result.content,
        "repository": repository,
        "model": model,
        "statistics": {
            "rounds": result.rounds,
            "tool_calls": result.tool_calls,
            "files_read": result.files_read,
            "context_chars": result.context_chars,
            "usage": dict(result.usage),
            "finish_reason": result.finish_reason,
            "budget_exhausted": result.budget_exhausted,
        },
        "citation_validation": dict(citation_result),
    }


def build_markdown_report(
    result: AgentResult,
    citation_result: Mapping[str, Any],
    *,
    model: str,
    repository: str,
) -> str:
    """Wrap the model report with reproducible run and validation metadata."""
    validation = "passed" if citation_result.get("valid") else "failed"
    run_status = "complete" if result_is_complete(result, citation_result) else "incomplete"
    citations = citation_result.get("citations") or []
    usage = result.usage
    lines = [
        "# Hy3 Repo Scout Report",
        "",
        result.content.strip(),
        "",
        "---",
        "",
        "## Run Metadata",
        "",
        "| Field | Value |",
        "|---|---:|",
        f"| Repository | `{repository}` |",
        f"| Model | `{model}` |",
        f"| Model rounds | {result.rounds} |",
        f"| Tool calls | {result.tool_calls} |",
        f"| Files read | {result.files_read} |",
        f"| Repository context | {result.context_chars} chars |",
        f"| Total tokens | {usage.get('total_tokens', 0)} |",
        f"| Run status | {run_status} |",
        f"| Budget exhausted | {'yes' if result.budget_exhausted else 'no'} |",
        "",
        "## Citation Validation",
        "",
        f"Status: **{validation}**. Verified citations: **{len(citations)}**.",
    ]
    error = citation_result.get("error")
    if error:
        message = error.get("message", "unknown validation error")
        lines.extend(["", f"Validation error: `{message}`"])
    return "\n".join(lines).rstrip() + "\n"


def write_text(path: str | Path, content: str) -> Path:
    """Write UTF-8 output, creating only the explicitly requested parent directory."""
    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination


def to_json(summary: Mapping[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
