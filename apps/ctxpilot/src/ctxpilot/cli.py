"""CLI — thin wrapper over the CtxPilot facade (DESIGN.md §3.7).

No business logic here: parse args, call CtxPilot, print with rich.
"""
from __future__ import annotations

import typer
from rich.console import Console

from ctxpilot.config import Config
from ctxpilot.core import CtxPilot

app = typer.Typer(help="CtxPilot / 续舱 — 跨会话上下文连续性层 (powered by Hy3)")
console = Console()


def _ctx() -> CtxPilot:
    return CtxPilot(Config.from_env())


@app.command()
def snapshot(project: str = typer.Argument(..., help="Project directory to snapshot")):
    """Build HANDOFF.md for a project and write it (sanitized + git-ignored)."""
    cp = _ctx()
    snap = cp.snapshot(project)
    path = cp.snapshot_svc.write(snap, project)
    console.print(f"[green]✓[/] HANDOFF.md -> {path}")
    console.print(f"  goals={len(snap.goals)} tasks={len(snap.tasks)} decisions={len(snap.decisions)}")


@app.command()
def export(
    project: str = typer.Argument(..., help="Project directory"),
    out: str = typer.Option("handoff.json", help="Output file (.json)"),
    target: str = typer.Option(None, help="Target agent name"),
):
    """Export a portable handoff envelope."""
    cp = _ctx()
    exp = cp.export(project, target_agent=target)
    cp.handoff_svc.to_file(exp, out)
    console.print(f"[green]✓[/] Exported handoff to {out}")


@app.command()
def import_handoff(
    file: str = typer.Argument(..., help="Handoff .json or HANDOFF.md"),
    target: str = typer.Option(None, help="Target agent name"),
):
    """Render the injection text for a NEW agent session."""
    cp = _ctx()
    console.print(cp.import_handoff(file, target_agent=target))


@app.command()
def brief(project: str = typer.Argument(..., help="Project directory")):
    """Print a 5-line onboarding brief for a restarted session."""
    cp = _ctx()
    console.print(cp.brief(project))


@app.command()
def watch(project: str = typer.Argument(..., help="Project directory")):
    """(phase 2) Run the drift watchdog and print signals."""
    cp = _ctx()
    report = cp.watch(project)
    if not report.signals:
        console.print("[green]✓[/] No drift detected.")
        return
    for s in report.signals:
        color = {"red": "red", "yellow": "yellow", "info": "blue"}.get(s.severity, "white")
        console.print(f"[{color}]{s.severity.upper()}[/{color}] {s.kind}: {s.detail}")


@app.command()
def config():
    """Show current configuration (API key is masked)."""
    c = Config.from_store()
    masked = ("****" + c.hy3_api_key[-4:]) if c.hy3_api_key else "(not set)"
    console.print(f"base_url        : {c.hy3_base_url}")
    console.print(f"model           : {c.hy3_model}")
    console.print(f"reasoning       : {c.hy3_reasoning_effort}")
    console.print(f"api_key         : {masked}")
    console.print(f"has_credentials : {c.has_credentials}")
    console.print(f"project_roots   : {c.project_roots or [str(c.project_path)]}")


@app.command()
def serve(host: str = typer.Option("127.0.0.1"), port: int = typer.Option(8000)):
    """Start the Web dashboard (auto-scan + live monitor + key UI)."""
    import uvicorn

    from ctxpilot.web.api import create_app

    cfg = Config.from_store()
    app = create_app(config=cfg)
    console.print(f"[green]✓[/] CtxPilot dashboard -> http://{host}:{port}")
    if not cfg.has_credentials:
        console.print("[yellow]! 尚未配置 Hy3 Key，打开页面右上角「设置」填入即可。[/]")
    uvicorn.run(app, host=host, port=port)


@app.command()
def qt():
    """Launch the Qt desktop client (install with: pip install ctxpilot[qt])."""
    try:
        from ctxpilot.qt.app import run_qt
    except ImportError:
        console.print("[red]✗ PySide6 未安装。[/] 运行: pip install ctxpilot[qt] 后再试。")
        raise typer.Exit(code=2)
    raise SystemExit(run_qt())


def main() -> None:
    app()


if __name__ == "__main__":
    main()
