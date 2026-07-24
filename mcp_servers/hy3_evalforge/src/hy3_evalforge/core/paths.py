"""Constrained local artifact access with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from hy3_evalforge.errors import ErrorCode, EvalForgeError


class ArtifactStore:
    """Read and write only files that resolve below one allowed project root."""

    def __init__(self, allowed_root: Path, *, max_file_bytes: int = 10 * 1024 * 1024) -> None:
        self._allowed_root = allowed_root.expanduser().resolve(strict=True)
        if not self._allowed_root.is_dir():
            raise EvalForgeError(ErrorCode.PATH_DENIED, "The allowed root must be a directory.")
        self._max_file_bytes = max_file_bytes

    @property
    def allowed_root(self) -> Path:
        """Return the resolved root used for all containment checks."""
        return self._allowed_root

    def resolve(self, requested_path: str | Path, *, must_exist: bool = False) -> Path:
        """Resolve a path and reject traversal or symlink resolution outside the allowed root."""
        requested = Path(requested_path).expanduser()
        candidate = requested if requested.is_absolute() else self._allowed_root / requested
        try:
            resolved = candidate.resolve(strict=must_exist)
            resolved.relative_to(self._allowed_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise EvalForgeError(
                ErrorCode.PATH_DENIED, "Path is outside EVALFORGE_ALLOWED_ROOT."
            ) from exc
        return resolved

    def read_text(self, requested_path: str | Path) -> str:
        """Read a bounded UTF-8 file after containment and type checks."""
        path = self.resolve(requested_path, must_exist=True)
        if not path.is_file():
            raise EvalForgeError(ErrorCode.INPUT_ERROR, "Expected a regular input file.")
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise EvalForgeError(
                ErrorCode.INPUT_ERROR, "Could not inspect the input file."
            ) from exc
        if size > self._max_file_bytes:
            raise EvalForgeError(
                ErrorCode.INPUT_ERROR,
                f"Input file exceeds the {self._max_file_bytes} byte limit.",
            )
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise EvalForgeError(
                ErrorCode.INPUT_ERROR, "Input file must be readable UTF-8 text."
            ) from exc

    def read_json(self, requested_path: str | Path) -> Any:
        """Read exactly one JSON value; mixed text and multiple objects are rejected."""
        try:
            return json.loads(self.read_text(requested_path))
        except json.JSONDecodeError as exc:
            raise EvalForgeError(
                ErrorCode.INPUT_ERROR, "Input file must contain one valid JSON value."
            ) from exc

    def write_json(
        self, requested_path: str | Path, value: Any, *, overwrite: bool = False
    ) -> Path:
        """Atomically write canonical JSON without replacing existing artifacts by default."""
        payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        return self.write_text(requested_path, payload, overwrite=overwrite)

    def write_text(
        self, requested_path: str | Path, content: str, *, overwrite: bool = False
    ) -> Path:
        """Atomically write one bounded artifact beneath the allowed root."""
        path = self.resolve(requested_path)
        if len(content.encode("utf-8")) > self._max_file_bytes:
            raise EvalForgeError(
                ErrorCode.INPUT_ERROR,
                f"Artifact exceeds the {self._max_file_bytes} byte limit.",
            )
        parent = path.parent
        if not parent.is_dir():
            raise EvalForgeError(ErrorCode.PATH_DENIED, "Artifact parent directory does not exist.")
        if path.exists() and not overwrite:
            raise EvalForgeError(
                ErrorCode.ARTIFACT_CONFLICT,
                "Artifact already exists; set overwrite=true to replace it.",
            )

        descriptor = -1
        temporary_path: Path | None = None
        try:
            descriptor, raw_path = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=parent, text=True
            )
            temporary_path = Path(raw_path)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                descriptor = -1
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        except OSError as exc:
            raise EvalForgeError(
                ErrorCode.INPUT_ERROR, "Could not atomically write the artifact."
            ) from exc
        finally:
            if descriptor != -1:
                os.close(descriptor)
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return path
