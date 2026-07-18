"""允许根目录、来源发现与受限读取。"""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Iterable
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath, PureWindowsPath

from .errors import LimitExceededError, PathNotAllowedError, UnsupportedFileError
from .models import AllowedRoot, ResolvedSource, ResolvedTarget
from .safe_fs import (
    FILE_ATTRIBUTE_REPARSE_POINT,
    FileIdentity,
    FileMetadata,
    canonical_path_key,
    canonical_relative_parts,
    canonicalize_allowed_root,
    fstat_metadata,
    locked_scandir,
    open_verified_binary,
    resolve_no_follow,
    resolve_no_follow_snapshot,
    stat_no_follow,
)

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".rst", ".pdf"}
MAX_GLOB_PATTERN_CHARS = 4096
MAX_GLOB_PATTERN_PARTS = 256


def _root_id(path: Path) -> str:
    """根据规范化根路径生成稳定的公开标识。"""
    normalized = canonical_path_key(path)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def _reject_nul_path(value: str | Path) -> None:
    """在进入 pathlib 或原生 API 前拒绝 NUL 路径。"""
    if "\0" in os.fspath(value):
        raise PathNotAllowedError("请求的路径包含非法字符")


def _is_symlink_loop_runtime_error(error: RuntimeError) -> bool:
    """仅识别 pathlib 为 ELOOP 生成的固定 RuntimeError。"""
    return (
        len(error.args) == 1
        and isinstance(error.args[0], str)
        and error.args[0].startswith("Symlink loop from ")
    )


def build_allowed_roots(paths: Iterable[Path]) -> tuple[AllowedRoot, ...]:
    """严格解析、去重并按最深目录优先构建允许根目录。"""
    roots: dict[FileIdentity, Path] = {}
    failed = False
    try:
        for path in paths:
            _reject_nul_path(path)
            try:
                resolved = Path(path).resolve(strict=True)
            except RuntimeError as error:
                if not _is_symlink_loop_runtime_error(error):
                    raise
                failed = True
                break
            snapshot = canonicalize_allowed_root(resolved)
            roots.setdefault(snapshot.metadata.identity, snapshot.canonical_path)
    except OSError:
        failed = True

    if failed or not roots:
        raise PathNotAllowedError("允许根目录配置无效")

    ordered = sorted(
        roots.values(),
        key=lambda root: (-len(root.parts), canonical_path_key(root)),
    )
    return tuple(AllowedRoot(root_id=_root_id(root), path=root) for root in ordered)


def _is_contained(candidate: Path, root: Path) -> bool:
    """使用路径组件语义判断候选路径是否位于根目录内。"""
    return canonical_relative_parts(candidate, root) is not None


def resolve_requested_path(
    requested_path: str | Path,
    roots: tuple[AllowedRoot, ...],
) -> ResolvedTarget:
    """严格解析请求路径。将其唯一归属到允许根目录。"""
    _reject_nul_path(requested_path)
    requested = Path(requested_path)
    matches: list[tuple[Path, AllowedRoot]] = []
    failed = False

    if requested.is_absolute():
        if ".." in requested.parts:
            failed = True
        else:
            lexical_candidate = Path(os.path.abspath(requested))
            owner = next(
                (root for root in roots if _is_contained(lexical_candidate, root.path)),
                None,
            )
            if owner is None:
                failed = True
            else:
                candidate = resolve_no_follow(lexical_candidate, owner.path)
                if candidate is None:
                    failed = True
                elif _is_contained(candidate, owner.path):
                    return ResolvedTarget(absolute_path=candidate, root=owner)
                else:
                    failed = True
    else:
        if ".." in requested.parts:
            failed = True
        else:
            for search_root in roots:
                lexical_candidate = search_root.path / requested
                owner = next(
                    (root for root in roots if _is_contained(lexical_candidate, root.path)),
                    search_root,
                )
                candidate = resolve_no_follow(lexical_candidate, owner.path)
                if candidate is None:
                    continue
                if _is_contained(candidate, owner.path):
                    matches.append((candidate, owner))

            distinct_paths = {os.path.normcase(str(candidate)) for candidate, _ in matches}
            if len(distinct_paths) == 1:
                candidate = matches[0][0]
                owner = matches[0][1]
                return ResolvedTarget(absolute_path=candidate, root=owner)
            if len(distinct_paths) > 1:
                raise PathNotAllowedError("相对路径无法唯一解析")

    if failed or not matches:
        raise PathNotAllowedError("请求的路径不在允许范围内")
    raise PathNotAllowedError("相对路径无法唯一解析")


