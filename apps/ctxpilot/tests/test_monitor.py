"""Tests for the auto layer: ProjectScanner grouping + Monitor new-session detection."""
from __future__ import annotations

from pathlib import Path

from ctxpilot.models import SessionTranscript
from ctxpilot.services.monitor import Monitor, ProjectScanner


class FakeAdapter:
    """In-memory adapter backed by real temp files so mtime diffing is real."""
    name = "fake"

    def __init__(self, sessions: list[tuple[Path, SessionTranscript]]):
        self._sessions = sessions

    def discover_sessions(self) -> list[Path]:
        return [p for p, _ in self._sessions]

    def parse_session(self, path: Path) -> SessionTranscript:
        for p, t in self._sessions:
            if p == path:
                return t
        raise KeyError(path)


def _write_session(tmp_path: Path, name: str, project_path: str | None, agent="fake") -> tuple[Path, SessionTranscript]:
    f = tmp_path / name
    f.write_text("{}", encoding="utf-8")
    t = SessionTranscript(agent=agent, session_id=name, project_path=project_path)
    return f, t


def test_scan_groups_sessions_by_project(tmp_path):
    a = _write_session(tmp_path, "a.json", "/proj/X")
    b = _write_session(tmp_path, "b.json", "/proj/X")
    ad = FakeAdapter([a, b])
    views = ProjectScanner([ad]).scan_projects(["/proj/X"])
    assert len(views) == 1
    v = views[0]
    assert "proj/X" in v.path.replace("\\", "/")
    assert len(v.sessions) == 2


def test_scan_includes_watched_root_without_sessions(tmp_path):
    ad = FakeAdapter([])
    views = ProjectScanner([ad]).scan_projects(["/proj/Y"])
    assert "proj/Y" in views[0].path.replace("\\", "/")
    assert len(views[0].sessions) == 0


def test_scan_unlinked_bucket(tmp_path):
    c = _write_session(tmp_path, "c.json", None)
    ad = FakeAdapter([c])
    views = ProjectScanner([ad]).scan_projects([])
    unlinked = [v for v in views if v.path.startswith("(未关联")]
    assert unlinked and len(unlinked[0].sessions) == 1


def test_monitor_reports_new_session(tmp_path):
    a = _write_session(tmp_path, "a.json", "/proj/X")
    ad = FakeAdapter([a])
    mon = Monitor([ad])
    # a.json already seeded as seen
    assert mon.poll() == []
    # add a new session file
    b = _write_session(tmp_path, "b.json", "/proj/X")
    ad._sessions.append(b)
    fresh = mon.poll()
    assert len(fresh) == 1
    assert fresh[0].session_id == "b.json"


def test_monitor_detects_changed_mtime(tmp_path):
    a = _write_session(tmp_path, "a.json", "/proj/X")
    ad = FakeAdapter([a])
    mon = Monitor([ad])
    mon.poll()
    # touch the file so mtime advances
    import time
    time.sleep(0.01)
    Path(a[0]).touch()
    changed = mon.poll()
    assert len(changed) == 1


def test_scan_infers_root_from_touched_files(tmp_path):
    """A session with NO recorded project_path is still grouped under the common
    parent of the files it touched — this is what lets the dashboard auto-list
    real projects without the user typing anything (issue #2)."""
    proj_dir = tmp_path / "myproject"
    proj_dir.mkdir()
    # absolute paths under the same project dir
    f1 = proj_dir / "a.py"
    f2 = proj_dir / "sub" / "b.py"
    f2.parent.mkdir()
    f1.write_text("x")
    f2.write_text("y")
    t = SessionTranscript(
        agent="fake",
        session_id="s.json",
        project_path=None,
        files_touched=[str(f1), str(f2)],
    )
    ad = FakeAdapter([(tmp_path / "s.json", t)])
    (tmp_path / "s.json").write_text("{}")
    views = ProjectScanner([ad]).scan_projects([])
    # the inferred root should be the project dir, not the unlinked bucket
    assert not any(v.path.startswith("(未关联") for v in views)
    assert str(proj_dir) in [v.path for v in views]
