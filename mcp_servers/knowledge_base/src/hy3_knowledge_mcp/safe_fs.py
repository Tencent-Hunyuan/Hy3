"""抵御链接跳转与路径交换的底层文件系统原语。"""

from __future__ import annotations

import ntpath
import os
import posixpath
import stat
import struct
import sys
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from errno import ENOENT, ENOTDIR
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO

from .errors import PathNotAllowedError

FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_READ_ATTRIBUTES = 0x00000080
GENERIC_READ = 0x80000000
FILE_TYPE_DISK = 0x0001
FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
FILE_ID_INFO_CLASS = 18
INVALID_HANDLE_VALUE = (1 << (8 * struct.calcsize("P"))) - 1
_IS_WINDOWS = os.name == "nt"
_PLATFORM = sys.platform
_DARWIN_F_GETPATH = 50
_DARWIN_PATH_BUFFER_BYTES = 1024

try:
    import fcntl as _fcntl
except ImportError:
    _fcntl = None


@dataclass(frozen=True)
class FileIdentity:
    """跨安全打开步骤传递的文件系统对象身份。"""

    device_id: int
    file_id: int


@dataclass(frozen=True)
class FileMetadata:
    """不跟随链接取得的受限元数据。"""

    size_bytes: int
    mtime_ns: int
    device_id: int
    file_id: int
    is_directory: bool

    @property
    def identity(self) -> FileIdentity:
        """返回可用于后续打开验证的稳定身份。"""
        return FileIdentity(self.device_id, self.file_id)


@dataclass(frozen=True)
class ResolvedPathSnapshot:
    """由最终 handle 同时取得的规范路径与对象元数据。"""

    canonical_path: Path
    metadata: FileMetadata


if _IS_WINDOWS:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class _FileAttributeTagInfo(ctypes.Structure):
        _fields_ = [
            ("FileAttributes", wintypes.DWORD),
            ("ReparseTag", wintypes.DWORD),
        ]

    class _FileId128(ctypes.Structure):
        _fields_ = [("Identifier", ctypes.c_ubyte * 16)]

    class _FileIdInfo(ctypes.Structure):
        _fields_ = [
            ("VolumeSerialNumber", ctypes.c_ulonglong),
            ("FileId", _FileId128),
        ]

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.GetFileType.argtypes = (wintypes.HANDLE,)
    _kernel32.GetFileType.restype = wintypes.DWORD
    _kernel32.GetFileInformationByHandle.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ByHandleFileInformation),
    )
    _kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
    _kernel32.GetFileInformationByHandleEx.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    _kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _kernel32.GetFinalPathNameByHandleW.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    _kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
else:
    _kernel32 = None


def _identity_value(expected: FileIdentity | tuple[int, int]) -> FileIdentity:
    """统一调用方提供的身份表示。"""
    if isinstance(expected, FileIdentity):
        return expected
    return FileIdentity(*expected)


def _metadata_from_stat(result: os.stat_result) -> FileMetadata:
    """将 POSIX fstat 结果转换为共享元数据。"""
    return FileMetadata(
        size_bytes=result.st_size,
        mtime_ns=result.st_mtime_ns,
        device_id=result.st_dev,
        file_id=result.st_ino,
        is_directory=stat.S_ISDIR(result.st_mode),
    )


def _verify_expected_identity(
    metadata: FileMetadata,
    expected: FileIdentity | tuple[int, int],
) -> None:
    """拒绝发现后被替换成另一对象的路径。"""
    if metadata.identity != _identity_value(expected):
        raise PathNotAllowedError("请求的路径在验证期间发生变化")


def _ensure_contained(final_path: Path, root: Path) -> None:
    """使用最终打开对象的路径验证允许根目录边界。"""
    if canonical_relative_parts(final_path, root) is None:
        raise PathNotAllowedError("请求的路径不在允许范围内")