def _make_source(
    candidate: Path,
    root: AllowedRoot,
    metadata: FileMetadata,
) -> ResolvedSource:
    """根据已锁定快照构建不泄露绝对路径的来源记录。"""
    outside = False
    try:
        relative = candidate.relative_to(root.path)
    except ValueError:
        outside = True
    if outside:
        raise PathNotAllowedError("请求的路径不在允许范围内")
    relative_path = PurePosixPath(*relative.parts)
    return ResolvedSource(
        absolute_path=candidate,
        root_path=root.path,
        root_id=root.root_id,
        relative_path=relative_path,
        source_path=PurePosixPath(root.root_id) / relative_path,
        size_bytes=metadata.size_bytes,
        mtime_ns=metadata.mtime_ns,
        device_id=metadata.device_id,
        file_id=metadata.file_id,
    )


def _validate_globs(include_globs: tuple[str, ...]) -> None:
    """拒绝可能脱离相对 POSIX 路径语义的匹配表达式。"""
    for pattern in include_globs:
        if "\0" in pattern:
            raise PathNotAllowedError("包含模式含有非法字符")
        if (
            len(pattern) > MAX_GLOB_PATTERN_CHARS
            or len(pattern.split("/")) > MAX_GLOB_PATTERN_PARTS
        ):
            raise LimitExceededError("包含模式复杂度超过安全限制")
        posix_pattern = PurePosixPath(pattern)
        windows_pattern = PureWindowsPath(pattern)
        if (
            not pattern
            or posix_pattern.is_absolute()
            or windows_pattern.is_absolute()
            or bool(windows_pattern.drive)
            or ".." in posix_pattern.parts
            or ".." in windows_pattern.parts
            or "\\" in pattern
        ):
            raise PathNotAllowedError("包含模式必须使用安全的相对 POSIX 路径")


def _matches_globs(relative_path: PurePosixPath, include_globs: tuple[str, ...]) -> bool:
    """按相对根目录的 POSIX 路径匹配包含模式。"""
    if not include_globs:
        return True
    path_parts = relative_path.parts

    def matches_pattern(pattern: str) -> bool:
        pattern_parts = tuple(pattern.split("/"))
        states = {0}
        for pattern_part in pattern_parts:
            if pattern_part == "**":
                states = set(range(min(states), len(path_parts) + 1)) if states else set()
            else:
                states = {
                    path_index + 1
                    for path_index in states
                    if path_index < len(path_parts)
                    and fnmatchcase(path_parts[path_index], pattern_part)
                }
            if not states:
                return False
        return len(path_parts) in states

    return any(matches_pattern(pattern) for pattern in include_globs)


def _ensure_candidate_contained(candidate: Path, root: AllowedRoot) -> None:
    """在构建来源前再次执行组件级边界检查。"""
    if not _is_contained(candidate, root.path):
        raise PathNotAllowedError("请求的路径不在允许范围内")


