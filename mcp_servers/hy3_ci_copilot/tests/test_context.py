from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import hy3_ci_copilot.context as context_module
from hy3_ci_copilot.context import (
    PathPolicy,
    git_context,
    parse_workflow,
    read_text_excerpt,
    repository_context,
    signal_diff,
)
from hy3_ci_copilot.errors import AccessDeniedError, InputFileError


def test_path_policy_accepts_repository_files(repository: Path) -> None:
    policy = PathPolicy((repository,))

    assert policy.file("failed.log", repository) == repository / "failed.log"


def test_path_policy_rejects_parent_and_git_files(repository: Path, tmp_path: Path) -> None:
    policy = PathPolicy((repository,))
    outside = tmp_path.parent / "outside.log"
    outside.write_text("secret", encoding="utf-8")
    (repository / ".git").mkdir()
    (repository / ".git" / "config").write_text("config", encoding="utf-8")

    with pytest.raises(AccessDeniedError):
        policy.file(str(outside), repository)
    with pytest.raises(AccessDeniedError, match=r"\.git"):
        policy.file(".git/config", repository)
    with pytest.raises(AccessDeniedError, match=r"\.git"):
        policy.repository(str(repository / ".git"))


def test_path_policy_rejects_case_insensitive_git_name(repository: Path) -> None:
    metadata = repository / ".GIT"
    metadata.mkdir()
    (metadata / "config").write_text("secret", encoding="utf-8")

    with pytest.raises(AccessDeniedError, match=r"\.git"):
        PathPolicy((repository,)).file(".GIT/config", repository)


