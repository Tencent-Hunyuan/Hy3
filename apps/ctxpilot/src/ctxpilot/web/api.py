"""Web API — FastAPI routes that call the CtxPilot facade (DESIGN.md §4).

The UI (web/static) only ever talks to these JSON endpoints; it never touches
business logic directly. `create_app` accepts injected config/hy3/adapters so
every route can be unit-tested without a real Hy3 endpoint or real agents.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ctxpilot.config import Config
from ctxpilot.core import CtxPilot
from ctxpilot.hy3.client import Hy3Error

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_INDEX = _STATIC_DIR / "index.html"


class ProjectReq(BaseModel):
    project_path: str
    target_agent: str | None = None


class ConfigReq(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    reasoning: str | None = None
    project_roots: list[str] | None = None


class TestReq(BaseModel):
    """Values the user just typed into the settings form (validated before save)."""

    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    reasoning: str | None = None


def create_app(config: Config | None = None, hy3=None, adapters: list | None = None) -> FastAPI:
    cfg = config or Config.from_store()
    cp = CtxPilot(cfg, hy3=hy3, adapters=adapters)

    app = FastAPI(title="CtxPilot", version="0.2.0")

    # -- graceful error envelope ------------------------------------------
    # So the UI shows a clean message (not a raw 500 HTML page) when Hy3 is
    # unconfigured or the model call fails. This is what makes "生成 HANDOFF"
    # failures legible to the user instead of looking broken.
    @app.exception_handler(Hy3Error)
    def _hy3_err(_, exc):
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})

    @app.exception_handler(Exception)
    def _unhandled(_, exc):
        return JSONResponse(status_code=500, content={"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    @app.get("/")
    def index():
        return FileResponse(str(_INDEX))

    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/health")
    def health():
        return {"status": "ok", "has_credentials": cfg.has_credentials}

    @app.get("/config")
    def get_config():
        # Never echo the raw key — only whether one is set.
        return {
            "base_url": cfg.hy3_base_url,
            "model": cfg.hy3_model,
            "reasoning": cfg.hy3_reasoning_effort,
            "has_credentials": cfg.has_credentials,
            "project_roots": cp.list_project_roots(),
            "monitor_running": cp.monitor_running(),
            "agents": cp.detected_agents(),
        }

    @app.post("/config")
    def post_config(req: ConfigReq):
        cp.set_credentials(
            api_key=req.api_key,
            base_url=req.base_url,
            model=req.model,
            reasoning=req.reasoning,
        )
        if req.project_roots is not None:
            for r in req.project_roots:
                cp.add_project_root(r)
        return {"ok": True, "has_credentials": cfg.has_credentials}

    @app.get("/scan")
    def scan():
        return {"projects": [p.to_dict() for p in cp.scan_projects()]}

    @app.get("/agents")
    def agents():
        # What the user can monitor right now — drives the agent-visibility strip.
        return {"agents": cp.detected_agents()}

    @app.get("/monitor/status")
    def monitor_status():
        return cp.monitor_status()

    @app.get("/sessions")
    def sessions():
        # Current known sessions across all projects (one snapshot, no diffing).
        projs = cp.scan_projects()
        all_sessions = [s for p in projs for s in p.sessions]
        return {"sessions": [s.to_dict() for s in all_sessions]}

    @app.post("/config/test")
    def config_test(req: TestReq):
        # Validate the TYPED-IN values, not the stored config — so the user can
        # test connectivity before committing the key.
        return cp.test_connection(
            api_key=req.api_key, base_url=req.base_url, model=req.model, reasoning=req.reasoning
        )

    @app.get("/events")
    def events():
        # New/changed agent sessions since the last poll — drives live feed.
        return {"events": [s.to_dict() for s in cp.monitor_poll()]}

    @app.post("/monitor/start")
    def monitor_start():
        # Re-seed baseline and return it so the UI can show "monitoring N sessions"
        # immediately instead of a blank feed.
        return cp.monitor_start()

    @app.post("/monitor/stop")
    def monitor_stop():
        cp.monitor_stop()
        return {"running": False}

    @app.post("/projects/add")
    def add_project(req: ProjectReq):
        roots = cp.add_project_root(req.project_path)
        return {"project_roots": roots}

    @app.post("/snapshot")
    def snapshot(req: ProjectReq):
        snap = cp.snapshot(req.project_path)
        path = cp.snapshot_svc.write(snap, req.project_path)
        return {
            "written_to": str(path),
            "generated_at": snap.generated_at,
            "goals": snap.goals,
            "tasks": [t.to_dict() for t in snap.tasks],
            "decisions": [d.to_dict() for d in snap.decisions],
            "open_issues": snap.open_issues,
        }

    @app.post("/export")
    def export(req: ProjectReq):
        exp = cp.export(req.project_path, target_agent=req.target_agent)
        return exp.to_dict()

    @app.post("/import")
    def import_handoff(req: ProjectReq):
        # project_path carries the handoff file path here
        prompt = cp.import_handoff(req.project_path, target_agent=req.target_agent)
        return {"prompt": prompt}

    @app.post("/brief")
    def brief(req: ProjectReq):
        return {"brief": cp.brief(req.project_path)}

    @app.post("/watch")
    def watch(req: ProjectReq):
        report = cp.watch(req.project_path)
        return report.to_dict()

    @app.post("/savings")
    def savings(req: ProjectReq):
        return cp.savings(req.project_path)

    return app
