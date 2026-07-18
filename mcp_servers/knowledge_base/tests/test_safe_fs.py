"""安全文件系统原语测试。"""

import os
from pathlib import Path

import pytest

from hy3_knowledge_mcp import safe_fs
from hy3_knowledge_mcp.errors import PathNotAllowedError
from hy3_knowledge_mcp.safe_fs import (
    FileIdentity,
    FileMetadata,
    fstat_metadata,
    locked_scandir,
    open_verified_binary,
    resolve_no_follow,
    stat_no_follow,
)


def _mock_posix_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    """在 Windows 测试进程中提供 POSIX 安全打开能力常量。"""
    monkeypatch.setattr(safe_fs, "_IS_WINDOWS", False)
    monkeypatch.setattr(safe_fs.os, "O_NOFOLLOW", 0x100, raising=False)
    monkeypatch.setattr(safe_fs.os, "O_DIRECTORY", 0x200, raising=False)
    monkeypatch.setattr(safe_fs.os, "O_CLOEXEC", 0x400, raising=False)


def test_stat_no_follow_rejects_file_symlink_when_supported(tmp_path: Path) -> None:
    """无跟随元数据读取拒绝文件符号链接。"""
    target = tmp_path / "target.md"
    link = tmp_path / "link.md"
    target.write_text("知识", encoding="utf-8")
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"当前运行环境无法创建文件符号链接: {exc}")

    with pytest.raises(PathNotAllowedError, match="链接"):
        stat_no_follow(link)


