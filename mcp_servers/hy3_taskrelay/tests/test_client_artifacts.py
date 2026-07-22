"""Regression checks for sanitized real-client evidence."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from hy3_taskrelay.schemas import AuditResult, Checkpoint, ResumeBrief

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = PROJECT_ROOT / "docs" / "client_artifacts"
CLIENTS = PROJECT_ROOT / "docs" / "clients"
DEMO = PROJECT_ROOT / "docs" / "demo"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_real_client_artifacts_are_valid_and_linked() -> None:
    checkpoint = Checkpoint.model_validate(
        _load_json(ARTIFACTS / "codebuddy_checkpoint_2026-07-20.json")
    )
    audit = AuditResult.model_validate(_load_json(ARTIFACTS / "codex_audit_2026-07-20.json"))
    resume = ResumeBrief.model_validate(_load_json(ARTIFACTS / "codex_resume_2026-07-20.json"))

    assert checkpoint.checkpoint_id == audit.checkpoint_id == resume.checkpoint_id
    assert audit.overall_status == "clean"
    assert [step.priority for step in resume.next_steps] == [1, 2]


def test_client_records_match_the_validated_artifacts() -> None:
    codebuddy = _load_json(CLIENTS / "codebuddy_2026-07-20.json")
    codex = _load_json(CLIENTS / "codex_2026-07-20.json")

    assert codebuddy["exit_code"] == codex["exit_code"] == 0
    assert codebuddy["result"]["checkpoint_id"] == codex["input_checkpoint_id"]
    assert [call["status"] for call in codex["mcp_calls"]] == ["completed", "completed"]
    assert codebuddy["security"]["credentials_recorded"] is False
    assert codex["security"]["credentials_recorded"] is False


def test_actual_call_demo_is_bounded_and_rendered_from_current_records() -> None:
    for name in (
        "codebuddy_actual_call.png",
        "codex_actual_calls.png",
        "codebuddy_checkpoint.png",
        "codex_audit_resume.png",
    ):
        with Image.open(DEMO / name) as screenshot:
            assert screenshot.size == (1280, 720)

    with Image.open(DEMO / "taskrelay_cross_client.gif") as animation:
        durations = []
        for frame in range(animation.n_frames):
            animation.seek(frame)
            durations.append(animation.info["duration"])
        assert animation.size == (1280, 720)
        assert animation.n_frames == 6
        assert sum(durations) == 13_200
