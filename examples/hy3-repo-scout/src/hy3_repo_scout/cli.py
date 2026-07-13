"""Rich command-line interface for Hy3 Repo Scout."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .agent import AgentResult, RepoScoutAgent
from .citations import citation_validation_result, evidence_lines_from_trace
from .config import ConfigError, Settings
from .prompts import IMPACT_DEMO_PROMPT, PIPELINE_DEMO_PROMPT
from .report import (
    build_markdown_report,
    result_is_complete,
    result_summary,
    to_json,
    write_text,
)
from .tools import RepoTools, ToolError

DEMO_PROMPTS = {
    "impact": IMPACT_DEMO_PROMPT,
    "pipeline": PIPELINE_DEMO_PROMPT,
}

_UNTRUSTED_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_SINGLE_LINE_CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _strip_untrusted_controls(value: str) -> str:
    """Remove terminal controls while preserving report newlines and tabs."""

    return _UNTRUSTED_CONTROL_PATTERN.sub("", value)


def _strip_untrusted_single_line(value: str) -> str:
    """Remove every terminal control from fields that must stay on one line."""

    return _SINGLE_LINE_CONTROL_PATTERN.sub("", value)


class TraceRenderer:
    """Render compact, stable progress lines suitable for terminals and recordings."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def __call__(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "model_request":
            self.console.print(
                f"[cyan]Round {event['round']}[/cyan]  Hy3 is reviewing the evidence..."
            )
        elif event_type == "tool_start":
            arguments = self._short_arguments(event.get("arguments", {}))
            name = escape(_strip_untrusted_single_line(str(event.get("name", "unknown"))))
            self.console.print(f"  [blue]→[/blue] {name} {arguments}")
        elif event_type == "tool_end":
            name = escape(_strip_untrusted_single_line(str(event.get("name", "unknown"))))
            if event.get("error"):
                self.console.print(f"  [red]×[/red] {name}: tool call failed")
            else:
                suffix = " (truncated)" if event.get("truncated") else ""
                self.console.print(
                    f"  [green]✓[/green] {name} "
                    f"+{event.get('context_chars', 0)} chars{suffix}"
                )
        elif event_type == "retry":
            error = escape(
                _strip_untrusted_single_line(str(event.get("error", "transient error")))
            )
            self.console.print(
                f"  [yellow]retry[/yellow] {error} in {event['delay']:.1f}s"
            )
        elif event_type == "report_repair":
            self.console.print(
                "  [yellow]citation check requested one report repair round[/yellow]"
            )

    @staticmethod
    def _short_arguments(arguments: Any) -> str:
        if not isinstance(arguments, dict):
            return ""
        parts = []
        if "query" in arguments:
            parts.append(f"query=<{len(str(arguments['query']))} chars>")
        for name in ("path", "pattern", "base"):
            if name not in arguments:
                continue
            value = str(arguments[name])
            pure = PurePosixPath(value)
            unsafe = (
                pure.is_absolute()
                or (len(value) >= 3 and value[0].isalpha() and value[1:3] in {":/", ":\\"})
                or ".." in pure.parts
                or "\\" in value
                or _SINGLE_LINE_CONTROL_PATTERN.search(value) is not None
            )
            rendered = "<blocked>" if unsafe else repr(value[:52])
            parts.append(f"{name}={escape(rendered)}")
        for name in ("start_line", "end_line"):
            if name in arguments and isinstance(arguments[name], int):
                parts.append(f"{name}={arguments[name]}")
        return " ".join(parts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hy3-repo-scout",
        description="Investigate a repository with Hy3 and verified file:line evidence.",
    )
    parser.add_argument("question", nargs="*", help="Investigation question; omit for REPL mode")
    parser.add_argument("--repo", default=".", help="Repository root to inspect (default: .)")
    parser.add_argument("--demo", choices=sorted(DEMO_PROMPTS), help="Run a built-in demo")
    parser.add_argument("--output", help="Write the report to a Markdown file")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of rich output")
    parser.add_argument("--model", help="Override HY3_MODEL")
    parser.add_argument("--base-url", help="Override HY3_BASE_URL")
    parser.add_argument(
        "--reasoning-effort",
        choices=("no_think", "low", "high"),
        help="Override HY3_REASONING_EFFORT",
    )
    parser.add_argument("--max-rounds", type=int, help="Override the model-round budget")
    parser.add_argument("--max-tool-calls", type=int, help="Override the tool-call budget")
    parser.add_argument("--max-context-chars", type=int, help="Override repository context budget")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def resolve_question(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str | None:
    if args.demo and args.question:
        parser.error("a positional question cannot be combined with --demo")
    if args.demo:
        return DEMO_PROMPTS[args.demo]
    question = " ".join(args.question).strip()
    return question or None


def load_settings(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Merge CLI overrides into raw environment values before validating once."""
    values = dict(os.environ if environ is None else environ)
    overrides = {
        "HY3_MODEL": args.model,
        "HY3_BASE_URL": args.base_url,
        "HY3_REASONING_EFFORT": args.reasoning_effort,
        "HY3_MAX_ROUNDS": args.max_rounds,
        "HY3_MAX_TOOL_CALLS": args.max_tool_calls,
        "HY3_MAX_CONTEXT_CHARS": args.max_context_chars,
    }
    values.update(
        {name: str(value) for name, value in overrides.items() if value is not None}
    )
    return Settings.from_env(values)


def investigate(
    question: str,
    *,
    settings: Settings,
    tools: RepoTools,
    console: Console,
    json_output: bool = False,
) -> tuple[AgentResult, dict[str, Any]]:
    callback = None if json_output else TraceRenderer(console)

    def validate_report(content: str, trace: tuple[Any, ...]) -> dict[str, Any]:
        return citation_validation_result(
            content,
            tools,
            require=True,
            evidence_lines=evidence_lines_from_trace(trace),
        )

    agent = RepoScoutAgent(
        settings,
        tools,
        on_event=callback,
        report_validator=validate_report,
    )
    result = agent.run(question)
    validation = agent.last_report_validation
    if validation is None:
        validation = validate_report(result.content, result.trace)
    else:
        validation = dict(validation)
    return result, validation


def render_result(
    result: AgentResult,
    validation: dict[str, Any],
    *,
    settings: Settings,
    tools: RepoTools,
    console: Console,
    json_output: bool,
    output: str | None,
) -> bool:
    safe_result = replace(result, content=_strip_untrusted_controls(result.content))
    repository = _strip_untrusted_single_line(tools.root.name)
    model = _strip_untrusted_single_line(settings.model)
    summary = result_summary(
        safe_result,
        validation,
        model=model,
        repository=repository,
    )
    document = build_markdown_report(
        safe_result,
        validation,
        model=model,
        repository=repository,
    )
    if output:
        destination = write_text(output, document)
        summary["output"] = str(destination)

    if json_output:
        sys.stdout.write(to_json(summary) + "\n")
    else:
        console.print()
        console.print(Markdown(safe_result.content))
        console.print()
        console.print(_statistics_table(safe_result, validation))
        if output:
            rendered_destination = escape(_strip_untrusted_single_line(str(destination)))
            console.print(f"[dim]Report written to {rendered_destination}[/dim]")
    return result_is_complete(safe_result, validation)


def _statistics_table(result: AgentResult, validation: dict[str, Any]) -> Table:
    table = Table(title="Investigation summary", show_header=False, box=None)
    table.add_column(style="dim")
    table.add_column(justify="right")
    table.add_row("Model rounds", str(result.rounds))
    table.add_row("Tool calls", str(result.tool_calls))
    table.add_row("Files read", str(result.files_read))
    table.add_row("Context", f"{result.context_chars:,} chars")
    table.add_row("Tokens", f"{result.usage.get('total_tokens', 0):,}")
    citations = len(validation.get("citations") or [])
    status = f"verified ({citations})" if validation.get("valid") else "failed"
    table.add_row("Citations", status)
    table.add_row("Run", "complete" if result_is_complete(result, validation) else "incomplete")
    return table


def _run_repl(
    *,
    settings: Settings,
    tools: RepoTools,
    console: Console,
) -> int:
    console.print(
        Panel.fit(
            "Ask a repository question. Type [bold]/exit[/bold] to quit or "
            "[bold]/demos[/bold] to list demos.",
            title="Hy3 Repo Scout",
            border_style="cyan",
        )
    )
    while True:
        try:
            question = console.input("\n[bold cyan]scout>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return 0
        if not question:
            continue
        if question in {"/exit", "/quit"}:
            return 0
        if question == "/demos":
            console.print("[bold]impact[/bold] - reasoning mode change impact")
            console.print("[bold]pipeline[/bold] - LoRA pipeline consistency audit")
            continue
        if question.startswith("/demo "):
            demo = question.removeprefix("/demo ").strip()
            if demo not in DEMO_PROMPTS:
                console.print("[red]Unknown demo. Use impact or pipeline.[/red]")
                continue
            question = DEMO_PROMPTS[demo]
        run_tools = RepoTools(
            tools.root,
            max_file_bytes=tools.max_file_bytes,
            max_read_lines=tools.max_read_lines,
        )
        try:
            result, validation = investigate(
                question,
                settings=settings,
                tools=run_tools,
                console=console,
            )
            render_result(
                result,
                validation,
                settings=settings,
                tools=run_tools,
                console=console,
                json_output=False,
                output=None,
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Current investigation cancelled.[/yellow]")
        except Exception as exc:
            _emit_error(exc, "investigation", json_output=False)


def _emit_error(exc: Exception, category: str, *, json_output: bool) -> None:
    if json_output:
        payload = {
            "error": {
                "category": category,
                "type": type(exc).__name__,
                "message": str(exc),
            }
        }
        sys.stdout.write(to_json(payload) + "\n")
        return
    error_console = Console(stderr=True)
    safe_category = escape(_strip_untrusted_single_line(category.title()))
    safe_type = escape(_strip_untrusted_single_line(type(exc).__name__))
    safe_message = escape(_strip_untrusted_single_line(str(exc)))
    error_console.print(
        f"[red]{safe_category} error:[/red] {safe_type}: {safe_message}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    question = resolve_question(args, parser)
    console = Console(stderr=False)
    if args.json and question is None:
        parser.error("--json requires a positional question or --demo")
    if args.output and question is None:
        parser.error("--output requires a positional question or --demo")
    try:
        settings = load_settings(args)
        tools = RepoTools(Path(args.repo))
        if question is None:
            return _run_repl(settings=settings, tools=tools, console=console)
        result, validation = investigate(
            question,
            settings=settings,
            tools=tools,
            console=console,
            json_output=args.json,
        )
        valid = render_result(
            result,
            validation,
            settings=settings,
            tools=tools,
            console=console,
            json_output=args.json,
            output=args.output,
        )
        return 0 if valid else 3
    except (ConfigError, ToolError) as exc:
        _emit_error(exc, "configuration", json_output=args.json)
        return 2
    except KeyboardInterrupt:
        if args.json:
            _emit_error(KeyboardInterrupt("interrupted"), "interrupted", json_output=True)
        else:
            Console(stderr=True).print("\n[yellow]Interrupted.[/yellow]")
        return 130
    except Exception as exc:  # API/transport errors need a concise CLI failure.
        _emit_error(exc, "investigation", json_output=args.json)
        return 1


if __name__ == "__main__":
    sys.exit(main())
