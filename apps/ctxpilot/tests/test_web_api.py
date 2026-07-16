"""Web API tests via FastAPI TestClient with injected fake Hy3 + fake adapter."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from ctxpilot.config import Config
from ctxpilot.models import SessionTranscript
from ctxpilot.web.api import create_app

from conftest import FakeHy3, SAMPLE_MARKDOWN, make_raw

DRIFT_TEXT = "red|loop|retrying same edit"


class FakeAdapter:
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


def _client(responses=None, adapters=None):
    cfg = Config(hy3_api_key="k", hy3_base_url="http://x", hy3_model="hy3")
    return TestClient(create_app(config=cfg, hy3=FakeHy3(responses or [SAMPLE_MARKDOWN]), adapters=adapters))


def _fake_sessions(tmp_path):
    f = tmp_path / "s.json"
    f.write_text("{}", encoding="utf-8")
    t = SessionTranscript(agent="fake", session_id="s.json", project_path=str(tmp_path))
    return [(f, t)]


def test_scan_endpoint(tmp_path):
    c = _client(adapters=[FakeAdapter(_fake_sessions(tmp_path))])
    r = c.get("/scan")
    assert r.status_code == 200
    paths = [p["path"] for p in r.json()["projects"]]
    assert any(str(tmp_path).lower() in p.lower() for p in paths)


def test_events_endpoint(tmp_path):
    c = _client(adapters=[FakeAdapter(_fake_sessions(tmp_path))])
    r = c.get("/events")
    assert r.status_code == 200
    assert "events" in r.json()


def test_config_post_updates_credentials(tmp_path, monkeypatch):
    # isolate the on-disk store to a temp location
    store = tmp_path / "config.json"
    monkeypatch.setattr("ctxpilot.config._CONFIG_FILE", store)
    c = _client()
    r = c.post("/config", json={"api_key": "sk-demo", "base_url": "http://h", "model": "hy3"})
    assert r.json()["has_credentials"] is True
    # key must NOT be echoed back
    cfg = c.get("/config").json()
    assert "sk-demo" not in json.dumps(cfg)
    # it was persisted
    assert "sk-demo" in store.read_text(encoding="utf-8")


def test_projects_add_endpoint(tmp_path):
    c = _client()
    r = c.post("/projects/add", json={"project_path": str(tmp_path)})
    assert str(tmp_path) in r.json()["project_roots"]


def test_agents_endpoint(tmp_path):
    c = _client(adapters=[FakeAdapter(_fake_sessions(tmp_path))])
    r = c.get("/agents")
    assert r.status_code == 200
    agents = r.json()["agents"]
    assert agents[0]["name"] == "fake"
    assert agents[0]["session_count"] == 1


def test_monitor_status_endpoint(tmp_path):
    c = _client(adapters=[FakeAdapter(_fake_sessions(tmp_path))])
    r = c.get("/monitor/status")
    assert r.status_code == 200
    st = r.json()
    assert st["running"] is False
    assert "fake" in st["agents_watched"]
    assert st["known_sessions"] == 1


def test_config_test_endpoint():
    c = _client()
    r = c.post("/config/test", json={})  # no overrides -> uses configured (fake) client
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_health():
    c = _client()
    assert c.get("/health").json()["status"] == "ok"


def test_snapshot_endpoint():
    c = _client()
    r = c.post("/snapshot", json={"project_path": "/tmp/proj"})
    assert r.status_code == 200
    body = r.json()
    assert "Ship MVP" in body["goals"]
    assert body["written_to"].endswith("HANDOFF.md")


def test_brief_endpoint():
    c = _client([SAMPLE_MARKDOWN, "brief from hy3"])
    r = c.post("/brief", json={"project_path": "/tmp/proj"})
    assert r.json()["brief"] == "brief from hy3"


def test_export_then_import_endpoint(tmp_path):
    c = _client()
    exp = c.post("/export", json={"project_path": "/tmp/proj"}).json()
    assert exp["snapshot"]["goals"]
    # write a handoff json and import it
    f = tmp_path / "h.json"
    f.write_text(__import__("json").dumps(exp), encoding="utf-8")
    r = c.post("/import", json={"project_path": str(f), "target_agent": "codex"})
    assert "CONTEXT HANDOFF" in r.json()["prompt"]


def test_watch_endpoint():
    c = _client([SAMPLE_MARKDOWN, DRIFT_TEXT])
    # snapshot consumes first
    c.post("/snapshot", json={"project_path": "/tmp/proj"})
    r = c.post("/watch", json={"project_path": "/tmp/proj"})
    assert r.json()["signals"][0]["severity"] == "red"


def test_savings_endpoint():
    c = _client()
    r = c.post("/savings", json={"project_path": "/tmp/proj"})
    assert r.json()["saved_tokens"] > 0


def test_install_endpoint_writes_marker(tmp_path):
    c = _client()
    proj = tmp_path / "proj"
    proj.mkdir()
    r = c.post("/install", json={"project_path": str(proj)})
    assert r.status_code == 200
    body = r.json()
    assert body["installed"] is True
    assert (proj / "AGENTS.md").exists()
    assert "<!-- ctxpilot:handoff -->" in (proj / "AGENTS.md").read_text(encoding="utf-8")
    assert body["handoff_generated"] is True


def test_continue_prompt_endpoint():
    c = _client()
    r = c.post("/continue-prompt", json={"project_path": "/tmp/proj"})
    assert "HANDOFF.md" in r.json()["prompt"]


def test_handoff_statuses_endpoint(tmp_path):
    c = _client()
    proj = tmp_path / "proj"
    proj.mkdir()
    # before install
    r0 = c.post("/handoff-statuses", json={"paths": [str(proj)]})
    assert r0.json()["statuses"][str(proj)]["installed"] is False
    # install, then re-check
    c.post("/install", json={"project_path": str(proj)})
    r1 = c.post("/handoff-statuses", json={"paths": [str(proj)]})
    st = r1.json()["statuses"][str(proj)]
    assert st["installed"] is True
    assert st["has_handoff"] is True
