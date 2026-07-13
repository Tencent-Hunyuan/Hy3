import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from hy3_repo_scout.agent import AgentResult
from hy3_repo_scout.report import (
    build_markdown_report,
    result_is_complete,
    result_summary,
    to_json,
    write_text,
)


def sample_result() -> AgentResult:
    return AgentResult(
        content="## Executive Summary\nFact: found [README.md:L1-L1]",
        rounds=2,
        tool_calls=3,
        files_read=1,
        context_chars=400,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        finish_reason="stop",
    )


class ReportTests(TestCase):
    def test_summary_excludes_messages_and_raw_tool_results(self) -> None:
        summary = result_summary(
            sample_result(),
            {"valid": True, "citations": [{"path": "README.md"}], "error": None},
            model="tencent/hy3:free",
            repository="Hy3",
        )

        encoded = to_json(summary)
        self.assertEqual(json.loads(encoded)["statistics"]["tool_calls"], 3)
        self.assertNotIn("messages", encoded)
        self.assertNotIn("trace", encoded)

    def test_markdown_includes_report_telemetry_and_validation(self) -> None:
        document = build_markdown_report(
            sample_result(),
            {"valid": True, "citations": [{"path": "README.md"}], "error": None},
            model="tencent/hy3:free",
            repository="Hy3",
        )

        self.assertIn("# Hy3 Repo Scout Report", document)
        self.assertIn("Fact: found", document)
        self.assertIn("| Tool calls | 3 |", document)
        self.assertIn("| Run status | complete |", document)
        self.assertIn("Status: **passed**", document)

    def test_truncated_or_budget_exhausted_results_are_incomplete(self) -> None:
        validation = {"valid": True, "citations": [], "error": None}
        length_result = sample_result()
        object.__setattr__(length_result, "finish_reason", "length")
        budget_result = sample_result()
        object.__setattr__(budget_result, "budget_exhausted", True)

        self.assertFalse(result_is_complete(length_result, validation))
        self.assertFalse(result_is_complete(budget_result, validation))

    def test_missing_finish_reason_is_incomplete(self) -> None:
        result = sample_result()
        object.__setattr__(result, "finish_reason", None)

        self.assertFalse(
            result_is_complete(result, {"valid": True, "citations": [], "error": None})
        )

    def test_write_text_creates_requested_parent(self) -> None:
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "reports" / "result.md"
            written = write_text(destination, "report\n")

            self.assertEqual(written, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), "report\n")
