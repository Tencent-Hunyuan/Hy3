"""允许根目录与受限文件读取测试。"""

import hashlib
import os
import subprocess
import traceback
from pathlib import Path

import pytest

from hy3_knowledge_mcp import paths, safe_fs
from hy3_knowledge_mcp.errors import LimitExceededError, PathNotAllowedError
from hy3_knowledge_mcp.paths import (
    build_allowed_roots,
    discover_source_files,
    read_validated_bytes,
    resolve_requested_path,
)
from hy3_knowledge_mcp.safe_fs import FileMetadata


def test_allowed_root_rejects_nul_with_safe_context_free_error(tmp_path: Path) -> None:
    """NUL 路径在任何文件系统调用前映射为不泄露路径的领域错误。"""
    invalid = str(tmp_path / "private-root") + "\0suffix"

    with pytest.raises(PathNotAllowedError) as exc_info:
        build_allowed_roots((Path(invalid),))

    error = exc_info.value
    assert str(tmp_path) not in str(error)
    assert str(tmp_path) not in repr(error)
    assert error.__cause__ is None
    assert error.__context__ is None


def test_build_allowed_roots_uses_stable_ids_and_deepest_first(tmp_path: Path) -> None:
    """允许根目录去重。优先匹配更深的根目录。"""
    parent = tmp_path / "knowledge"
    child = parent / "nested"
    child.mkdir(parents=True)

    roots = build_allowed_roots((parent, child, parent / "."))

    expected_id = hashlib.sha256(
        os.path.normcase(str(child.resolve())).encode("utf-8")
    ).hexdigest()[:12]
    assert tuple(root.path for root in roots) == (child.resolve(), parent.resolve())
    assert roots[0].root_id == expected_id


def test_resolve_absolute_path_uses_deepest_containing_root(tmp_path: Path) -> None:
    """绝对路径归属到包含它的最深允许根目录。"""
    parent = tmp_path / "knowledge"
    child = parent / "nested"
    source = child / "guide.md"
    child.mkdir(parents=True)
    source.write_text("知识", encoding="utf-8")
    roots = build_allowed_roots((parent, child))

    target = resolve_requested_path(source, roots)

    assert target.absolute_path == source.resolve()
    assert target.root.path == child.resolve()


def test_resolve_relative_path_rejects_ambiguity_across_roots(tmp_path: Path) -> None:
    """相对路径在多个根目录存在时拒绝猜测。"""
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "guide.md").write_text("一", encoding="utf-8")
    (second / "guide.md").write_text("二", encoding="utf-8")

    with pytest.raises(PathNotAllowedError, match="无法唯一"):
        resolve_requested_path("guide.md", build_allowed_roots((first, second)))


def test_resolve_rejects_common_prefix_directory_outside_root(tmp_path: Path) -> None:
    """字符串公共前缀不能绕过路径组件边界。"""
    root = tmp_path / "allowed"
    evil = tmp_path / "allowed-evil"
    root.mkdir()
    evil.mkdir()
    outside = evil / "secret.md"
    outside.write_text("秘密", encoding="utf-8")

    with pytest.raises(PathNotAllowedError):
        resolve_requested_path(outside, build_allowed_roots((root,)))


def test_resolve_rejects_external_file_symlink_when_supported(tmp_path: Path) -> None:
    """指向允许根目录外部的文件符号链接不能通过严格解析。"""
    root = tmp_path / "root"
    outside = tmp_path / "outside.md"
    link = root / "linked.md"
    root.mkdir()
    outside.write_text("秘密", encoding="utf-8")
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"当前运行环境无法创建文件符号链接: {exc}")

    with pytest.raises(PathNotAllowedError):
        resolve_requested_path(link, build_allowed_roots((root,)))


@pytest.mark.skipif(os.name != "nt", reason="Windows junction only")
@pytest.mark.parametrize("relative", (False, True), ids=("absolute", "relative"))
def test_resolve_rejects_direct_internal_junction_directory(
    tmp_path: Path,
    relative: bool,
) -> None:
    """直接请求根目录内 junction 时在 resolve 擦除链接前拒绝。"""
    root = tmp_path / "root"
    target = root / "target"
    junction = root / "linked"
    target.mkdir(parents=True)
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            "创建 junction 失败: "
            f"stdout={result.stdout.strip()!r}, stderr={result.stderr.strip()!r}"
        )
    requested: str | Path = junction.name if relative else junction

    with pytest.raises(PathNotAllowedError, match="链接"):
        resolve_requested_path(requested, build_allowed_roots((root,)))


