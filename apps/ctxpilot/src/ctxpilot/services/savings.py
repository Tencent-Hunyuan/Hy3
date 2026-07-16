"""N6 (phase 2) — SavingsService: quantify avoided re-read cost.

Turns Hy3's token efficiency into a concrete PR narrative: reusing the snapshot
vs. re-reading the repo/sessions. Pure function — trivially testable.
"""
from __future__ import annotations

from ctxpilot.ingestion import RawMaterial
from ctxpilot.models import ProjectStateSnapshot


def _estimate_project_tokens(project_path: str | None) -> int:
    # very rough heuristic if no real measurement available
    return 4000


class SavingsService:
    def estimate(
        self,
        raw: RawMaterial,
        snapshot: ProjectStateSnapshot | None = None,
        project_path: str | None = None,
    ) -> dict:
        reread_tokens = sum(t.token_usage for t in raw.transcripts) + _estimate_project_tokens(project_path)
        snapshot_tokens = 0
        if snapshot is not None:
            snapshot_tokens = max(1, len(snapshot.to_markdown()) // 4)
        saved = max(0, reread_tokens - snapshot_tokens)
        ratio = (reread_tokens / snapshot_tokens) if snapshot_tokens else 0.0
        return {
            "reread_tokens": reread_tokens,
            "snapshot_tokens": snapshot_tokens,
            "saved_tokens": saved,
            "reduction_ratio": round(ratio, 2),
        }