@pytest.mark.skipif(os.name != "nt", reason="Windows native handle flags only")
def test_windows_directory_handle_uses_nofollow_locking_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows 目录句柄禁止跟随重解析点且不共享删除权限。"""
    calls: list[tuple[object, ...]] = []

    class FakeCreateFile:
        def __call__(self, *args: object) -> int:
            calls.append(args)
            return 123

    class FakeKernel32:
        CreateFileW = FakeCreateFile()

    monkeypatch.setattr(safe_fs, "_kernel32", FakeKernel32())

    handle = safe_fs._windows_create_handle(tmp_path, is_directory=True, for_read=False)
    file_handle = safe_fs._windows_create_handle(
        tmp_path / "guide.md",
        is_directory=False,
        for_read=True,
    )

    assert handle == 123
    assert file_handle == 123
    assert len(calls) == 2
    share_mode = calls[0][2]
    flags = calls[0][5]
    assert isinstance(share_mode, int)
    assert isinstance(flags, int)
    assert flags & safe_fs.FILE_FLAG_OPEN_REPARSE_POINT
    assert flags & safe_fs.FILE_FLAG_BACKUP_SEMANTICS
    assert not share_mode & safe_fs.FILE_SHARE_DELETE
    file_share_mode = calls[1][2]
    assert isinstance(file_share_mode, int)
    assert not file_share_mode & safe_fs.FILE_SHARE_WRITE
    assert not file_share_mode & safe_fs.FILE_SHARE_DELETE


def test_verified_binary_uses_same_identity_as_no_follow_snapshot(tmp_path: Path) -> None:
    """发现身份与打开句柄身份使用同一稳定表示。"""
    root = tmp_path / "root"
    root.mkdir()
    path = root / "guide.md"
    path.write_bytes(b"knowledge")
    snapshot = stat_no_follow(path)

    with open_verified_binary(path, root, snapshot.identity) as file_object:
        opened = fstat_metadata(file_object)
        data = file_object.read()

    assert opened.identity == snapshot.identity
    assert opened.size_bytes == snapshot.size_bytes
    assert data == b"knowledge"


@pytest.mark.skipif(os.name != "nt", reason="Windows native handle behavior only")
@pytest.mark.parametrize("phase", ("downstream", "scanner-close"))
def test_windows_locked_scandir_releases_each_owner_once_after_yield(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    """Windows 枚举器接管后任意异常只关闭 scanner 与 handle 各一次。"""
    root = tmp_path / "root"
    root.mkdir()
    expected = FileIdentity(1, 2)
    handle_closed: list[int] = []

    class FakeScanner:
        def __init__(self) -> None:
            self.close_calls = 0

        def close(self) -> None:
            self.close_calls += 1
            if phase == "scanner-close":
                raise ValueError("mocked scanner close failure")

    scanner = FakeScanner()
    monkeypatch.setattr(safe_fs, "_windows_create_handle", lambda *args, **kwargs: 45)
    monkeypatch.setattr(
        safe_fs,
        "_windows_metadata_from_handle",
        lambda _handle: FileMetadata(0, 0, 1, 2, True),
    )
    monkeypatch.setattr(safe_fs, "_windows_final_path", lambda _handle: root)
    monkeypatch.setattr(safe_fs.os, "scandir", lambda _path: scanner)
    monkeypatch.setattr(safe_fs, "_windows_close_handle", handle_closed.append)

    error_type = RuntimeError if phase == "downstream" else ValueError
    with pytest.raises(error_type), locked_scandir(root, root, expected):
        if phase == "downstream":
            raise RuntimeError("mocked downstream failure")

    assert scanner.close_calls == 1
    assert handle_closed == [45]


@pytest.mark.skipif(os.name != "nt", reason="Windows native handle behavior only")
def test_windows_binary_open_closes_handle_on_identity_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """文件身份不符时关闭尚未转交给 CRT 的原生句柄。"""
    root = tmp_path / "root"
    root.mkdir()
    path = root / "guide.md"
    path.write_bytes(b"x")
    closed: list[int] = []
    monkeypatch.setattr(safe_fs, "_windows_create_handle", lambda *args, **kwargs: 66)
    monkeypatch.setattr(
        safe_fs,
        "_windows_metadata_from_handle",
        lambda _handle: FileMetadata(1, 1, 9, 9, False),
    )
    monkeypatch.setattr(safe_fs, "_windows_close_handle", closed.append)

    with (
        pytest.raises(PathNotAllowedError),
        open_verified_binary(
            path,
            root,
            FileIdentity(1, 2),
        ),
    ):
        pytest.fail("身份不符时不应返回文件对象")

    assert closed == [66]


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor branch only")
def test_posix_locked_scandir_and_binary_open_use_descriptor_identity(tmp_path: Path) -> None:
    """POSIX 分支使用 O_NOFOLLOW 描述符并保持对象身份。"""
    root = tmp_path / "root"
    root.mkdir()
    path = root / "guide.md"
    path.write_bytes(b"knowledge")
    root_snapshot = stat_no_follow(root)
    file_snapshot = stat_no_follow(path)

    with locked_scandir(root, root, root_snapshot.identity) as scanner:
        assert [entry.name for entry in scanner] == ["guide.md"]
    with open_verified_binary(path, root, file_snapshot.identity) as file_object:
        assert file_object.read() == b"knowledge"


@pytest.mark.parametrize(
    ("operation", "missing_flag"),
    (("directory", "O_NOFOLLOW"), ("directory", "O_DIRECTORY"), ("file", "O_NOFOLLOW")),
)
def test_posix_open_fails_closed_when_required_flags_are_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    missing_flag: str,
) -> None:
    """POSIX 缺少 no-follow 或目录能力时不得退化为普通 open。"""
    root = tmp_path / "root"
    root.mkdir()
    path = root if operation == "directory" else root / "guide.md"
    if operation == "file":
        path.write_bytes(b"x")
    open_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(safe_fs, "_IS_WINDOWS", False)
    monkeypatch.setattr(safe_fs.os, "O_NOFOLLOW", 0x100, raising=False)
    monkeypatch.setattr(safe_fs.os, "O_DIRECTORY", 0x200, raising=False)
    monkeypatch.delattr(safe_fs.os, missing_flag, raising=False)

    def forbidden_open(*args: object, **kwargs: object) -> int:
        open_calls.append(args)
        raise AssertionError("缺少安全 flags 时不得调用 os.open")

    monkeypatch.setattr(safe_fs.os, "open", forbidden_open)

    with pytest.raises(PathNotAllowedError, match="能力"):
        if operation == "directory":
            with locked_scandir(path, root, FileIdentity(1, 2)):
                pytest.fail("缺少 flags 时不应进入目录上下文")
        else:
            with open_verified_binary(path, root, FileIdentity(1, 2)):
                pytest.fail("缺少 flags 时不应进入文件上下文")

    assert open_calls == []


def test_darwin_final_path_uses_f_getpath(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Darwin 从已打开 fd 通过 F_GETPATH 获取最终路径。"""
    expected = tmp_path / "root" / "guide.md"
    calls: list[tuple[int, int, int]] = []

    class FakeFcntl:
        @staticmethod
        def fcntl(fd: int, command: int, buffer: bytes) -> bytes:
            calls.append((fd, command, len(buffer)))
            encoded = os.fsencode(expected)
            return encoded + b"\0" * (len(buffer) - len(encoded))

    monkeypatch.setattr(safe_fs, "_PLATFORM", "darwin")
    monkeypatch.setattr(safe_fs, "_fcntl", FakeFcntl())

    actual = safe_fs._posix_final_path(42)

    assert actual == expected
    assert calls == [(42, safe_fs._DARWIN_F_GETPATH, safe_fs._DARWIN_PATH_BUFFER_BYTES)]


