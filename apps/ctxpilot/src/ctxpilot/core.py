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

    # -- default continuation (Point ④) -----------------------------------
    # Both opencode and codex auto-load `AGENTS.md` from the project root on
    # EVERY session start. We exploit that as the safe "default continuation"
    # injection point: a guarded marker block (and ONLY that block — user
    # content is never touched) tells a fresh session to read HANDOFF.md.
    _MARKER_OPEN = "<!-- ctxpilot:handoff -->"
    _MARKER_CLOSE = "<!-- /ctxpilot -->"

    def install_handoff(self, project_path: str | None = None, agents: list[str] | None = None) -> dict:
        """Make a project resume automatically across new sessions / agent switches.

        - Ensures ``HANDOFF.md`` exists (generates it via Hy3 if missing; if no
          key is configured the block is still installed and a warning returned).
        - Upserts a guarded marker block into the project's ``AGENTS.md`` — the
          file opencode & codex auto-read on session start. The block is the only
          thing we ever write there; any user content outside it is preserved.
        """
        pp = str(Path(project_path or str(self.config.project_path)).resolve())
        agents_used = agents or self._agents_for_project(pp)

        handoff_md = Path(pp) / "HANDOFF.md"
        warning = None
        if not handoff_md.exists():
            try:
                snap = self.snapshot(pp)
                self.snapshot_svc.write(snap, pp)
            except Exception as e:  # noqa: BLE001
                warning = f"HANDOFF.md 未生成（需配置 Hy3 Key）：{e}"

        block = self._handoff_block(agents_used)
        agents_md = self._upsert_agents_md(pp, block)
        return {
            "installed": True,
            "agents_md": str(agents_md),
            "agents": agents_used,
            "handoff_md": str(handoff_md),
            "handoff_generated": handoff_md.exists(),
            "warning": warning,
        }

    def continue_prompt(self, project_path: str | None = None) -> str:
        """Copy-paste prompt a user can drop into a brand-new agent session."""
        return (
            "请先阅读本项目的 HANDOFF.md（位于项目根目录），它记录了由 CtxPilot "
            "(powered by Hy3) 维护的跨会话上下文快照：目标 / 任务 / 决策 / 未决问题 / 约定。\n"
            "据此续接工作，不要从头重复已完成的探索与文件扫描。\n"
            "若 HANDOFF.md 缺失或已过时，可运行 `python -m ctxpilot snapshot <project>` 刷新。"
        )

    def handoff_status(self, project_path: str) -> dict:
        pp = Path(project_path).resolve()
        handoff = (pp / "HANDOFF.md").exists()
        md = pp / "AGENTS.md"
        installed = False
        if md.exists():
            try:
                installed = self._MARKER_OPEN in md.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                installed = False
        return {"has_handoff": handoff, "installed": installed}

    def _agents_for_project(self, pp: str) -> list[str]:
        norm = str(Path(pp).resolve())
        for v in self._scanner.scan_projects(self._project_roots):
            if str(Path(v.path).resolve()) == norm:
                return sorted({s.agent for s in v.sessions}) or ["ctxpilot"]
        return ["ctxpilot"]

    @staticmethod
    def _handoff_block(agents: list[str]) -> str:
        ags = ", ".join(agents) or "ctxpilot"
        return (
            f"{CtxPilot._MARKER_OPEN}\n"
            "# CtxPilot 跨会话续接\n"
            f"本项目的上下文快照由 **CtxPilot** (powered by Hy3) 维护，新会话 / 切换 agent（{ags}）时默认续接。\n"
            "- 开始工作前请先阅读仓库根目录的 `HANDOFF.md`（含目标 / 任务 / 决策 / 未决问题 / 约定）。\n"
            "- 不要从头重复已完成的探索；若 `HANDOFF.md` 缺失或过时，运行 `python -m ctxpilot snapshot <project>` 刷新。\n"
            f"{CtxPilot._MARKER_CLOSE}"
        )

    def _upsert_agents_md(self, pp: str, block: str) -> Path:
        base = Path(pp)
        base.mkdir(parents=True, exist_ok=True)  # mirror SnapshotService.write's robustness
        md = base / "AGENTS.md"
        if md.exists():
            content = md.read_text(encoding="utf-8", errors="ignore")
            start = content.find(self._MARKER_OPEN)
            end = content.find(self._MARKER_CLOSE)
            if start != -1 and end != -1:
                end += len(self._MARKER_CLOSE)
                new_content = content[:start] + block + content[end:]
            else:
                sep = "\n\n" if content.strip() else ""
                new_content = content + sep + block + "\n"
        else:
            new_content = block + "\n"
        md.write_text(new_content, encoding="utf-8")
        return md

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