def test_path_policy_rejects_git_symlink_to_internal_directory(repository: Path) -> None:
    metadata = repository / "metadata"
    metadata.mkdir()
    (metadata / "config").write_text("secret", encoding="utf-8")
    try:
        (repository / ".git").symlink_to(metadata, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are not available on this platform")
    policy = PathPolicy((repository,))

    with pytest.raises(AccessDeniedError, match=r"\.git"):
        policy.file(".git/config", repository)
    with pytest.raises(AccessDeniedError, match=r"\.git"):
        policy.repository(str(repository / ".git"))


def test_path_policy_rejects_symlink_escape(repository: Path, tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-target.log"
    outside.write_text("secret", encoding="utf-8")
    link = repository / "linked.log"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks are not available on this platform")

    with pytest.raises(AccessDeniedError):
        PathPolicy((repository,)).file("linked.log", repository)


def test_binary_and_empty_files_are_rejected(repository: Path) -> None:
    binary = repository / "binary.log"
    binary.write_bytes(b"prefix" + (b"x" * 9000) + b"\x00suffix")
    empty = repository / "empty.log"
    empty.touch()

    with pytest.raises(InputFileError, match="Binary"):
        read_text_excerpt(binary, repository, 10_000)
    with pytest.raises(InputFileError, match="empty"):
        read_text_excerpt(empty, repository, 10_000)


def test_workflow_parser_preserves_on_key_and_jobs() -> None:
    result = parse_workflow("on: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n")

    assert "on" in result["top_level_keys"]
    assert result["jobs"] == ["test"]


def test_workflow_aliases_are_supported() -> None:
    workflow = "defaults: &defaults\n  runs-on: ubuntu-latest\njobs:\n  test: *defaults\n"

    result = parse_workflow(workflow)

    assert result["jobs"] == ["test"]


def test_workflow_alias_count_is_bounded() -> None:
    jobs = "\n".join(f"  test-{index}: *defaults" for index in range(101))
    workflow = f"defaults: &defaults\n  runs-on: ubuntu-latest\njobs:\n{jobs}\n"

    with pytest.raises(InputFileError, match="too many aliases"):
        parse_workflow(workflow)


def test_signal_diff_highlights_failed_only_errors() -> None:
    diff = signal_diff("test passed\n", "test failed\nERROR dependency missing\n")

    assert "+test failed" in diff
    assert "+ERROR dependency missing" in diff


def test_git_environment_cannot_redirect_repository(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    outside = tmp_path / "outside"
    outside.mkdir()
    for path, message in ((repository, "INSIDE_COMMIT"), (outside, "OUTSIDE_SECRET")):
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
        subprocess.run(
            ["git", "-C", str(path), "config", "user.email", "test@example.test"],
            check=True,
        )
        (path / "tracked.txt").write_text(message, encoding="utf-8")
        subprocess.run(["git", "-C", str(path), "add", "tracked.txt"], check=True)
        subprocess.run(["git", "-C", str(path), "commit", "-qm", message], check=True)

    monkeypatch.setenv("GIT_DIR", str(outside / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(outside))

    context = git_context(repository)

    assert "INSIDE_COMMIT" in context["recent_commits"]
    assert "OUTSIDE_SECRET" not in str(context)


def test_git_context_rejects_external_object_alternates(tmp_path: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    outside = tmp_path / "outside"
    repository = tmp_path / "repository"
    outside.mkdir()
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(outside)], check=True)
    subprocess.run(["git", "-C", str(outside), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(outside), "config", "user.email", "test@example.test"],
        check=True,
    )
    (outside / "tracked.txt").write_text("secret", encoding="utf-8")
    subprocess.run(["git", "-C", str(outside), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(outside), "commit", "-qm", "OUTSIDE_SECRET_COMMIT"],
        check=True,
    )
    outside_commit = subprocess.run(
        ["git", "-C", str(outside), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    object_info = repository / ".git" / "objects" / "info"
    object_info.mkdir(parents=True, exist_ok=True)
    (object_info / "alternates").write_text(
        str(outside / ".git" / "objects") + "\n", encoding="utf-8"
    )
    (repository / ".git" / "refs" / "heads" / "main").write_text(
        outside_commit + "\n", encoding="utf-8"
    )
    (repository / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    context = git_context(repository, allowed_roots=(repository,))

    assert set(context.values()) == {"unavailable"}
    assert "OUTSIDE_SECRET_COMMIT" not in str(context)


def test_git_context_rejects_external_common_directory(tmp_path: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    outside = tmp_path / "outside"
    repository = tmp_path / "repository"
    subprocess.run(["git", "init", "-q", str(outside)], check=True)
    repository.mkdir()
    metadata = repository / ".git"
    metadata.mkdir()
    (metadata / "commondir").write_text(str(outside / ".git") + "\n", encoding="utf-8")

    context = git_context(repository, allowed_roots=(repository,))

    assert set(context.values()) == {"unavailable"}


def test_git_context_rejects_metadata_symlinks(tmp_path: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    repository = tmp_path / "repository"
    outside = tmp_path / "outside-objects"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    outside.mkdir()
    objects = repository / ".git" / "objects"
    shutil.rmtree(objects)
    try:
        objects.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are not available on this platform")

    context = git_context(repository, allowed_roots=(repository,))

    assert set(context.values()) == {"unavailable"}


def test_git_context_does_not_execute_repository_filters(tmp_path: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "test@example.test"],
        check=True,
    )
    tracked = repository / "tracked.txt"
    tracked.write_text("original", encoding="utf-8")
    (repository / ".gitattributes").write_text("*.txt filter=evil\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "SAFE_COMMIT"], check=True)

    marker = tmp_path / "filter-executed"
    filter_script = repository / "filter.py"
    filter_script.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).touch()\n"
        "import sys\n"
        "sys.stdout.buffer.write(sys.stdin.buffer.read())\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "config",
            "filter.evil.clean",
            f'"{sys.executable}" "{filter_script}"',
        ],
        check=True,
    )
    tracked.write_text("modified", encoding="utf-8")

    context = git_context(repository, allowed_roots=(repository,))

    assert context["status"] == "unavailable"
    assert "SAFE_COMMIT" in context["recent_commits"]
    assert not marker.exists()


def test_git_context_disables_replacement_refs(tmp_path: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "test@example.test"],
        check=True,
    )
    tracked = repository / "tracked.txt"
    tracked.write_text("original", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-qm", "ORIGINAL_SUBJECT"], check=True
    )
    original_commit = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tracked.write_text("replacement", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-qm", "REPLACEMENT_SUBJECT"], check=True
    )
    replacement_commit = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(repository), "replace", original_commit, replacement_commit],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "reset", "--hard", "-q", original_commit], check=True
    )

    context = git_context(repository, allowed_roots=(repository,))

    assert "ORIGINAL_SUBJECT" in context["recent_commits"]
    assert "REPLACEMENT_SUBJECT" not in context["recent_commits"]


def test_git_context_rejects_config_includes(tmp_path: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    external_config = tmp_path / "external-config"
    external_config.write_text("[core]\n\tpager = cat\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repository), "config", "include.path", str(external_config)],
        check=True,
    )

    context = git_context(repository, allowed_roots=(repository,))

    assert set(context.values()) == {"unavailable"}


def test_git_context_rejects_external_mailmap_config(tmp_path: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "mailmap.file", str(tmp_path / "mailmap")],
        check=True,
    )

    context = git_context(repository, allowed_roots=(repository,))

    assert set(context.values()) == {"unavailable"}


def test_git_metadata_scan_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    repository = tmp_path / "repository"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    monkeypatch.setattr(context_module, "_MAX_GIT_METADATA_ENTRIES", 1)

    context = git_context(repository, allowed_roots=(repository,))

    assert set(context.values()) == {"unavailable"}


def test_repository_context_bounds_git_metadata(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repository / ".git").mkdir()
    monkeypatch.setattr(
        "hy3_ci_copilot.context._run_git",
        lambda *_args, **_kwargs: "x" * 20_000,
    )

    context = repository_context(repository, 2000)

    assert sum(len(value) for value in context["git"].values()) <= 400


def test_supplemental_context_skips_symlink_to_git_metadata(repository: Path) -> None:
    metadata = repository / ".git"
    metadata.mkdir()
    (metadata / "config").write_text("SECRET_GIT_CONFIG", encoding="utf-8")
    requirements = repository / "requirements.txt"
    try:
        requirements.symlink_to(metadata / "config")
    except OSError:
        pytest.skip("Symlinks are not available on this platform")

    context = repository_context(repository, 10_000)

    assert "SECRET_GIT_CONFIG" not in str(context)
    assert all(item["path"] != ".git/config" for item in context["files"])


def test_supplemental_context_skips_symlink_to_private_file(repository: Path) -> None:
    private_file = repository / ".env"
    private_file.write_text("PRIVATE_VALUE=do-not-upload", encoding="utf-8")
    requirements = repository / "requirements.txt"
    try:
        requirements.symlink_to(private_file)
    except OSError:
        pytest.skip("Symlinks are not available on this platform")

    context = repository_context(repository, 10_000)

    assert "do-not-upload" not in str(context)


def test_supplemental_context_skips_symlinked_workflow_directory(repository: Path) -> None:
    workflow_dir = repository / ".github" / "workflows"
    (workflow_dir / "ci.yml").unlink()
    workflow_dir.rmdir()
    private_dir = repository / "private-workflows"
    private_dir.mkdir()
    (private_dir / "secret.yml").write_text("marker: SYMLINKED_PRIVATE_MARKER", encoding="utf-8")
    try:
        workflow_dir.symlink_to(private_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are not available on this platform")

    context = repository_context(repository, 10_000)

    assert "SYMLINKED_PRIVATE_MARKER" not in str(context)


def test_git_context_handles_non_utf8_commit_message(repository: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "test@example.test"],
        check=True,
    )
    (repository / "tracked.txt").write_text("content", encoding="utf-8")
    message_file = repository / "commit-message.bin"
    message_file.write_bytes(b"bad \xff subject")
    subprocess.run(["git", "-C", str(repository), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-q", "-F", str(message_file)],
        check=True,
    )

    context = git_context(repository)

    assert "bad" in context["recent_commits"]
    assert "subject" in context["recent_commits"]


def test_git_context_supports_allowed_linked_worktree(tmp_path: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    main = tmp_path / "main"
    worktree = tmp_path / "worktree"
    main.mkdir()
    subprocess.run(["git", "init", "-q", str(main)], check=True)
    subprocess.run(["git", "-C", str(main), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(main), "config", "user.email", "test@example.test"],
        check=True,
    )
    (main / "tracked.txt").write_text("content", encoding="utf-8")
    subprocess.run(["git", "-C", str(main), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(main), "commit", "-qm", "WORKTREE_COMMIT"], check=True)
    subprocess.run(
        ["git", "-C", str(main), "worktree", "add", "-qb", "test-worktree", str(worktree)],
        check=True,
    )

    context = git_context(worktree, allowed_roots=(tmp_path,))
    restricted = git_context(worktree, allowed_roots=(worktree,))

    assert "WORKTREE_COMMIT" in context["recent_commits"]
    assert set(restricted.values()) == {"unavailable"}


def test_git_context_supports_allowed_submodule_gitfile(tmp_path: Path) -> None:
    if not shutil.which("git"):
        pytest.skip("git is not installed")

    source = tmp_path / "source"
    superproject = tmp_path / "superproject"
    source.mkdir()
    superproject.mkdir()
    for repository in (source, superproject):
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test"], check=True)
        subprocess.run(
            ["git", "-C", str(repository), "config", "user.email", "test@example.test"],
            check=True,
        )

    (source / "tracked.txt").write_text("content", encoding="utf-8")
    subprocess.run(["git", "-C", str(source), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(source), "commit", "-qm", "SUBMODULE_COMMIT"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "protocol.file.allow=always",
            "-C",
            str(superproject),
            "submodule",
            "add",
            "-q",
            str(source),
            "module",
        ],
        check=True,
    )

    submodule = superproject / "module"
    context = git_context(submodule, allowed_roots=(superproject,))
    restricted = git_context(submodule, allowed_roots=(submodule,))

    assert (submodule / ".git").is_file()
    assert "SUBMODULE_COMMIT" in context["recent_commits"]
    assert set(restricted.values()) == {"unavailable"}