def discover_source_files(
    target: ResolvedTarget,
    recursive: bool,
    include_globs: tuple[str, ...],
    max_files: int,
    max_total_bytes: int,
    max_entries: int = 20_000,
    max_directories: int = 2_000,
    max_depth: int = 64,
) -> tuple[ResolvedSource, ...]:
    """以显式有界遍历发现允许根目录内的支持文件。"""
    _validate_globs(include_globs)
    if min(max_files, max_total_bytes, max_entries, max_directories) < 1 or max_depth < 0:
        raise LimitExceededError("发现限制配置无效")

    root = target.root
    candidate = target.absolute_path
    _ensure_candidate_contained(candidate, root)
    entry_snapshot = resolve_no_follow_snapshot(candidate, root.path)
    if entry_snapshot is None or entry_snapshot.canonical_path != candidate:
        raise PathNotAllowedError("请求的路径在解析后发生变化")
    initial = entry_snapshot.metadata
    if not initial.is_directory:
        if candidate.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise UnsupportedFileError("文件格式不受支持")
        relative = PurePosixPath(*candidate.relative_to(root.path).parts)
        if not _matches_globs(relative, include_globs):
            return ()
        if max_files < 1:
            raise LimitExceededError("发现文件数量超过限制")
        if initial.size_bytes > max_total_bytes:
            raise LimitExceededError("发现文件总字节数超过限制")
        return (_make_source(candidate, root, initial),)

    sources: list[ResolvedSource] = []
    total_bytes = 0
    entries_seen = 0
    directories_seen = 1
    if directories_seen > max_directories:
        raise LimitExceededError("扫描目录数量超过限制")
    stack: list[tuple[Path, int, FileIdentity]] = [(candidate, 0, initial.identity)]
    visited: set[FileIdentity] = set()

    while stack:
        directory, depth, expected_identity = stack.pop()
        if expected_identity in visited:
            continue
        visited.add(expected_identity)

        child_directories: list[tuple[Path, int, FileIdentity]] = []
        scan_failed = False
        try:
            with locked_scandir(directory, root.path, expected_identity) as scanner:
                bounded_entries = []
                for entry in scanner:
                    entries_seen += 1
                    if entries_seen > max_entries:
                        raise LimitExceededError("扫描条目数量超过限制")
                    bounded_entries.append(entry)

                bounded_entries.sort(key=lambda item: (item.name.casefold(), item.name))
                for entry in bounded_entries:
                    entry_stat = entry.stat(follow_symlinks=False)
                    attributes = getattr(entry_stat, "st_file_attributes", 0)
                    if stat.S_ISLNK(entry_stat.st_mode) or (
                        attributes & FILE_ATTRIBUTE_REPARSE_POINT
                    ):
                        raise PathNotAllowedError("扫描目录包含不允许的链接")

                    entry_path = directory / entry.name
                    _ensure_candidate_contained(entry_path, root)
                    metadata = stat_no_follow(entry_path)
                    if metadata.is_directory:
                        if not recursive:
                            continue
                        child_depth = depth + 1
                        if child_depth > max_depth:
                            raise LimitExceededError("扫描目录深度超过限制")
                        directories_seen += 1
                        if directories_seen > max_directories:
                            raise LimitExceededError("扫描目录数量超过限制")
                        child_directories.append((entry_path, child_depth, metadata.identity))
                    elif stat.S_ISREG(entry_stat.st_mode):
                        if entry_path.suffix.lower() not in SUPPORTED_SUFFIXES:
                            continue
                        relative = PurePosixPath(*entry_path.relative_to(root.path).parts)
                        if not _matches_globs(relative, include_globs):
                            continue
                        if len(sources) + 1 > max_files:
                            raise LimitExceededError("发现文件数量超过限制")
                        next_total_bytes = total_bytes + metadata.size_bytes
                        if next_total_bytes > max_total_bytes:
                            raise LimitExceededError("发现文件总字节数超过限制")
                        total_bytes = next_total_bytes
                        sources.append(_make_source(entry_path, root, metadata))
        except OSError:
            scan_failed = True

        if scan_failed:
            raise PathNotAllowedError("无法安全枚举请求的目录")

        for child in reversed(child_directories):
            stack.append(child)

    sources.sort(
        key=lambda source: (
            source.source_path.as_posix().casefold(),
            source.source_path.as_posix(),
        )
    )
    return tuple(sources)


def read_validated_bytes(source: ResolvedSource, max_bytes: int) -> bytes:
    """从同一已验证文件对象读取最多 ``max_bytes + 1`` 字节。"""
    if source.absolute_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise UnsupportedFileError("文件格式不受支持")
    if max_bytes < 1:
        raise LimitExceededError("文件读取字节限制无效")

    expected = FileIdentity(source.device_id, source.file_id)
    read_failed = False
    try:
        with open_verified_binary(source.absolute_path, source.root_path, expected) as file_object:
            before = fstat_metadata(file_object)
            if (
                before.identity != expected
                or before.size_bytes != source.size_bytes
                or before.mtime_ns != source.mtime_ns
            ):
                raise PathNotAllowedError("请求的文件在发现后发生变化")
            data = file_object.read(max_bytes + 1)
            after = fstat_metadata(file_object)
            if (
                after.identity != expected
                or after.size_bytes != before.size_bytes
                or after.mtime_ns != before.mtime_ns
            ):
                raise PathNotAllowedError("请求的文件在读取期间发生变化")
            if len(data) > max_bytes:
                raise LimitExceededError("文件大小超过读取限制")
            if len(data) != after.size_bytes:
                raise PathNotAllowedError("请求的文件在读取期间发生变化")
    except OSError:
        read_failed = True

    if read_failed:
        raise PathNotAllowedError("无法安全读取请求的文件")
    return data
