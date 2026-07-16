"""N7 — BriefService: generate a short onboarding brief for a restarted session.

Answers "what should I look at first?" so a freshly restarted agent (or you after
a time gap) gets oriented instantly instead of re-reading everything.
"""
from __future__ import annotations

from ctxpilot.models import ProjectStateSnapshot

SYSTEM = (
    "You are CtxPilot. Given a project state snapshot, write a 5-line onboarding "
    "brief for a new session: (1) current goal, (2) the single most urgent blocker, "
    "(3) which file to read first, (4) one recent decision to respect, (5) one open "
    "risk. Plain text, no headings."
)


class BriefService:
    def render_prompt(self, snap: ProjectStateSnapshot) -> str:
        return snap.to_markdown()

    def generate(self, snap: ProjectStateSnapshot, hy3) -> str:
        return hy3.chat(self.render_prompt(snap), system=SYSTEM)
