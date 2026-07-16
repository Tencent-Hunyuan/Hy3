"""CtxPilot facade — the single boundary between UI and business logic (DESIGN.md §3.7).

Both CLI and Web depend ONLY on this class. Dependencies (hy3 client, adapters)
are injectable so every sub-business can be unit-tested in isolation.
"""
from __future__ import annotations

from ctxpilot.config import Config
from ctxpilot.hy3.client import Hy3Client
from ctxpilot.ingestion import RawMaterial, collect
from pathlib import Path
from ctxpilot.models import ProjectStateSnapshot
from ctxpilot.services import (
    BriefService,
    DriftService,
    HandoffService,
    MemoryService,
    SavingsService,
    SnapshotService,
)
from ctxpilot.services.handoff import HandoffExport
from ctxpilot.services.monitor import Monitor, ProjectScanner


class CtxPilot:
    def __init__(self, config: Config | None = None, hy3: Hy3Client | None = None, adapters: list | None = None):
        self.config = config or Config.from_env()
        self.hy3 = hy3 or Hy3Client(
            api_key=self.config.hy3_api_key,
            base_url=self.config.hy3_base_url,
            model=self.config.hy3_model,
            reasoning_effort=self.config.hy3_reasoning_effort,
        )
        self._adapters = adapters
        # sub-business services — independent, composed here
        self.snapshot_svc = SnapshotService()
        self.handoff_svc = HandoffService()
        self.brief_svc = BriefService()
        self.drift_svc = DriftService()
        self.memory_svc = MemoryService()
        self.savings_svc = SavingsService()
        # avoid regenerating the snapshot on every call (each call = 1 Hy3 round-trip)
        self._snap_cache: dict[str, ProjectStateSnapshot] = {}
        # auto layer: scan + real-time monitor (read-only over agent stores)
        self._monitor = Monitor(self._effective_adapters())
        self._scanner = ProjectScanner(self._effective_adapters())
        # Explicitly pinned roots (from UI/config); auto-discovery still runs on
        # top, so an empty list just means "discover from agent histories only".
        self._project_roots = list(self.config.project_roots)

    # -- internals ---------------------------------------------------------
    def _effective_adapters(self) -> list:
        if self._adapters:
            return self._adapters
        from ctxpilot.adapters.base import get_adapter, list_adapters

        return [get_adapter(n) for n in list_adapters()]

    def _collect(self, project_path: str | None = None) -> RawMaterial:
        pp = project_path or str(self.config.project_path)
        return collect(pp, adapters=self._adapters)

    def _source_agent(self) -> str:
        if self.config.agents:
            return self.config.agents[0]
        if self._adapters:
            return getattr(self._adapters[0], "name", "ctxpilot")
        return "ctxpilot"

    # -- MVP use-cases -----------------------------------------------------
    def snapshot(self, project_path: str | None = None, force: bool = False) -> ProjectStateSnapshot:
        key = project_path or str(self.config.project_path)
        if not force and key in self._snap_cache:
            return self._snap_cache[key]
        raw = self._collect(key)
        snap = self.snapshot_svc.build(raw, self.hy3, reasoning_effort=self.config.hy3_reasoning_effort)
        self._snap_cache[key] = snap
        return snap

    def export(self, project_path: str | None = None, target_agent: str | None = None) -> HandoffExport:
        snap = self.snapshot(project_path)
        return self.handoff_svc.export(snap, source_agent=self._source_agent())

    def import_handoff(self, file_path: str, target_agent: str | None = None) -> str:
        return self.handoff_svc.import_as_prompt(file_path, target_agent=target_agent)

    def brief(self, project_path: str | None = None) -> str:
        snap = self.snapshot(project_path)
        return self.brief_svc.generate(snap, self.hy3)

    # -- phase-2 use-cases -------------------------------------------------
    def watch(self, project_path: str | None = None) -> "DriftReport":  # noqa: F821
        from ctxpilot.services.drift import DriftReport

        raw = self._collect(project_path)
        return self.drift_svc.analyze(raw, self.hy3)

    def savings(self, project_path: str | None = None) -> dict:
        raw = self._collect(project_path)
        snap = self.snapshot(project_path)
        return self.savings_svc.estimate(raw, snapshot=snap, project_path=raw.project_path)

    # -- auto layer: scan + live monitor -----------------------------------
    def scan_projects(self) -> list:
        """List discovered projects and their agent history (no manual path)."""
        return self._scanner.scan_projects(self._project_roots)

    def monitor_poll(self) -> list:
        """Return agent sessions that appeared/changed since the last poll."""
        return self._monitor.poll()

    def monitor_running(self) -> bool:
        return self._monitor.running

    def monitor_start(self) -> dict:
        # Re-seed so the live feed only reports sessions that appear AFTER this
        # moment (the baseline is "everything currently on disk").
        self._monitor.seed()
        self._monitor.start()
        return self.monitor_status()

    def monitor_stop(self) -> None:
        self._monitor.stop()

    def monitor_status(self) -> dict:
        """Visibility for the UI: what we watch + how many sessions known."""
        return {
            "running": self._monitor.running,
            "agents_watched": [a["name"] for a in self.detected_agents()],
            "known_sessions": self._monitor.known_count,
        }

    def detected_agents(self) -> list[dict]:
        """Which agents we can monitor right now, with live session counts.

        Read-only discovery — never touches agent internals. This is what the
        UI shows so the user knows what is being watched.
        """
        out: list[dict] = []
        for ad in self._effective_adapters():
            try:
                sessions = ad.discover_sessions()
            except Exception:
                sessions = []
            out.append(
                {
                    "name": ad.name,
                    "session_count": len(sessions),
                    "store_path": getattr(ad, "store_path", None),
                    "available": bool(sessions) or getattr(ad, "available", True),
                }
            )
        return out

    def test_connection(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        reasoning: str | None = None,
    ) -> dict:
        """Lightweight Hy3 reachability check (no project work).

        If any override is supplied, a FRESH client is built from those values —
        this is what the UI "测试连接" button uses to validate what the user just
        typed, before saving. With no overrides, the already-configured client
        (``self.hy3``, injectable in tests) is used.
        """
        key = api_key or self.config.hy3_api_key
        url = base_url or self.config.hy3_base_url
        if not key or not url:
            return {"ok": False, "error": "missing_credentials"}
        if api_key or base_url or model or reasoning:
            client: Hy3Client = Hy3Client(
                api_key=key,
                base_url=url,
                model=model or self.config.hy3_model,
                reasoning_effort=reasoning or self.config.hy3_reasoning_effort,
            )
        else:
            client = self.hy3
        try:
            client.chat("ping")
            return {"ok": True}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def list_project_roots(self) -> list[str]:
        return list(self._project_roots)

    def add_project_root(self, path: str) -> list[str]:
        p = str(Path(path).resolve())
        if p not in self._project_roots:
            self._project_roots.append(p)
            self.config.project_roots = list(self._project_roots)
            self.config.save()
        return list(self._project_roots)

    # -- credentials (UI-settable, stored locally, never echoed) -----------
    def set_credentials(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        reasoning: str | None = None,
    ) -> None:
        if api_key is not None:
            self.config.hy3_api_key = api_key
        if base_url is not None:
            self.config.hy3_base_url = base_url
        if model is not None:
            self.config.hy3_model = model
        if reasoning is not None:
            self.config.hy3_reasoning_effort = reasoning
        self.hy3 = Hy3Client(
            api_key=self.config.hy3_api_key,
            base_url=self.config.hy3_base_url,
            model=self.config.hy3_model,
            reasoning_effort=self.config.hy3_reasoning_effort,
        )
        self.config.save()