def test_windows_handle_held_resolver_closes_all_handles_in_reverse_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows resolver 持有全部祖先 handle 并反序各关闭一次。"""
    root = tmp_path / "root"
    child = root / "child"
    path = child / "guide.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"x")
    handle_for_path = {root: 70, child: 71, path: 72}
    path_for_handle = {handle: item for item, handle in handle_for_path.items()}
    closed: list[int] = []
    monkeypatch.setattr(safe_fs, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        safe_fs,
        "_windows_create_handle",
        lambda item, **kwargs: handle_for_path[item],
    )
    monkeypatch.setattr(
        safe_fs,
        "_windows_metadata_from_handle",
        lambda handle: FileMetadata(0, 0, 1, handle, handle != 72),
    )
    monkeypatch.setattr(
        safe_fs,
        "_windows_final_path",
        lambda handle: path_for_handle[handle],
    )
    monkeypatch.setattr(safe_fs, "_windows_close_handle", closed.append)

    assert resolve_no_follow(path, root) == path
    assert closed == [72, 71, 70]


def test_posix_handle_held_resolver_uses_dir_fd_and_closes_in_reverse_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POSIX resolver 相对祖先 fd 打开组件并反序各关闭一次。"""
    root = tmp_path / "root"
    child = root / "child"
    path = child / "guide.md"
    child.mkdir(parents=True)
    path.write_bytes(b"x")
    stats = {60: root.stat(), 61: child.stat(), 62: path.stat()}
    final_paths = {60: root, 62: path}
    open_calls: list[tuple[object, int, int | None]] = []
    closed: list[int] = []
    _mock_posix_capabilities(monkeypatch)

    def fake_open(item: object, flags: int, *, dir_fd: int | None = None) -> int:
        open_calls.append((item, flags, dir_fd))
        if dir_fd is None:
            return 60
        if dir_fd == 60 and item == "child":
            return 61
        if dir_fd == 61 and item == "guide.md":
            return 62
        raise AssertionError(f"意外的相对打开: {item!r}, dir_fd={dir_fd!r}")

    monkeypatch.setattr(safe_fs.os, "open", fake_open)
    monkeypatch.setattr(safe_fs.os, "supports_dir_fd", {fake_open})
    monkeypatch.setattr(safe_fs.os, "fstat", stats.__getitem__)
    monkeypatch.setattr(safe_fs, "_posix_final_path", final_paths.__getitem__)
    monkeypatch.setattr(safe_fs.os, "close", closed.append)

    assert resolve_no_follow(path, root) == path
    assert open_calls[0][0] == root
    assert open_calls[0][1] & safe_fs.os.O_DIRECTORY
    assert open_calls[1][0:] == ("child", open_calls[1][1], 60)
    assert open_calls[1][1] & safe_fs.os.O_DIRECTORY
    assert open_calls[2][0:] == ("guide.md", open_calls[2][1], 61)
    assert not open_calls[2][1] & safe_fs.os.O_DIRECTORY
    assert all(flags & safe_fs.os.O_NOFOLLOW for _, flags, _ in open_calls)
    assert closed == [62, 61, 60]


def test_posix_handle_held_resolver_fails_closed_without_dir_fd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POSIX os.open 不支持 dir_fd 时不得退化到拼接路径打开。"""
    root = tmp_path / "root"
    root.mkdir()
    path = root / "guide.md"
    path.write_bytes(b"x")
    open_calls: list[object] = []
    _mock_posix_capabilities(monkeypatch)

    def forbidden_open(item: object, *args: object, **kwargs: object) -> int:
        open_calls.append(item)
        raise AssertionError("缺少 dir_fd 时不得调用 os.open")

    monkeypatch.setattr(safe_fs.os, "open", forbidden_open)
    monkeypatch.setattr(safe_fs.os, "supports_dir_fd", set())

    with pytest.raises(PathNotAllowedError, match="相对打开能力"):
        resolve_no_follow(path, root)

    assert open_calls == []
