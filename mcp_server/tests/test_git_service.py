import subprocess
from pathlib import Path

import pytest

from hy3_code_review_mcp.git_service import GitService, GitServiceError


def _git(repository: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repository), *args], check=True, capture_output=True)


def test_collect_provided_diff_and_truncate(tmp_path: Path) -> None:
    service = GitService(tmp_path, max_diff_chars=10)

    result = service.collect_diff(source="provided", provided_diff="0123456789abcdef")

    assert result.truncated is True
    assert result.original_chars == 16
    assert result.content.startswith("0123456789")
    assert "TRUNCATED" in result.content


def test_omit_sensitive_file_sections(tmp_path: Path) -> None:
    service = GitService(tmp_path, max_diff_chars=10_000)
    diff = """diff --git a/.env b/.env
--- a/.env
+++ b/.env
@@ -1 +1 @@
-TOKEN=old
+TOKEN=secret
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-value = 1
+value = 2
"""

    result = service.collect_diff(source="provided", provided_diff=diff)

    assert "TOKEN=secret" not in result.content
    assert "SENSITIVE FILE DIFF OMITTED: .env" in result.content
    assert "+value = 2" in result.content


def test_collect_working_tree_diff(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    file_path = tmp_path / "example.py"
    file_path.write_text("value = 1\n")
    _git(tmp_path, "add", "example.py")
    _git(tmp_path, "commit", "-m", "initial")
    file_path.write_text("value = 2\n")
    service = GitService(tmp_path, max_diff_chars=10_000)

    result = service.collect_diff(source="working_tree")

    assert "-value = 1" in result.content
    assert "+value = 2" in result.content
    assert result.truncated is False


def test_collect_staged_diff(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    file_path = tmp_path / "example.py"
    file_path.write_text("value = 1\n")
    _git(tmp_path, "add", "example.py")
    _git(tmp_path, "commit", "-m", "initial")
    file_path.write_text("value = 2\n")
    _git(tmp_path, "add", "example.py")
    service = GitService(tmp_path, max_diff_chars=10_000)

    result = service.collect_diff(source="staged")

    assert "+value = 2" in result.content
    assert result.source == "staged"


def test_collect_diff_between_refs(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    file_path = tmp_path / "example.py"
    file_path.write_text("value = 1\n")
    _git(tmp_path, "add", "example.py")
    _git(tmp_path, "commit", "-m", "initial")
    first_commit = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    file_path.write_text("value = 3\n")
    _git(tmp_path, "add", "example.py")
    _git(tmp_path, "commit", "-m", "change")
    service = GitService(tmp_path, max_diff_chars=10_000)

    result = service.collect_diff(source="refs", base_ref=first_commit, target_ref="HEAD")

    assert "+value = 3" in result.content
    assert result.source == "refs"


def test_reject_empty_diff(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    service = GitService(tmp_path, max_diff_chars=100)

    with pytest.raises(GitServiceError, match="selected diff is empty"):
        service.collect_diff(source="working_tree")


def test_reject_repository_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    service = GitService(workspace, max_diff_chars=100)

    with pytest.raises(GitServiceError, match="inside HY3_WORKSPACE_ROOT"):
        service.collect_diff(repository_path=str(outside), source="working_tree")


def test_reject_option_like_ref(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    service = GitService(tmp_path, max_diff_chars=100)

    with pytest.raises(GitServiceError, match="safe Git reference"):
        service.collect_diff(source="refs", base_ref="--output=/tmp/file")


def test_git_timeout_has_actionable_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service = GitService(tmp_path, max_diff_chars=100)

    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="git", timeout=30)

    monkeypatch.setattr(subprocess, "run", timeout)

    with pytest.raises(GitServiceError) as caught:
        service.collect_diff(source="working_tree")

    assert caught.value.code == "GIT_TIMEOUT"
    assert caught.value.retryable is True
    assert "retry" in caught.value.suggested_action.lower()
