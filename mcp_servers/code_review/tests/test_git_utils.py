import subprocess
from pathlib import Path

from hy3_code_review_mcp.git_utils import get_git_diff, truncate_text


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_get_git_diff_reads_worktree_diff(tmp_path: Path):
    run(["git", "init"], tmp_path)
    run(["git", "config", "user.email", "test@example.com"], tmp_path)
    run(["git", "config", "user.name", "Test User"], tmp_path)

    source = tmp_path / "app.py"
    source.write_text("print('old')\n", encoding="utf-8")
    run(["git", "add", "app.py"], tmp_path)
    run(["git", "commit", "-m", "initial"], tmp_path)
    source.write_text("print('new')\n", encoding="utf-8")

    diff = get_git_diff(repo_path=str(tmp_path), base_ref="HEAD")

    assert "diff --git a/app.py b/app.py" in diff
    assert "-print('old')" in diff
    assert "+print('new')" in diff


def test_truncate_text_preserves_prefix_and_reports_original_size():
    text = "abcdef"

    assert truncate_text(text, max_chars=4) == "abcd\n\n[truncated: original 6 chars]"
