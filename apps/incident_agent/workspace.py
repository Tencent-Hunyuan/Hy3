from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory


ALLOWED_EXTENSIONS = {
    ".py",
    ".txt",
    ".log",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
}
MAX_FILES = 8
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024


class WorkspaceError(ValueError):
    pass


def validate_files(files: Sequence[tuple[str, bytes]]) -> dict[str, str]:
    if not files or len(files) > MAX_FILES:
        raise WorkspaceError("Provide between 1 and 8 files.")

    decoded: dict[str, str] = {}
    total = 0
    for raw_name, content in files:
        name = Path(raw_name).name
        if (
            not name
            or name != raw_name
            or "/" in raw_name
            or "\\" in raw_name
            or Path(name).suffix.lower() not in ALLOWED_EXTENSIONS
        ):
            raise WorkspaceError(f"Unsupported filename: {raw_name}")
        if name in decoded:
            raise WorkspaceError(f"Duplicate filename: {name}")
        if len(content) > MAX_FILE_BYTES:
            raise WorkspaceError(f"File is larger than 512 KiB: {name}")

        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise WorkspaceError("Files exceed the 2 MiB total limit.")
        if b"\x00" in content:
            raise WorkspaceError(f"Binary content is not supported: {name}")
        try:
            decoded[name] = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError(f"File is not valid UTF-8: {name}") from exc

    return decoded


@contextmanager
def incident_workspace(files: Sequence[tuple[str, bytes]]) -> Iterator[Path]:
    decoded = validate_files(files)
    with TemporaryDirectory(prefix="hy3-incident-") as temporary_directory:
        root = Path(temporary_directory)
        for name, content in decoded.items():
            (root / name).write_text(content, encoding="utf-8")
        yield root
