"""Project scanning + real-time session monitoring (the "auto" layer).

- `ProjectScanner.scan_projects()` groups every discovered agent session by its
  project path, so the dashboard can list projects without the user typing paths.
- `Monitor` polls the adapter session stores and reports NEW sessions, so the
  dashboard can show "opencode just opened a session in <project>" live.

Both are pure logic and take adapters as injectable arguments (testable, and UI
never touches adapters directly — only the CtxPilot facade does).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from ctxpilot.models import ProjectView, SessionSummary, SessionTranscript


def _infer_root(files_touched: list[str]) -> str | None:
    """Fallback project root: common parent dir of the absolute files touched.

    Agent logs often omit the project path, but they record which files were
    edited. The common ancestor of those paths is a strong heuristic for the
    project root, so the dashboard can still list the project automatically.
    """
    abs_dirs: list[Path] = []
    for f in files_touched:
        p = Path(f)
        if p.is_absolute():
            abs_dirs.append(p.parent)
    if not abs_dirs:
        return None
    try:
        return os.path.commonpath([str(d) for d in abs_dirs])
    except ValueError:
        # paths on different drives — fall back to the first file's parent
        return str(abs_dirs[0])


def _summarize(t: SessionTranscript, mtime: float) -> SessionSummary:
    preview = ""
    for m in t.messages:
        if m.role == "user" and m.content.strip():
            preview = m.content.strip().replace("\n", " ")
            break
    if not preview and t.messages:
        preview = t.messages[0].content.strip().replace("\n", " ")
    if len(preview) > 140:
        preview = preview[:140] + "…"
    return SessionSummary(
        agent=t.agent,
        session_id=t.session_id,
        project_path=t.project_path,
        started_at=t.started_at,
        ended_at=t.ended_at,
        message_count=len(t.messages),
        files_touched=list(t.files_touched),
        preview=preview,
        mtime=mtime,
    )


class ProjectScanner:
    def __init__(self, adapters: list, git_runner=None):
        self._adapters = adapters
        self._git_runner = git_runner  # GitRunner | None

    def scan_projects(self, watched_roots: list[str] | None = None) -> list[ProjectView]:
        """Discover projects and the agent history attached to each.

        Auto-discovery (the default): a project root is derived from every
        discovered agent session — either its recorded ``project_path`` or, as a
        fallback, the common parent directory of the files it touched. This is
        what lets the dashboard list real projects WITHOUT the user typing paths.

        ``watched_roots`` (optional, from the UI/config) are pinned as extra
        project cards even when no session points at them.
        """
        transcripts: list[SessionTranscript] = []
        for ad in self._adapters:
            try:
                paths = ad.discover_sessions()
            except Exception:
                continue
            for p in paths:
                try:
                    t = ad.parse_session(p)
                except Exception:
                    continue
                try:
                    t._mtime = float(Path(p).stat().st_mtime)  # type: ignore[attr-defined]
                except OSError:
                    t._mtime = 0.0  # type: ignore[attr-defined]
                transcripts.append(t)

        # Group sessions by their (inferred) project root.
        # NOTE: we do NOT fold a child project into a parent container (the old
        # _merge_nested did that and produced wrong cards like "D:\\Documents"
        # swallowing "D:\\Documents\\kill-tower"). Each real project directory is
        # its own card, exactly as the user expects.
        root_map: dict[str, list[SessionTranscript]] = {}
        unlinked: list[SessionTranscript] = []
        for t in transcripts:
            root = self._root_of(t)
            if root:
                root_map.setdefault(self._norm(root), []).append(t)
            else:
                unlinked.append(t)

        views: list[ProjectView] = []
        configured = [self._norm(str(r)) for r in (watched_roots or [])]
        for r in configured:
            sessions: list[SessionTranscript] = root_map.pop(r, [])
            for proj in [k for k in list(root_map) if self._under(k, r)]:
                sessions.extend(root_map.pop(proj))
            views.append(self._view_for(r, sessions))

        for proj, slist in root_map.items():
            views.append(self._view_for(proj, slist))

        if unlinked:
            views.append(
                ProjectView(
                    path="(未关联项目 / unlinked)",
                    is_git=False,
                    branch=None,
                    recent_commits=[],
                    sessions=[_summarize(t, getattr(t, "_mtime", 0.0)) for t in unlinked],
                )
            )

        # git projects first, then by session count (most active on top)
        views.sort(key=lambda v: (not v.is_git, -len(v.sessions), v.path))
        return views

    # -- root inference ----------------------------------------------------
    @staticmethod
    def _root_of(t: SessionTranscript) -> str | None:
        if t.project_path:
            return t.project_path
        return _infer_root(t.files_touched)

    def _view_for(self, path: str, transcripts: list[SessionTranscript]) -> ProjectView:
        is_git = Path(path).joinpath(".git").exists()
        git: dict = self._git_collect(path) if is_git else {}
        return ProjectView(
            path=path,
            is_git=is_git,
            branch=git.get("branch"),
            recent_commits=git.get("recent_commits", []),
            sessions=[_summarize(t, getattr(t, "_mtime", 0.0)) for t in transcripts],
        )

    @staticmethod
    def _norm(p: str) -> str:
        try:
            return str(Path(p).resolve())
        except OSError:
            return str(Path(p).absolute())

    @staticmethod
    def _under(proj: str, root: str) -> bool:
        """True if `proj` equals `root` or is located under `root` (direction matters)."""
        proj, root = str(proj), str(root)
        return proj == root or proj.startswith(root + os.sep)

    def _git_collect(self, path: str) -> dict:
        from ctxpilot.ingestion import git_collect

        if self._git_runner:
            return git_collect(path, runner=self._git_runner)
        return git_collect(path)


class Monitor:
    """Polls adapter session stores and reports sessions that are NEW.

    Lightweight by design: no filesystem watcher library, just mtime diffing.
    Safe to unit-test by calling ``poll()`` directly with fake adapters.
    """

    def __init__(self, adapters: list, interval: float = 3.0):
        self._adapters = adapters
        self.interval = interval
        self._seen: dict[str, float] = {}  # "agent:filename" -> mtime
        self._running = False
        self._last_poll = 0.0
        self.seed()

    def seed(self) -> None:
        """(Re)build the baseline of sessions currently known on disk.

        Called on construction and again on ``start()`` so that the live feed
        only reports sessions that appear AFTER monitoring begins.
        """
        self._seen.clear()
        for ad in self._adapters:
            try:
                for p in ad.discover_sessions():
                    self._mark(ad.name, p)
            except Exception:
                continue

    @property
    def known_count(self) -> int:
        """Number of sessions in the current baseline (what we are watching)."""
        return len(self._seen)

    def _mark(self, agent: str, path: Path) -> None:
        key = f"{agent}:{Path(path).name}"
        try:
            mtime = float(Path(path).stat().st_mtime)
        except OSError:
            mtime = 0.0
        self._seen[key] = mtime

    def poll(self) -> list[SessionSummary]:
        """Return summaries of sessions that are NEW or CHANGED since last poll.

        - A session whose key was never seen before is reported (a freshly
          opened agent session → "新会话" in the live feed).
        - A known session whose mtime advanced (an in-progress session that got
          new messages) is reported again so the feed reflects activity.

        Visual flooding is prevented at the UI layer, which dedups by
        ``agent:session_id`` — so a continuously-written session appears as a
        single feed line rather than dozens of duplicates.
        """
        new: list[SessionSummary] = []
        for ad in self._adapters:
            try:
                paths = ad.discover_sessions()
            except Exception:
                continue
            for p in paths:
                key = f"{ad.name}:{Path(p).name}"
                try:
                    mtime = float(Path(p).stat().st_mtime)
                except OSError:
                    mtime = 0.0
                if key not in self._seen:
                    try:
                        t = ad.parse_session(p)
                    except Exception:
                        self._seen[key] = mtime
                        continue
                    self._seen[key] = mtime
                    new.append(_summarize(t, mtime))
                elif mtime != self._seen[key]:
                    # known session whose content changed — report once, refresh baseline
                    try:
                        t = ad.parse_session(p)
                    except Exception:
                        self._seen[key] = mtime
                        continue
                    self._seen[key] = mtime
                    new.append(_summarize(t, mtime))
                else:
                    # seen & unchanged — keep baseline fresh, no re-emit
                    self._seen[key] = mtime
        self._last_poll = time.time()
        return new

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    @property
    def running(self) -> bool:
        return self._running
