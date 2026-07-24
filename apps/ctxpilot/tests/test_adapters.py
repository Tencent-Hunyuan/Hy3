"""Tests for agent adapters (open / codex) using fixture session files."""
from __future__ import annotations

from pathlib import Path

from ctxpilot.adapters.base import discover_adapters, get_adapter, list_adapters
from ctxpilot.adapters.codex import CodexAdapter
from ctxpilot.adapters.opencode import OpenCodeAdapter

FIX = Path(__file__).parent / "fixtures"


def test_registry_discovers_both():
    discover_adapters()
    names = list_adapters()
    assert "opencode" in names
    assert "codex" in names


def test_get_adapter_returns_instance():
    ad = get_adapter("opencode")
    assert isinstance(ad, OpenCodeAdapter)
    assert get_adapter("codex").name == "codex"


def test_opencode_parse_session():
    tr = OpenCodeAdapter().parse_session(FIX / "opencode_session.json")
    assert tr.agent == "opencode"
    assert tr.session_id == "sess-opencode-001"
    # content parts get flattened, tool calls recorded
    assert any("facade" in m.content for m in tr.messages)
    assert "src/ctxpilot/core.py" in tr.files_touched
    assert "README.md" in tr.files_touched
    assert tr.started_at == "2026-07-15T10:00:00Z"


def test_codex_parse_session():
    tr = CodexAdapter().parse_session(FIX / "codex_rollout.jsonl")
    assert tr.agent == "codex"
    # user + assistant messages parsed from parts
    roles = [m.role for m in tr.messages]
    assert "user" in roles and "assistant" in roles
    assert any("return sum(xs)" in m.content for m in tr.messages)
    # tool calls captured as assistant messages + file tracking
    assert "src/calc.py" in tr.files_touched
    assert any(m.role == "assistant" and m.content.startswith("[shell]") for m in tr.messages)


def test_codex_captures_cwd_from_session_meta(tmp_path):
    """Real Codex logs put cwd inside {"type":"session_meta","payload":{"cwd":...}}.
    This is what lets the dashboard auto-place the session under its project dir."""
    f = tmp_path / "rollout-x.jsonl"
    f.write_text(
        "\n".join(
            [
                '{"type":"session_meta","payload":{"id":"abc-123","cwd":"C:\\\\projects\\\\demo","cli_version":"0.121.0"}}',
                '{"type":"response_item","payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"hi"}]}}',
                '{"type":"response_item","payload":{"type":"function_call","name":"edit","arguments":"C:\\\\projects\\\\demo\\\\src\\\\a.py"}}',
            ]
        ),
        encoding="utf-8",
    )
    tr = CodexAdapter().parse_session(f)
    assert tr.project_path == "C:\\projects\\demo"
    assert tr.session_id == "abc-123"
    # absolute file path under cwd should be tracked
    assert "C:\\projects\\demo\\src\\a.py" in tr.files_touched
