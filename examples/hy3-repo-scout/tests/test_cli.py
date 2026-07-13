import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase

from rich.console import Console

from hy3_repo_scout.agent import AgentResult
from hy3_repo_scout.cli import (
    TraceRenderer,
    build_parser,
    load_settings,
    render_result,
    resolve_question,
)
from hy3_repo_scout.config import Settings
from hy3_repo_scout.prompts import IMPACT_DEMO_PROMPT


class CliTests(TestCase):
    def setUp(self) -> None:
        self.parser = build_parser()

    def test_positional_question_and_demo_resolution(self) -> None:
        question_args = self.parser.parse_args(["what", "changed?"])
        demo_args = self.parser.parse_args(["--demo", "impact"])

        self.assertEqual(resolve_question(question_args, self.parser), "what changed?")
        self.assertEqual(resolve_question(demo_args, self.parser), IMPACT_DEMO_PROMPT)

    def test_empty_question_enters_repl(self) -> None:
        args = self.parser.parse_args([])
        self.assertIsNone(resolve_question(args, self.parser))

    def test_settings_overrides_preserve_unset_values(self) -> None:
        args = self.parser.parse_args(
            ["--model", "custom-hy3", "--reasoning-effort", "low", "--max-rounds", "4"]
        )

        updated = load_settings(args, {"HY3_API_KEY": "test-key"})

        self.assertEqual(updated.model, "custom-hy3")
        self.assertEqual(updated.reasoning_effort, "low")
        self.assertEqual(updated.max_rounds, 4)
        self.assertEqual(updated.base_url, Settings(api_key="test-key").base_url)

    def test_base_url_override_is_applied_before_empty_key_validation(self) -> None:
        args = self.parser.parse_args(
            ["--base-url", "https://hy3-gateway.example.com/v1", "--model", "hy3"]
        )

        settings = load_settings(args, {"HY3_API_KEY": "EMPTY"})

        self.assertEqual(settings.base_url, "https://hy3-gateway.example.com/v1")
        self.assertEqual(settings.api_key, "EMPTY")

    def test_trace_hides_unsafe_paths_and_raw_errors(self) -> None:
        output = io.StringIO()
        renderer = TraceRenderer(Console(file=output, color_system=None))

        renderer(
            {
                "type": "tool_start",
                "name": "read_file",
                "arguments": {"path": "C:/Users/alice/private.py"},
            }
        )
        renderer(
            {
                "type": "tool_end",
                "name": "read_file",
                "error": "/Users/alice/private.py could not be opened",
            }
        )

        rendered = output.getvalue()
        self.assertIn("<blocked>", rendered)
        self.assertIn("tool call failed", rendered)
        self.assertNotIn("C:/Users", rendered)
        self.assertNotIn("/Users/alice", rendered)

    def test_json_output_is_not_wrapped_by_terminal_width(self) -> None:
        result = AgentResult(
            content="Fact: " + "evidence " * 30 + "[README.md:L1-L1]",
            rounds=1,
            tool_calls=1,
            files_read=1,
            context_chars=100,
            usage={"total_tokens": 10},
            finish_reason="stop",
        )
        tools = type("Tools", (), {"root": Path("Hy3")})()
        output = io.StringIO()

        with redirect_stdout(output):
            valid = render_result(
                result,
                {"valid": True, "citations": [], "error": None},
                settings=Settings(api_key="test"),
                tools=tools,
                console=Console(width=40),
                json_output=True,
                output=None,
            )

        self.assertTrue(valid)
        self.assertEqual(json.loads(output.getvalue())["statistics"]["tool_calls"], 1)

    def test_untrusted_controls_are_removed_from_traces_terminal_and_report(self) -> None:
        renderer_output = io.StringIO()
        renderer = TraceRenderer(Console(file=renderer_output, color_system=None))
        renderer(
            {
                "type": "tool_start",
                "name": "read\nspoof\x1b]52;c;payload\x07",
                "arguments": {},
            }
        )
        renderer(
            {
                "type": "retry",
                "error": "remote\nspoof\x1b[2J\x9c failure",
                "delay": 0.5,
            }
        )
        from contextlib import redirect_stderr

        from hy3_repo_scout.cli import _emit_error

        error_output = io.StringIO()
        with redirect_stderr(error_output):
            _emit_error(
                RuntimeError("remote\x1b]52;c;payload\x07"),
                "api\x1b[2J",
                json_output=False,
            )

        result = AgentResult(
            content="Fact\x1b]52;c;payload\x07\b\r\x9c: safe [README.md:L1-L1]",
            rounds=1,
            tool_calls=0,
            files_read=1,
            context_chars=10,
            usage={"total_tokens": 5},
            finish_reason="stop",
        )
        tools = type("Tools", (), {"root": Path("Hy3")})()
        terminal = io.StringIO()
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.md"
            valid = render_result(
                result,
                {"valid": True, "citations": [], "error": None},
                settings=Settings(api_key="test"),
                tools=tools,
                console=Console(file=terminal, color_system=None),
                json_output=False,
                output=str(report_path),
            )
            report = report_path.read_text(encoding="utf-8")

        self.assertTrue(valid)
        self.assertIn("readspoof", renderer_output.getvalue())
        self.assertIn("remotespoof", renderer_output.getvalue())
        for rendered in (
            renderer_output.getvalue(),
            error_output.getvalue(),
            terminal.getvalue(),
            report,
        ):
            self.assertIsNone(
                __import__("re").search(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", rendered)
            )
        self.assertIn("payload", report)
