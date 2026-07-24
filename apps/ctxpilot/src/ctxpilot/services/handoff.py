"""N4 — HandoffService: export / import a portable project-state envelope.

Cross-agent handoff: `export` produces a `HandoffExport` (JSON by default), and
`import_as_prompt` renders text a NEW agent can paste as its first context —
so it reads the HANDOFF instead of re-reading the whole repo (scenario B).
"""
from __future__ import annotations

from pathlib import Path

from ctxpilot.models import HandoffExport, ProjectStateSnapshot


class HandoffService:
    def export(self, snap: ProjectStateSnapshot, source_agent: str = "") -> HandoffExport:
        return HandoffExport(source_agent=source_agent, snapshot=snap)

    def to_file(self, exp: HandoffExport, path: str | Path) -> Path:
        return exp.to_file(path)

    def _resolve_snapshot(self, source) -> ProjectStateSnapshot | None:
        if isinstance(source, ProjectStateSnapshot):
            return source
        if isinstance(source, HandoffExport):
            return source.snapshot
        p = Path(source)
        text = p.read_text(encoding="utf-8")
        if p.suffix == ".json":
            return HandoffExport.from_json(text).snapshot
        # treat as HANDOFF.md markdown
        return ProjectStateSnapshot.from_markdown(text)

    def import_as_prompt(self, source: str | Path | HandoffExport | ProjectStateSnapshot,
                         target_agent: str | None = None) -> str:
        snap = self._resolve_snapshot(source)
        if snap is None:
            raise ValueError("No snapshot found in handoff source")
        header = "# CONTEXT HANDOFF (by CtxPilot, powered by Hy3)"
        if target_agent:
            header += f" — for agent: {target_agent}"
        header += "\nRead this before starting; do NOT re-read the entire repository.\n"
        return header + "\n" + snap.to_markdown()
