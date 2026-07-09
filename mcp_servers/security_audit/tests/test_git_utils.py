"""Tests for git_utils: read_diff / read_file_text against REAL git repos.

No mocking of subprocess — every test builds an actual throwaway repo in
tmp_path (via the `git_repo` fixture) and shells out to the real `git` binary,
so these prove the module against git's actual behavior/output format.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hy3_security_mcp.git_utils import GitError, read_diff, read_file_text
from tests.conftest import run_git


def _commit_all(repo: Path, message: str) -> None:
    run_git(["add", "-A"], repo)
    run_git(["commit", "-m", message], repo)


class TestReadDiff:
    def test_unstaged_diff_contains_the_change(self, git_repo: Path) -> None:
        (git_repo / "app.py").write_text("print('hello')\n")
        _commit_all(git_repo, "initial")

        (git_repo / "app.py").write_text("print('modified')\n")

        diff = read_diff(str(git_repo))

        assert "-print('hello')" in diff
        assert "+print('modified')" in diff

    def test_staged_shows_only_staged_changes(self, git_repo: Path) -> None:
        (git_repo / "a.py").write_text("a = 1\n")
        (git_repo / "b.py").write_text("b = 1\n")
        _commit_all(git_repo, "initial")

        (git_repo / "a.py").write_text("a = 2\n")
        run_git(["add", "a.py"], git_repo)
        (git_repo / "b.py").write_text("b = 2\n")  # left unstaged

        diff = read_diff(str(git_repo), staged=True)

        assert "a.py" in diff
        assert "b.py" not in diff

    def test_ref_range_head_tilde_1_to_head(self, git_repo: Path) -> None:
        (git_repo / "app.py").write_text("v1\n")
        _commit_all(git_repo, "first")
        (git_repo / "app.py").write_text("v2\n")
        _commit_all(git_repo, "second")

        diff = read_diff(str(git_repo), ref_range="HEAD~1..HEAD")

        assert "-v1" in diff
        assert "+v2" in diff

    def test_empty_diff_returns_empty_string(self, git_repo: Path) -> None:
        (git_repo / "app.py").write_text("v1\n")
        _commit_all(git_repo, "first")

        assert read_diff(str(git_repo)) == ""

    def test_non_repo_dir_raises_git_error_with_stderr(self, tmp_path: Path) -> None:
        plain_dir = tmp_path / "not_a_repo"
        plain_dir.mkdir()

        with pytest.raises(GitError) as exc_info:
            read_diff(str(plain_dir))

        assert "not a git repository" in str(exc_info.value).lower()

    def test_staged_and_ref_range_together_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            read_diff(".", staged=True, ref_range="HEAD~1..HEAD")

    def test_ref_range_starting_with_dash_is_rejected_before_git_runs(self, git_repo: Path) -> None:
        # A ref_range like "--output=<path>" would otherwise be interpreted by
        # git as an option (argument smuggling — e.g. writing a file). It must
        # be rejected with ValueError before the value ever reaches the git
        # argv, so the smuggled file is never created.
        smuggled = git_repo / "smuggled_output"

        with pytest.raises(ValueError):
            read_diff(str(git_repo), ref_range=f"--output={smuggled}")

        assert not smuggled.exists()


class TestReadFileText:
    def test_reads_short_file_verbatim(self, tmp_path: Path) -> None:
        file_path = tmp_path / "small.txt"
        file_path.write_text("hello world")

        assert read_file_text(str(file_path)) == "hello world"

    def test_truncates_long_file_with_marker(self, tmp_path: Path) -> None:
        file_path = tmp_path / "big.txt"
        file_path.write_text("x" * 100)

        result = read_file_text(str(file_path), max_chars=10)

        assert result == "x" * 10 + "\n…[截断 truncated]"

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_file_text(str(tmp_path / "missing.txt"))
