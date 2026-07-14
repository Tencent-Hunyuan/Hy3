from pathlib import Path

import pytest

from hy3_code_review_mcp.git_service import GitServiceError
from hy3_code_review_mcp.smoke_test import load_diff


def test_smoke_test_uses_builtin_diff(tmp_path: Path) -> None:
    diff = load_diff(None, tmp_path)

    assert "diff --git" in diff
    assert "SELECT id FROM users" in diff


def test_smoke_test_loads_workspace_file(tmp_path: Path) -> None:
    diff_file = tmp_path / "change.diff"
    diff_file.write_text("diff --git a/a.py b/a.py\n+x = 1\n")

    assert load_diff("change.diff", tmp_path) == diff_file.read_text()


def test_smoke_test_rejects_file_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.diff"
    outside.write_text("diff")

    with pytest.raises(GitServiceError, match="inside HY3_WORKSPACE_ROOT"):
        load_diff(str(outside), workspace)
