"""Tests for the CtxPilot facade — all sub-businesses reachable via one boundary."""
from __future__ import annotations

from ctxpilot.config import Config
from ctxpilot.core import CtxPilot
from ctxpilot.services.drift import DriftReport

from conftest import FakeHy3, SAMPLE_MARKDOWN, make_raw


def _cp(responses=None):
    cfg = Config(hy3_api_key="k", hy3_base_url="http://x", hy3_model="hy3")
    return CtxPilot(config=cfg, hy3=FakeHy3(responses or [SAMPLE_MARKDOWN]))


def test_snapshot_and_export_roundtrip():
    cp = _cp()
    snap = cp.snapshot("/tmp/proj")
    assert "Ship MVP" in snap.goals
    exp = cp.export("/tmp/proj")
    assert exp.snapshot is not None
    assert exp.snapshot.goals == snap.goals


def test_brief_uses_hy3():
    cp = _cp([SAMPLE_MARKDOWN, "brief text from hy3"])
    assert cp.brief("/tmp/proj") == "brief text from hy3"


def test_import_handoff_renders_prompt(tmp_path):
    cp = _cp()
    exp = cp.export("/tmp/proj")
    f = cp.handoff_svc.to_file(exp, tmp_path / "h.json")
    prompt = cp.import_handoff(str(f), target_agent="codex")
    assert "CONTEXT HANDOFF" in prompt


def test_watch_returns_drift_report():
    cp = _cp([SAMPLE_MARKDOWN, "red|loop|retrying", "yellow|contradiction|switched"])
    # snapshot consumes first response; watch gets the drift text
    _ = cp.snapshot("/tmp/proj")
    report = cp.watch("/tmp/proj")
    assert isinstance(report, DriftReport)
    assert report.has_red


def test_savings_returns_dict():
    cp = _cp()
    res = cp.savings("/tmp/proj")
    assert "saved_tokens" in res and res["saved_tokens"] > 0


class _FakeAdapter:
    name = "fake"

    def __init__(self, sessions):
        self._sessions = sessions

    def discover_sessions(self):
        return [p for p, _ in self._sessions]

    def parse_session(self, path):
        for p, t in self._sessions:
            if p == path:
                return t
        raise KeyError(path)


def test_detected_agents_reports_monitorable():
    from ctxpilot.models import SessionTranscript

    f = "/tmp/s.json"
    t = SessionTranscript(agent="fake", session_id="s.json")
    cp = CtxPilot(config=Config(hy3_api_key="k", hy3_base_url="http://x"),
                  hy3=FakeHy3([SAMPLE_MARKDOWN]), adapters=[_FakeAdapter([(f, t)])])
    agents = cp.detected_agents()
    assert agents[0]["name"] == "fake"
    assert agents[0]["session_count"] == 1


def test_monitor_status_structure():
    from ctxpilot.models import SessionTranscript

    f = "/tmp/s.json"
    t = SessionTranscript(agent="fake", session_id="s.json")
    cp = CtxPilot(config=Config(hy3_api_key="k", hy3_base_url="http://x"),
                  hy3=FakeHy3([SAMPLE_MARKDOWN]), adapters=[_FakeAdapter([(f, t)])])
    st = cp.monitor_status()
    assert st["running"] is False
    assert "fake" in st["agents_watched"]
    assert st["known_sessions"] == 1


def test_test_connection_ok_with_credentials():
    cp = _cp()
    assert cp.test_connection()["ok"] is True


def test_test_connection_fails_without_credentials():
    cfg = Config(hy3_api_key="", hy3_base_url="")
    cp = CtxPilot(config=cfg, hy3=FakeHy3([SAMPLE_MARKDOWN]))
    assert cp.test_connection()["ok"] is False
    assert cp.test_connection()["error"] == "missing_credentials"


def test_install_handoff_writes_marker_block(tmp_path):
    cp = _cp()
    proj = tmp_path / "proj"
    proj.mkdir()
    res = cp.install_handoff(str(proj))
    assert res["installed"] is True
    agents_md = proj / "AGENTS.md"
    assert agents_md.exists()
    content = agents_md.read_text(encoding="utf-8")
    assert "<!-- ctxpilot:handoff -->" in content
    assert "<!-- /ctxpilot -->" in content
    assert (proj / "HANDOFF.md").exists()
    # re-install updates the block, never duplicates it
    cp.install_handoff(str(proj))
    assert agents_md.read_text(encoding="utf-8").count("<!-- ctxpilot:handoff -->") == 1


def test_install_handoff_preserves_user_content(tmp_path):
    cp = _cp()
    proj = tmp_path / "proj"
    proj.mkdir()
    user_md = proj / "AGENTS.md"
    user_md.write_text("# My Project\n\nSome user rules here.\n", encoding="utf-8")
    cp.install_handoff(str(proj))
    content = user_md.read_text(encoding="utf-8")
    assert "Some user rules here." in content
    assert content.index("Some user rules here.") < content.index("<!-- ctxpilot:handoff -->")


def test_handoff_status_detects_install(tmp_path):
    cp = _cp()
    proj = tmp_path / "proj"
    proj.mkdir()
    assert cp.handoff_status(str(proj))["installed"] is False
    cp.install_handoff(str(proj))
    st = cp.handoff_status(str(proj))
    assert st["installed"] is True
    assert st["has_handoff"] is True


def test_continue_prompt_mentions_handoff():
    cp = _cp()
    assert "HANDOFF.md" in cp.continue_prompt("/tmp/proj")
