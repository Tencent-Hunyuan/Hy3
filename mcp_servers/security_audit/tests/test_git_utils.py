"""Tests for git_utils: read_diff / read_file_text against REAL git repos.

No mocking of subprocess — every test builds an actual throwaway repo in
tmp_path (via the `git_repo` fixture) and shells out to the real `git` binary,
so these prove the module against git's actual behavior/output format.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hy3_security_mcp import git_utils
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


class TestReadDiffNoCodeExecution:
    """`review_diff`'s stated purpose is pointing at UNTRUSTED repos, so a
    repo-local diff driver must never be honored: `git diff` supports
    `diff.external` / textconv drivers configured in the repo's own
    `.git/config`, which are arbitrary shell commands git runs during a diff.
    read_diff must run with those disabled (--no-ext-diff/--no-textconv,
    -c diff.external=, GIT_EXTERNAL_DIFF cleared) so no code runs (RCE)."""

    def _dirty_repo(self, repo: Path) -> None:
        (repo / "app.py").write_text("v1\n")
        _commit_all(repo, "initial")
        (repo / "app.py").write_text("v2\n")  # unstaged diff to trigger a driver

    def test_repo_local_diff_external_driver_is_not_executed(self, git_repo: Path) -> None:
        marker = git_repo / "pwned_by_diff_external"
        self._dirty_repo(git_repo)
        # A malicious untrusted repo sets diff.external to an arbitrary command.
        run_git(["config", "diff.external", f"touch {marker}"], git_repo)

        read_diff(str(git_repo))

        assert not marker.exists(), "diff.external driver executed → RCE"

    def test_git_external_diff_env_var_is_not_honored(
        self, git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        marker = tmp_path / "pwned_by_env"
        self._dirty_repo(git_repo)
        # GIT_EXTERNAL_DIFF in the ambient env is the same RCE via inheritance.
        monkeypatch.setenv("GIT_EXTERNAL_DIFF", f"touch {marker}")

        read_diff(str(git_repo))

        assert not marker.exists(), "GIT_EXTERNAL_DIFF honored → RCE"

    def test_textconv_driver_is_not_executed(self, git_repo: Path) -> None:
        marker = git_repo / "pwned_by_textconv"
        self._dirty_repo(git_repo)
        # A textconv driver is likewise an arbitrary command git runs per-file.
        (git_repo / ".gitattributes").write_text("*.py diff=evil\n")
        run_git(["config", "diff.evil.textconv", f"touch {marker} && cat"], git_repo)

        read_diff(str(git_repo))

        assert not marker.exists(), "textconv driver executed → RCE"

    def test_repo_local_fsmonitor_hook_is_not_executed(self, git_repo: Path) -> None:
        # core.fsmonitor set to a non-boolean value is a hook program git runs
        # when it refreshes the index during `git diff` — arbitrary command RCE.
        marker = git_repo / "pwned_by_fsmonitor"
        self._dirty_repo(git_repo)
        run_git(["config", "core.fsmonitor", f"touch {marker}; false"], git_repo)

        read_diff(str(git_repo))

        assert not marker.exists(), "core.fsmonitor hook executed → RCE"

    def test_repo_local_filter_clean_is_not_executed(self, git_repo: Path) -> None:
        # filter.<name>.clean is an arbitrary command git runs to normalize
        # working-tree content into its index form; a working-tree diff of a
        # path routed to the filter via .gitattributes executes it → RCE.
        marker = git_repo / "pwned_by_filter_clean"
        (git_repo / "data.txt").write_text("v1\n")
        _commit_all(git_repo, "initial")
        (git_repo / ".gitattributes").write_text("*.txt filter=evil\n")
        run_git(["config", "filter.evil.clean", f"touch {marker}; cat"], git_repo)
        (git_repo / "data.txt").write_text("v2\n")  # unstaged change triggers clean

        read_diff(str(git_repo))

        assert not marker.exists(), "filter.<name>.clean executed → RCE"

    def test_timeout_expired_becomes_git_error(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise_timeout(*_args: object, **_kwargs: object) -> None:
            raise subprocess.TimeoutExpired(cmd="git diff", timeout=0.01)

        monkeypatch.setattr(git_utils.subprocess, "run", _raise_timeout)

        with pytest.raises(GitError):
            read_diff(str(git_repo), timeout=0.01)


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
