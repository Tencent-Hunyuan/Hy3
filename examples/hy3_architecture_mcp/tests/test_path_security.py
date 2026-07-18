"""Security tests for analyze_project_context sandbox isolation.

These exercise the pure file-reading helpers directly (no Hy3 network calls).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hy3_architecture_mcp.config import Settings
from hy3_architecture_mcp.exceptions import (
    ConfigurationError,
    FileTooLargeError,
    WorkspaceAccessError,
)
from hy3_architecture_mcp.tools.project_context import (
    collect_context,
    is_allowed_extension,
    is_denied_name,
    resolve_within_workspace,
)


def settings_for(root: Path, *, max_file=1024, max_total=4096) -> Settings:
    return Settings(
        workspace_root=root,
        max_file_size_bytes=max_file,
        max_total_size_bytes=max_total,
    )


def create_real_symlink(target: Path, link: Path) -> None:
    """Create a symlink, skipping the test if real symlinks are unavailable.

    On some Windows configurations ``os.symlink`` returns without error yet
    produces a *non-functional* pseudo-link (``is_symlink()`` is False, the
    link does not resolve to its target). Such a link cannot be used to escape
    the workspace, so the security behaviour under test is not exercisable —
    we skip rather than report a false failure.
    """
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform/permission")
    if not link.is_symlink():
        pytest.skip(
            "os.symlink produced a non-functional link "
            "(common on Windows without Developer Mode); cannot exercise symlink escape"
        )


# --- helpers --------------------------------------------------------------


def test_allowed_extensions():
    assert is_allowed_extension(Path("a.py"))
    assert is_allowed_extension(Path("b.TS"))
    assert not is_allowed_extension(Path("c.exe"))
    assert not is_allowed_extension(Path("d.env"))


def test_denied_env_variants():
    assert is_denied_name(".env")
    assert is_denied_name(".env.local")
    assert is_denied_name(".env.production")
    assert not is_denied_name("env.txt")


def test_denied_secrets():
    assert is_denied_name("id_rsa")
    assert is_denied_name("cert.pem")
    assert is_denied_name("secret.key")
    assert is_denied_name(".npmrc")
    assert not is_denied_name("main.py")


# --- traversal ------------------------------------------------------------


def test_dotdot_traversal_rejected(workspace: Path):
    (workspace / "real.txt").write_text("ok")
    with pytest.raises(WorkspaceAccessError):
        resolve_within_workspace("../escape.txt", workspace)


def test_absolute_outside_rejected(workspace: Path, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside").resolve()
    (outside / "x.txt").write_text("nope")
    with pytest.raises(WorkspaceAccessError):
        resolve_within_workspace(str(outside / "x.txt"), workspace)


def test_relative_inside_ok(workspace: Path):
    (workspace / "real.txt").write_text("ok")
    p = resolve_within_workspace("real.txt", workspace)
    assert p == (workspace / "real.txt").resolve()


def test_absolute_inside_ok(workspace: Path):
    (workspace / "real.txt").write_text("ok")
    p = resolve_within_workspace(str(workspace / "real.txt"), workspace)
    assert p == (workspace / "real.txt").resolve()


# --- sensitive files skipped ---------------------------------------------


def test_env_file_not_read(workspace: Path):
    (workspace / ".env").write_text("SECRET=1")
    s = settings_for(workspace)
    data = collect_context([".env"], s)
    assert data.files == []
    assert any(".env" in w or "No readable" in w for w in data.warnings)


def test_pem_file_not_read(workspace: Path):
    (workspace / "key.pem").write_text("-----BEGIN PRIVATE KEY-----")
    s = settings_for(workspace)
    data = collect_context(["key.pem"], s)
    assert data.files == []


def test_py_file_read(workspace: Path):
    (workspace / "main.py").write_text("print('hi')\n")
    s = settings_for(workspace)
    data = collect_context(["main.py"], s)
    assert len(data.files) == 1
    assert "print('hi')" in data.files[0].content


# --- denied directories ---------------------------------------------------


def test_denied_dirs_skipped(workspace: Path):
    (workspace / "node_modules").mkdir()
    (workspace / "node_modules" / "pkg.py").write_text("x = 1")
    (workspace / ".git").mkdir()
    (workspace / ".git" / "config.py").write_text("y = 2")
    (workspace / "good.py").write_text("z = 3")
    s = settings_for(workspace)
    data = collect_context(["."], s)
    names = [Path(f.rel_path).name for f in data.files]
    assert "good.py" in names
    assert "pkg.py" not in names
    assert "config.py" not in names


def test_max_depth_enforced(workspace: Path):
    deep = workspace / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "deep.py").write_text("deep")
    (workspace / "shallow.py").write_text("shallow")
    s = settings_for(workspace)
    data = collect_context(["."], s, max_depth=1)
    names = [Path(f.rel_path).name for f in data.files]
    assert "shallow.py" in names
    assert "deep.py" not in names


# --- size limits ----------------------------------------------------------


def test_single_file_too_large(workspace: Path):
    big = workspace / "big.txt"
    big.write_bytes(b"x" * 2048)
    s = settings_for(workspace, max_file=512, max_total=8192)
    with pytest.raises(FileTooLargeError):
        collect_context(["big.txt"], s)


def test_total_size_exceeded(workspace: Path):
    for i in range(5):
        (workspace / f"f{i}.txt").write_text("x" * 300)
    s = settings_for(workspace, max_file=512, max_total=1024)
    with pytest.raises(FileTooLargeError):
        collect_context(["."], s, max_depth=1)


# --- binary / encoding ----------------------------------------------------


def test_binary_file_skipped(workspace: Path):
    (workspace / "blob.py").write_bytes(b"\x00\x01\x02\x00binary")
    (workspace / "good.py").write_text("ok")
    s = settings_for(workspace)
    data = collect_context(["."], s, max_depth=1)
    names = [Path(f.rel_path).name for f in data.files]
    assert "good.py" in names
    assert "blob.py" not in names
    assert any("blob" in w for w in data.warnings)


def test_non_utf8_skipped(workspace: Path):
    (workspace / "weird.txt").write_bytes(b"\xff\xfe\x00bad")
    s = settings_for(workspace)
    data = collect_context(["weird.txt"], s)
    assert data.files == []
    assert any("weird" in w for w in data.warnings)


# --- symlink escaping -----------------------------------------------------


def test_symlink_escape_rejected(workspace: Path, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside").resolve()
    (outside / "secret.py").write_text("STOLEN")
    link = workspace / "link.py"
    create_real_symlink(outside / "secret.py", link)
    s = settings_for(workspace)
    with pytest.raises(WorkspaceAccessError):
        collect_context(["link.py"], s)


def test_symlink_into_subdir_inside_ok(workspace: Path):
    (workspace / "real.py").write_text("ok")
    sub = workspace / "sub"
    sub.mkdir()
    link = sub / "alias.py"
    create_real_symlink(workspace / "real.py", link)
    s = settings_for(workspace)
    # symlink target is inside workspace -> allowed.
    data = collect_context(["sub"], s, max_depth=1)
    assert any("alias.py" in f.rel_path for f in data.files)


def test_symlink_in_walked_dir_escape_rejected(workspace: Path, tmp_path_factory):
    """A symlink discovered while walking a directory must not leak outside."""
    outside = tmp_path_factory.mktemp("outside").resolve()
    (outside / "secret.py").write_text("STOLEN")
    sub = workspace / "sub"
    sub.mkdir()
    link = sub / "alias.py"
    create_real_symlink(outside / "secret.py", link)
    s = settings_for(workspace)
    with pytest.raises(WorkspaceAccessError):
        collect_context(["sub"], s, max_depth=1)


# --- workspace root required ---------------------------------------------


def test_workspace_root_required(tmp_path):
    s = Settings()  # no workspace_root
    with pytest.raises(ConfigurationError):
        collect_context(["."], s, max_depth=1)


def test_empty_path_rejected(workspace: Path):
    s = settings_for(workspace)
    with pytest.raises(WorkspaceAccessError):
        collect_context([""], s)


def test_no_readable_files_warns(workspace: Path):
    (workspace / "image.png").write_bytes(b"\x89PNG")  # not allowed ext
    s = settings_for(workspace)
    data = collect_context(["."], s, max_depth=1)
    assert data.files == []
    assert any("No readable" in w for w in data.warnings)