@pytest.mark.skipif(os.name != "nt", reason="Windows junction race only")
def test_resolution_never_accepts_junction_swapped_after_component_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """组件验证后发生目录交换时只能失败或保持原安全对象。"""
    root = tmp_path / "root"
    normal = root / "normal"
    backup = root / "normal-backup"
    junction_target = root / "junction-target"
    normal.mkdir(parents=True)
    junction_target.mkdir()
    safe_file = normal / "guide.md"
    junction_file = junction_target / "guide.md"
    safe_file.write_text("safe", encoding="utf-8")
    junction_file.write_text("junction", encoding="utf-8")
    roots = build_allowed_roots((root,))
    attempted = False
    swap_succeeded = False
    inside_legacy_stat = False
    handle_paths: dict[int, Path] = {}
    original_paths_stat = paths.stat_no_follow
    original_create_handle = safe_fs._windows_create_handle
    original_handle_metadata = safe_fs._windows_metadata_from_handle

    def attempt_swap() -> None:
        nonlocal attempted, swap_succeeded
        if attempted:
            return
        attempted = True
        try:
            normal.rename(backup)
        except OSError:
            return
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(normal), str(junction_target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            pytest.fail(
                "竞态测试创建 junction 失败: "
                f"stdout={result.stdout.strip()!r}, stderr={result.stderr.strip()!r}"
            )
        swap_succeeded = True

    def swapping_stat(path: Path) -> FileMetadata:
        nonlocal inside_legacy_stat
        inside_legacy_stat = True
        try:
            metadata = original_paths_stat(path)
        finally:
            inside_legacy_stat = False
        if path == normal:
            attempt_swap()
        return metadata

    def recording_create_handle(path: Path, *, is_directory: bool, for_read: bool) -> int:
        handle = original_create_handle(
            path,
            is_directory=is_directory,
            for_read=for_read,
        )
        handle_paths[handle] = path
        return handle

    def swapping_handle_metadata(handle: int) -> FileMetadata:
        metadata = original_handle_metadata(handle)
        if not inside_legacy_stat and handle_paths.get(handle) == normal:
            attempt_swap()
        return metadata

    monkeypatch.setattr(paths, "stat_no_follow", swapping_stat)
    monkeypatch.setattr(safe_fs, "_windows_create_handle", recording_create_handle)
    monkeypatch.setattr(safe_fs, "_windows_metadata_from_handle", swapping_handle_metadata)

    try:
        target = resolve_requested_path(safe_file, roots)
    except PathNotAllowedError:
        target = None

    assert attempted
    if target is not None:
        assert target.absolute_path != junction_file
        assert target.absolute_path == safe_file
        assert not swap_succeeded


def test_discovery_is_sorted_supported_and_globs_use_relative_posix_paths(tmp_path: Path) -> None:
    """发现结果稳定排序。只包含支持格式并按相对 POSIX 路径匹配。"""
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    for relative, content in (
        ("z.txt", "z"),
        ("A.md", "a"),
        ("notes.markdown", "m"),
        ("nested/B.rst", "b"),
        ("nested/manual.pdf", "%PDF"),
        ("nested/ignored.bin", "x"),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    roots = build_allowed_roots((root,))
    target = resolve_requested_path(root, roots)

    sources = discover_source_files(
        target,
        recursive=True,
        include_globs=("*.md", "nested/*.rst"),
        max_files=10,
        max_total_bytes=10_000,
    )

    assert tuple(source.relative_path.as_posix() for source in sources) == (
        "A.md",
        "nested/B.rst",
    )


@pytest.mark.parametrize(
    "pattern",
    ("**/" * 1500 + "*.md", "**/" * 300 + "*.md"),
    ids=("character-limit", "component-limit"),
)
def test_include_glob_complexity_fails_with_safe_limit_error(
    tmp_path: Path,
    pattern: str,
) -> None:
    """超长或组件过多的模式返回领域限制错误而非递归崩溃。"""
    root = tmp_path / "root"
    root.mkdir()
    (root / "guide.md").write_bytes(b"x")
    target = resolve_requested_path(root, build_allowed_roots((root,)))

    with pytest.raises(LimitExceededError, match="包含模式"):
        discover_source_files(
            target,
            recursive=True,
            include_globs=(pattern,),
            max_files=10,
            max_total_bytes=100,
        )


def test_discovery_enforces_directory_depth_file_and_total_byte_limits(tmp_path: Path) -> None:
    """目录、深度、文件数与总字节预算均立即生效。"""
    root = tmp_path / "root"
    deep = root / "one" / "two"
    deep.mkdir(parents=True)
    (root / "a.md").write_bytes(b"aa")
    (root / "b.txt").write_bytes(b"bb")
    (deep / "c.rst").write_bytes(b"c")
    target = resolve_requested_path(root, build_allowed_roots((root,)))
    common = {
        "target": target,
        "recursive": True,
        "include_globs": (),
        "max_files": 10,
        "max_total_bytes": 100,
    }

    with pytest.raises(LimitExceededError, match="目录"):
        discover_source_files(**common, max_directories=1)
    with pytest.raises(LimitExceededError, match="深度"):
        discover_source_files(**common, max_depth=1)
    with pytest.raises(LimitExceededError, match="文件"):
        discover_source_files(**{**common, "max_files": 1})
    with pytest.raises(LimitExceededError, match="字节"):
        discover_source_files(**{**common, "max_total_bytes": 3})


def test_read_rejects_same_size_same_mtime_identity_replacement(tmp_path: Path) -> None:
    """即使大小与时间相同。替换后的不同文件身份也必须拒绝。"""
    root = tmp_path / "root"
    root.mkdir()
    path = root / "guide.md"
    path.write_bytes(b"first")
    target = resolve_requested_path(path, build_allowed_roots((root,)))
    source = discover_source_files(
        target,
        recursive=False,
        include_globs=(),
        max_files=1,
        max_total_bytes=100,
    )[0]
    original_mtime = source.mtime_ns
    backup = root / "old.md"
    path.rename(backup)
    path.write_bytes(b"other")
    os.utime(path, ns=(original_mtime, original_mtime))

    with pytest.raises(PathNotAllowedError, match="发生变化"):
        read_validated_bytes(source, max_bytes=100)


def test_read_rejects_growth_and_does_not_leak_absolute_paths(tmp_path: Path) -> None:
    """发现后的增长被拒绝。异常链不泄露绝对路径。"""
    root = tmp_path / "private-root"
    root.mkdir()
    path = root / "guide.md"
    path.write_bytes(b"a")
    target = resolve_requested_path(path, build_allowed_roots((root,)))
    source = discover_source_files(
        target,
        recursive=False,
        include_globs=(),
        max_files=1,
        max_total_bytes=100,
    )[0]
    path.write_bytes(b"grew")

    with pytest.raises(PathNotAllowedError) as exc_info:
        read_validated_bytes(source, max_bytes=100)

    error = exc_info.value
    formatted = "".join(traceback.format_exception(error))
    assert str(root) not in str(error)
    assert str(root) not in repr(error)
    assert str(root) not in formatted
    assert error.__cause__ is None
    assert error.__context__ is None


def test_read_uses_max_bytes_plus_one_to_report_overflow(tmp_path: Path) -> None:
    """读取只多取一个字节即可识别超限。避免把正常大文件误报为竞态。"""
    root = tmp_path / "root"
    root.mkdir()
    path = root / "guide.md"
    path.write_bytes(b"0123456789")
    target = resolve_requested_path(path, build_allowed_roots((root,)))
    source = discover_source_files(
        target,
        recursive=False,
        include_globs=(),
        max_files=1,
        max_total_bytes=100,
    )[0]

    with pytest.raises(LimitExceededError, match="读取限制"):
        read_validated_bytes(source, max_bytes=4)
