"""
CLI entry point — `archaeologist` command.

Usage:
  archaeologist analyze https://github.com/user/repo
  archaeologist ask "What design patterns are used?"
  archaeologist serve
"""

from __future__ import annotations

import asyncio
import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from app.pipeline.orchestrator import Pipeline

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="Codebase Archaeologist")
def cli():
    """Codebase Archaeologist — Hy3-powered codebase understanding."""


@cli.command()
@click.argument("repo_url")
@click.option("--output", "-o", default=None, help="Save report to file")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def analyze(repo_url: str, output: str | None, verbose: bool):
    """Analyze a GitHub repository and print the architecture report."""

    async def _run():
        pipeline = Pipeline()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress_bar:
            task = progress_bar.add_task("Starting analysis...", total=None)

            def on_progress(phase, pct, message, data=None):
                progress_bar.update(task, description=f"[{pct}%] {message}")

            try:
                report = await pipeline.analyze(repo_url, progress=on_progress)
                _display_report(report, verbose)
                _print_usage_summary(pipeline)

                if output:
                    with open(output, "w") as f:
                        f.write(report.model_dump_json(indent=2))
                    console.print(f"\n[green]Report saved to {output}[/green]")
            except Exception as e:
                console.print(f"[red]Analysis failed: {e}[/red]")
                raise

    asyncio.run(_run())


@cli.command()
@click.argument("question")
def ask(question: str):
    """Ask a question about the last analyzed repository."""
    console.print("[yellow]QA mode requires a running server. Use `archaeologist serve` first.[/yellow]")
    console.print(f"Would ask: {question}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8000, help="Port to bind")
def serve(host: str, port: int):
    """Start the Web UI server."""
    import uvicorn

    console.print(Panel.fit(
        f"[bold]Codebase Archaeologist[/bold]\n"
        f"Web UI: [blue]http://{host}:{port}[/blue]\n"
        f"API Docs: [blue]http://{host}:{port}/docs[/blue]",
        title="Server Starting",
    ))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


# ── Display helpers ───────────────────────────────────────────

def _display_report(report, verbose: bool):
    """Pretty-print the architecture report."""
    arch = report.overview

    console.print()
    console.rule(f"[bold]Architecture Report: {arch.language} / {arch.framework}[/bold]")

    console.print(Panel(
        f"[bold]Style:[/bold] {arch.architecture_style}\n"
        f"[bold]Summary:[/bold] {arch.summary}",
        title="Overview",
    ))

    # Reading guide
    if arch.reading_guide:
        console.print("\n[bold]📖 Reading Guide:[/bold]")
        for i, step in enumerate(arch.reading_guide, 1):
            console.print(f"  {i}. {step}")

    # Modules
    table = Table(title="Modules", show_header=True, header_style="bold")
    table.add_column("Module")
    table.add_column("Responsibility")
    table.add_column("Stability")
    for mod in report.modules:
        stability_color = {
            "high": "green", "medium": "yellow", "low": "red", "volatile": "red"
        }.get(mod.stability, "white")
        table.add_row(
            mod.name,
            mod.responsibility[:80] + ("..." if len(mod.responsibility) > 80 else ""),
            f"[{stability_color}]{mod.stability}[/{stability_color}]",
        )
    console.print(table)

    # Design patterns
    if report.design_patterns:
        console.print("\n[bold]🎨 Design Patterns:[/bold]")
        for dp in report.design_patterns:
            icon = "✅" if dp.appropriateness == "appropriate" else "⚠️"
            console.print(f"  {icon} {dp.pattern} @ {dp.location}")
            if verbose and dp.note:
                console.print(f"     {dp.note}")

    # Risks
    if report.risks:
        console.print("\n[bold]⚠️ Risks:[/bold]")
        for risk in report.risks:
            color = {"critical": "red", "high": "red", "medium": "yellow", "low": "white"}.get(
                risk.severity, "white"
            )
            console.print(f"  [{color}]{risk.severity.upper()}[/{color}] {risk.risk_type}: "
                          f"{', '.join(risk.location[:3])}")
            if verbose and risk.fix_suggestion:
                console.print(f"     Fix: {risk.fix_suggestion}")

    # Call chains
    if report.call_chains and verbose:
        console.print("\n[bold]⚡ Key Call Chains:[/bold]")
        for chain in report.call_chains[:5]:
            console.print(f"  [bold]{chain.name}[/bold]")
            console.print(f"  {' → '.join(chain.sequence[:8])}")
            if chain.description:
                console.print(f"  {chain.description[:120]}")
            console.print()

    # Metrics
    m = report.metrics
    console.print(f"\n[bold]📊 Metrics:[/bold] "
                  f"{m.total_modules} modules, {m.total_classes} classes, "
                  f"avg depth {m.avg_dependency_depth:.1f}")


def _print_usage_summary(pipeline):
    """Print token usage and cost summary."""
    usage = pipeline.hy3.usage
    console.print(f"\n[dim]Token usage: {usage.summary()}[/dim]")


if __name__ == "__main__":
    cli()