def _windows_create_handle(path: Path, *, is_directory: bool, for_read: bool) -> int:
    """以不跟随重解析点且禁止删除共享的方式打开 Windows 路径。"""
    if not _IS_WINDOWS or _kernel32 is None:
        raise OSError("Windows handle API unavailable")
    desired_access = GENERIC_READ if for_read else FILE_READ_ATTRIBUTES
    share_mode = FILE_SHARE_READ | FILE_SHARE_WRITE if is_directory else FILE_SHARE_READ
    flags = FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS
    handle = _kernel32.CreateFileW(
        str(path),
        desired_access,
        share_mode,
        None,
        OPEN_EXISTING,
        flags,
        None,
    )
    if handle in (None, INVALID_HANDLE_VALUE):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(handle)


def _windows_close_handle(handle: int) -> None:
    """关闭未转交给 CRT 的 Windows 原生句柄。"""
    if _IS_WINDOWS and _kernel32 is not None:
        _kernel32.CloseHandle(handle)


def _windows_metadata_from_handle(handle: int) -> FileMetadata:
    """从已打开 Windows 句柄读取类型、身份、大小和修改时间。"""
    if not _IS_WINDOWS or _kernel32 is None:
        raise OSError("Windows handle API unavailable")
    if _kernel32.GetFileType(handle) != FILE_TYPE_DISK:
        raise PathNotAllowedError("请求的路径类型不受支持")

    tag_info = _FileAttributeTagInfo()
    if not _kernel32.GetFileInformationByHandleEx(
        handle,
        FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(tag_info),
        ctypes.sizeof(tag_info),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    if tag_info.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
        raise PathNotAllowedError("请求的路径包含不允许的链接")

    identity_info = _FileIdInfo()
    if not _kernel32.GetFileInformationByHandleEx(
        handle,
        FILE_ID_INFO_CLASS,
        ctypes.byref(identity_info),
        ctypes.sizeof(identity_info),
    ):
        raise ctypes.WinError(ctypes.get_last_error())

    information = _ByHandleFileInformation()
    if not _kernel32.GetFileInformationByHandle(handle, ctypes.byref(information)):
        raise ctypes.WinError(ctypes.get_last_error())

    ticks = (information.ftLastWriteTime.dwHighDateTime << 32) | (
        information.ftLastWriteTime.dwLowDateTime
    )
    mtime_ns = ticks * 100 - 11_644_473_600_000_000_000
    file_id = int.from_bytes(bytes(identity_info.FileId.Identifier), "little")
    return FileMetadata(
        size_bytes=(information.nFileSizeHigh << 32) | information.nFileSizeLow,
        mtime_ns=max(mtime_ns, 0),
        device_id=int(identity_info.VolumeSerialNumber),
        file_id=file_id,
        is_directory=bool(information.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY),
    )


def _strip_windows_extended_prefix(path: str) -> str:
    """把句柄返回的扩展 DOS 路径转换为 pathlib 可比较形式。"""
    uppercase = path.upper()
    if uppercase.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if uppercase.startswith("\\\\?\\"):
        return path[4:]
    return path


def _windows_final_path(handle: int) -> Path:
    """仅根据已打开句柄取得最终规范路径。"""
    if not _IS_WINDOWS or _kernel32 is None:
        raise OSError("Windows handle API unavailable")
    capacity = 32_768
    buffer = ctypes.create_unicode_buffer(capacity)
    length = _kernel32.GetFinalPathNameByHandleW(handle, buffer, capacity, 0)
    if length == 0:
        raise ctypes.WinError(ctypes.get_last_error())
    if length >= capacity:
        capacity = length + 1
        buffer = ctypes.create_unicode_buffer(capacity)
        length = _kernel32.GetFinalPathNameByHandleW(handle, buffer, capacity, 0)
        if length == 0 or length >= capacity:
            raise ctypes.WinError(ctypes.get_last_error())
    return Path(_strip_windows_extended_prefix(buffer.value))


def _posix_final_path(fd: int) -> Path:
    """通过描述符链接取得实际打开对象的路径。"""
    if _PLATFORM == "darwin":
        if _fcntl is None:
            raise OSError("Darwin F_GETPATH unavailable")
        result = _fcntl.fcntl(fd, _DARWIN_F_GETPATH, b"\0" * _DARWIN_PATH_BUFFER_BYTES)
        encoded_path = bytes(result).split(b"\0", 1)[0]
        if not encoded_path:
            raise OSError("Darwin F_GETPATH returned an empty path")
        return Path(os.fsdecode(encoded_path))

    if _PLATFORM.startswith("linux"):
        prefixes = ("/proc/self/fd", "/dev/fd")
    elif _PLATFORM.startswith(("freebsd", "openbsd", "netbsd")):
        prefixes = ("/dev/fd",)
    else:
        raise OSError("unsupported POSIX final-path capability")

    for prefix in prefixes:
        descriptor_path = Path(prefix) / str(fd)
        try:
            return Path(os.readlink(descriptor_path))
        except OSError:
            continue
    raise OSError("descriptor final path unavailable")


def _posix_open_flags(*, directory: bool) -> int:
    """返回具备强制 no-follow 能力的 POSIX 打开标志。"""
    if not hasattr(os, "O_NOFOLLOW") or (directory and not hasattr(os, "O_DIRECTORY")):
        raise PathNotAllowedError("当前 POSIX 平台缺少安全打开能力")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if directory:
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _missing_path_error(error: OSError) -> bool:
    """判断打开失败是否仅表示候选路径不存在。"""
    return error.errno in {ENOENT, ENOTDIR} or getattr(error, "winerror", None) in {2, 3}


def _same_canonical_path(first: Path, second: Path) -> bool:
    """比较两个已经由 handle 规范化的绝对路径。"""
    return canonical_path_key(first) == canonical_path_key(second)


def _darwin_path_case_sensitive(path: str) -> bool:
    """查询 Darwin 路径所在卷的大小写语义。未知时保守区分大小写。"""
    pathconf = getattr(os, "pathconf", None)
    if pathconf is None:
        return True
    try:
        return bool(pathconf(path, "PC_CASE_SENSITIVE"))
    except (OSError, ValueError):
        return True


def _normalized_absolute_path(path: os.PathLike[str] | str) -> str:
    """按平台语法生成不改变 Unicode 或大小写的绝对路径。"""
    value = os.fspath(path)
    if _IS_WINDOWS:
        value = value.replace("/", "\\")
        value = _strip_windows_extended_prefix(value)
        value = ntpath.abspath(value)
        value = _strip_windows_extended_prefix(value)
        return ntpath.normpath(value)
    return posixpath.normpath(posixpath.abspath(value))


def canonical_path_key(path: os.PathLike[str] | str) -> str:
    """按当前平台文件系统语义返回适合比较和稳定哈希的路径 key。"""
    value = _normalized_absolute_path(path)
    if _IS_WINDOWS:
        return ntpath.normcase(value)

    if _PLATFORM == "darwin":
        case_sensitive = _darwin_path_case_sensitive(value)
        value = unicodedata.normalize("NFC", value)
        if not case_sensitive:
            value = value.casefold()
    return value


def canonical_relative_parts(
    path: os.PathLike[str] | str,
    root: os.PathLike[str] | str,
) -> tuple[str, ...] | None:
    """按组件边界和平台 canonical key 语义取得相对根目录的组件。"""
    if _IS_WINDOWS:
        candidate = PureWindowsPath(_normalized_absolute_path(path))
        canonical_root = PureWindowsPath(_normalized_absolute_path(root))
    elif isinstance(path, PureWindowsPath) and isinstance(root, PureWindowsPath):
        candidate = PureWindowsPath(ntpath.normpath(ntpath.abspath(os.fspath(path))))
        canonical_root = PureWindowsPath(ntpath.normpath(ntpath.abspath(os.fspath(root))))
    else:
        candidate = PurePosixPath(posixpath.normpath(posixpath.abspath(os.fspath(path))))
        canonical_root = PurePosixPath(posixpath.normpath(posixpath.abspath(os.fspath(root))))
    root_part_count = len(canonical_root.parts)
    if len(candidate.parts) < root_part_count:
        return None

    darwin_case_sensitive = True
    if _PLATFORM == "darwin" and not _IS_WINDOWS:
        darwin_case_sensitive = _darwin_path_case_sensitive(os.fspath(canonical_root))

    def component_key(part: str) -> str:
        if _IS_WINDOWS:
            return ntpath.normcase(part)
        if _PLATFORM == "darwin":
            part = unicodedata.normalize("NFC", part)
            if not darwin_case_sensitive:
                part = part.casefold()
        return part

    if any(
        component_key(candidate_part) != component_key(root_part)
        for candidate_part, root_part in zip(
            candidate.parts[:root_part_count],
            canonical_root.parts,
            strict=True,
        )
    ):
        return None
    return candidate.parts[root_part_count:]


def canonicalize_allowed_root(path: Path) -> ResolvedPathSnapshot:
    """从已打开目录 handle 取得允许根的实际路径与身份。"""
    if _IS_WINDOWS:
        handle: int | None = None
        failed = False
        try:
            try:
                handle = _windows_create_handle(path, is_directory=True, for_read=False)
                metadata = _windows_metadata_from_handle(handle)
                if not metadata.is_directory:
                    raise PathNotAllowedError("允许根目录不是目录")
                canonical_path = _windows_final_path(handle)
            except OSError:
                failed = True
            if failed:
                raise PathNotAllowedError("无法安全打开允许根目录")
            return ResolvedPathSnapshot(canonical_path, metadata)
        finally:
            if handle is not None:
                _windows_close_handle(handle)

    descriptor: int | None = None
    failed = False
    try:
        try:
            descriptor = os.open(path, _posix_open_flags(directory=True))
            stat_result = os.fstat(descriptor)
            if not stat.S_ISDIR(stat_result.st_mode):
                raise PathNotAllowedError("允许根目录不是目录")
            metadata = _metadata_from_stat(stat_result)
            canonical_path = _posix_final_path(descriptor)
        except OSError:
            failed = True
        if failed:
            raise PathNotAllowedError("无法安全打开允许根目录")
        return ResolvedPathSnapshot(canonical_path, metadata)
    finally:
        if descriptor is not None:
            os.close(descriptor)


def resolve_no_follow_snapshot(path: Path, root: Path) -> ResolvedPathSnapshot | None:
    """持有根与祖先对象直到最终 handle 路径验证完成。"""
    relative_parts = canonical_relative_parts(path, root)
    if relative_parts is None:
        raise PathNotAllowedError("请求的路径不在允许范围内")

    if _IS_WINDOWS:
        handles: list[int] = []
        missing = False
        failed = False
        final_path: Path | None = None
        final_metadata: FileMetadata | None = None
        try:
            try:
                root_handle = _windows_create_handle(root, is_directory=True, for_read=False)
                handles.append(root_handle)
                root_metadata = _windows_metadata_from_handle(root_handle)
                final_metadata = root_metadata
                if not root_metadata.is_directory:
                    raise PathNotAllowedError("允许根目录已发生变化")
                opened_root = _windows_final_path(root_handle)
                if not _same_canonical_path(opened_root, root):
                    raise PathNotAllowedError("允许根目录已发生变化")

                current = root
                for index, part in enumerate(relative_parts):
                    opened_parent = _windows_final_path(handles[-1])
                    if not _same_canonical_path(opened_parent, current):
                        raise PathNotAllowedError("请求路径的组件在验证期间发生变化")
                    current /= part
                    is_final = index == len(relative_parts) - 1
                    handle = _windows_create_handle(
                        current,
                        is_directory=not is_final,
                        for_read=False,
                    )
                    handles.append(handle)
                    metadata = _windows_metadata_from_handle(handle)
                    final_metadata = metadata
                    if not is_final and not metadata.is_directory:
                        raise PathNotAllowedError("请求路径的中间组件不是目录")

                final_handle = handles[-1]
                final_path = _windows_final_path(final_handle)
                if not _same_canonical_path(final_path, path):
                    raise PathNotAllowedError("请求的路径在验证期间发生变化")
                _ensure_contained(final_path, opened_root)
            except OSError as error:
                if _missing_path_error(error):
                    missing = True
                else:
                    failed = True
            if missing:
                return None
            if failed or final_path is None or final_metadata is None:
                raise PathNotAllowedError("无法安全解析请求的路径")
            return ResolvedPathSnapshot(final_path, final_metadata)
        finally:
            for handle in reversed(handles):
                _windows_close_handle(handle)

    if os.open not in os.supports_dir_fd:
        raise PathNotAllowedError("当前 POSIX 平台缺少安全相对打开能力")

    descriptors: list[int] = []
    missing = False
    failed = False
    final_path = None
    final_metadata = None
    try:
        try:
            root_fd = os.open(root, _posix_open_flags(directory=True))
            descriptors.append(root_fd)
            root_stat = os.fstat(root_fd)
            final_metadata = _metadata_from_stat(root_stat)
            if not stat.S_ISDIR(root_stat.st_mode):
                raise PathNotAllowedError("允许根目录已发生变化")
            opened_root = _posix_final_path(root_fd)
            if not _same_canonical_path(opened_root, root):
                raise PathNotAllowedError("允许根目录已发生变化")

            current_fd = root_fd
            for index, part in enumerate(relative_parts):
                is_final = index == len(relative_parts) - 1
                descriptor = os.open(
                    part,
                    _posix_open_flags(directory=not is_final),
                    dir_fd=current_fd,
                )
                descriptors.append(descriptor)
                stat_result = os.fstat(descriptor)
                final_metadata = _metadata_from_stat(stat_result)
                if not is_final and not stat.S_ISDIR(stat_result.st_mode):
                    raise PathNotAllowedError("请求路径的中间组件不是目录")
                if is_final and not (
                    stat.S_ISDIR(stat_result.st_mode) or stat.S_ISREG(stat_result.st_mode)
                ):
                    raise PathNotAllowedError("请求的路径类型不受支持")
                current_fd = descriptor

            final_fd = descriptors[-1]
            final_path = _posix_final_path(final_fd)
            if not _same_canonical_path(final_path, path):
                raise PathNotAllowedError("请求的路径在验证期间发生变化")
            _ensure_contained(final_path, opened_root)
        except OSError as error:
            if _missing_path_error(error):
                missing = True
            else:
                failed = True
        if missing:
            return None
        if failed or final_path is None or final_metadata is None:
            raise PathNotAllowedError("无法安全解析请求的路径")
        return ResolvedPathSnapshot(final_path, final_metadata)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def resolve_no_follow(path: Path, root: Path) -> Path | None:
    """返回不跟随任何请求组件解析出的规范路径。"""
    snapshot = resolve_no_follow_snapshot(path, root)
    return None if snapshot is None else snapshot.canonical_path


def stat_no_follow(path: Path) -> FileMetadata:
    """读取路径元数据。拒绝符号链接与 Windows 重解析点。"""
    if _IS_WINDOWS:
        handle: int | None = None
        failed = False
        try:
            handle = _windows_create_handle(path, is_directory=False, for_read=False)
            metadata = _windows_metadata_from_handle(handle)
        except OSError:
            failed = True
        finally:
            if handle is not None:
                _windows_close_handle(handle)
        if failed:
            raise PathNotAllowedError("无法安全访问请求的路径")
        return metadata

    failed = False
    try:
        result = path.stat(follow_symlinks=False)
    except OSError:
        failed = True
    if failed:
        raise PathNotAllowedError("无法安全访问请求的路径")
    file_attributes = getattr(result, "st_file_attributes", 0)
    if stat.S_ISLNK(result.st_mode) or file_attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        raise PathNotAllowedError("请求的路径包含不允许的链接")
    if not (stat.S_ISREG(result.st_mode) or stat.S_ISDIR(result.st_mode)):
        raise PathNotAllowedError("请求的路径类型不受支持")
    return _metadata_from_stat(result)


@contextmanager
def locked_scandir(
    path: Path,
    root: Path,
    expected_identity: FileIdentity | tuple[int, int],
) -> Iterator[Iterator[os.DirEntry[str]]]:
    """在目录身份与允许边界保持锁定期间枚举目录项。"""
    if _IS_WINDOWS:
        handle: int | None = None
        scanner: os.ScandirIterator[str] | None = None
        try:
            failed = False
            try:
                handle = _windows_create_handle(path, is_directory=True, for_read=False)
                metadata = _windows_metadata_from_handle(handle)
                if not metadata.is_directory:
                    raise PathNotAllowedError("请求的路径不是目录")
                _verify_expected_identity(metadata, expected_identity)
                final_path = _windows_final_path(handle)
                _ensure_contained(final_path, root)
                if not _same_canonical_path(final_path, path):
                    raise PathNotAllowedError("最终 handle 与请求路径不一致")
                scanner = os.scandir(path)
            except OSError:
                failed = True
            if failed:
                raise PathNotAllowedError("无法安全枚举请求的目录")
            assert scanner is not None
            yield scanner
        finally:
            try:
                if scanner is not None:
                    scanner.close()
            finally:
                if handle is not None:
                    _windows_close_handle(handle)
        return

    fd: int | None = None
    scanner = None
    flags = _posix_open_flags(directory=True)
    try:
        failed = False
        try:
            fd = os.open(path, flags)
            metadata = _metadata_from_stat(os.fstat(fd))
            if not metadata.is_directory:
                raise PathNotAllowedError("请求的路径不是目录")
            _verify_expected_identity(metadata, expected_identity)
            final_path = _posix_final_path(fd)
            _ensure_contained(final_path, root)
            if not _same_canonical_path(final_path, path):
                raise PathNotAllowedError("最终 fd 与请求路径不一致")
            scanner = os.scandir(fd)
        except OSError:
            failed = True
        if failed:
            raise PathNotAllowedError("无法安全枚举请求的目录")
        assert scanner is not None
        yield scanner
    finally:
        try:
            if scanner is not None:
                scanner.close()
        finally:
            if fd is not None:
                os.close(fd)


@contextmanager
def open_verified_binary(
    path: Path,
    root: Path,
    expected_identity: FileIdentity | tuple[int, int],
) -> Iterator[BinaryIO]:
    """打开经身份与最终路径验证的普通二进制文件。"""
    if _IS_WINDOWS:
        handle: int | None = None
        descriptor: int | None = None
        file_object: BinaryIO | None = None
        try:
            failed = False
            try:
                handle = _windows_create_handle(path, is_directory=False, for_read=True)
                metadata = _windows_metadata_from_handle(handle)
                if metadata.is_directory:
                    raise PathNotAllowedError("请求的路径不是普通文件")
                _verify_expected_identity(metadata, expected_identity)
                final_path = _windows_final_path(handle)
                _ensure_contained(final_path, root)
                if not _same_canonical_path(final_path, path):
                    raise PathNotAllowedError("最终 handle 与请求路径不一致")
                descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
                handle = None
                file_object = os.fdopen(descriptor, "rb", closefd=True)
                descriptor = None
            except OSError:
                failed = True
            if failed:
                raise PathNotAllowedError("无法安全打开请求的文件")
            assert file_object is not None
            yield file_object
        finally:
            if file_object is not None:
                file_object.close()
            elif descriptor is not None:
                os.close(descriptor)
            elif handle is not None:
                _windows_close_handle(handle)
        return

    descriptor = None
    file_object = None
    flags = _posix_open_flags(directory=False)
    try:
        failed = False
        try:
            descriptor = os.open(path, flags)
            stat_result = os.fstat(descriptor)
            metadata = _metadata_from_stat(stat_result)
            if metadata.is_directory or not stat.S_ISREG(stat_result.st_mode):
                raise PathNotAllowedError("请求的路径不是普通文件")
            _verify_expected_identity(metadata, expected_identity)
            final_path = _posix_final_path(descriptor)
            _ensure_contained(final_path, root)
            if not _same_canonical_path(final_path, path):
                raise PathNotAllowedError("最终 fd 与请求路径不一致")
            file_object = os.fdopen(descriptor, "rb", closefd=True)
            descriptor = None
        except OSError:
            failed = True
        if failed:
            raise PathNotAllowedError("无法安全打开请求的文件")
        assert file_object is not None
        yield file_object
    finally:
        if file_object is not None:
            file_object.close()
        elif descriptor is not None:
            os.close(descriptor)


def fstat_metadata(file_object: BinaryIO) -> FileMetadata:
    """从已打开文件对象读取同一对象的当前元数据。"""
    if _IS_WINDOWS:
        return _windows_metadata_from_handle(msvcrt.get_osfhandle(file_object.fileno()))
    return _metadata_from_stat(os.fstat(file_object.fileno()))
