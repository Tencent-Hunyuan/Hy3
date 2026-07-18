"""analyze_project_context tool.

Reads user-specified local files inside a strict sandbox and passes their
contents as DATA to Hy3 for structured analysis. No file is ever executed;
no path may escape ``HY3_WORKSPACE_ROOT``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .._runtime import get_client, load_prompt
from ..config import Settings
from ..exceptions import FileTooLargeError, WorkspaceAccessError
from ..schemas import AnalyzeProjectContextInput, AnalyzeProjectContextOutput

PROMPT_NAME = "analyze_context"

# --- Allow / deny lists ----------------------------------------------------

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".md",
        ".txt",
        ".json",
        ".toml",
        ".yaml",
        ".yml",
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rs",
    }
)

# Directory names that are never traversed.
DENIED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "dist",
        "build",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "target",
        ".idea",
        ".vscode",
        ".eggs",
    }
)

# Exact sensitive file basenames.
DENIED_BASENAMES: frozenset[str] = frozenset(
    {
        ".env",
        ".npmrc",
        ".pypirc",
        ".netrc",
        ".htpasswd",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "credentials",
        ".aws_credentials",
    }
)

# Sensitive suffixes.
DENIED_SUFFIXES: frozenset[str] = frozenset(
    {
        ".env",  # catches config.env etc.
        ".pem",
        ".key",
        ".crt",
        ".cer",
        ".pub",
        ".p12",
        ".pfx",
        ".keystore",
        ".jks",
        ".asc",
        ".gpg",
    }
)


def is_env_variant(name: str) -> bool:
    """Match ``.env`` and its variants (.env.local, .env.production, ...)."""
    return name == ".env" or name.startswith(".env.")


def is_denied_name(name: str) -> bool:
    name_l = name.lower()
    if is_env_variant(name_l):
        return True
    if name_l in DENIED_BASENAMES:
        return True
    return any(name_l.endswith(suf) for suf in DENIED_SUFFIXES)


def is_allowed_extension(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_EXTENSIONS


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_within_workspace(path_str: str, workspace_root: Path) -> Path:
    """Resolve ``path_str`` against the workspace and verify it stays inside.

    Handles:
      * relative paths (anchored to workspace_root),
      * absolute paths (must already be inside workspace_root),
      * ``..`` traversal,
      * symlinks whose target escapes the workspace.

    Raises WorkspaceAccessError otherwise.
    """
    raw = path_str.strip()
    if not raw:
        raise WorkspaceAccessError("An empty path was supplied.")

    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (workspace_root / candidate).resolve()

    # ``resolve`` follows symlinks and normalises ``..``; ensure the real target
    # is still inside the workspace. This single check covers traversal and
    # symlink escapes alike (defence in depth).
    if not _within(resolved, workspace_root):
        raise WorkspaceAccessError(
            f"Path '{path_str}' resolves outside the workspace root and was refused."
        )

    return resolved


def iter_target_files(
    path: Path,
    max_depth: int,
    *,
    workspace_root: Path,
) -> list[Path]:
    """Return the list of readable files under ``path``.

    For a file path: return ``[path]`` (extension is checked later).
    For a directory: walk up to ``max_depth`` levels deep, skipping denied
    directories and denied file names.
    """
    if path.is_file():
        # Apply the same deny-list + extension checks used for directory walks,
        # so a user explicitly requesting ".env" or "key.pem" is still refused.
        if is_denied_name(path.name) or not is_allowed_extension(path):
            return []
        return [path]

    if not path.is_dir():
        return []

    collected: list[Path] = []
    # depth is relative to the requested directory itself.
    for root, dirs, files in os.walk(path):
        # Compute depth relative to the requested directory.
        rel = Path(root).relative_to(path)
        depth = 0 if str(rel) == "." else len(rel.parts)
        if depth > max_depth:
            dirs[:] = []  # do not descend further
            continue
        # prune denied directories in-place
        dirs[:] = [d for d in dirs if d not in DENIED_DIRS and not is_denied_name(d)]
        for fname in files:
            fpath = Path(root) / fname
            if not _within(fpath, workspace_root):
                continue
            if is_denied_name(fname):
                continue
            if not is_allowed_extension(fpath):
                continue
            collected.append(fpath)
    return collected


def _looks_binary(data: bytes) -> bool:
    """Heuristic: a null byte in the first 8 KiB suggests a binary file."""
    return b"\x00" in data[:8192]


@dataclass
class CollectedFile:
    rel_path: str
    content: str


@dataclass
class ProjectContextData:
    files: list[CollectedFile] = field(default_factory=list)
    structure: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_bytes: int = 0


def collect_context(
    paths: list[str],
    settings: Settings,
    *,
    max_depth: int = 2,
) -> ProjectContextData:
    """Read all allowed files under the given paths, respecting every limit."""
    workspace_root = settings.require_workspace_root()
    max_file = settings.max_file_size_bytes
    max_total = settings.max_total_size_bytes
    data = ProjectContextData()

    seen: set[Path] = set()
    for raw_path in paths:
        resolved = resolve_within_workspace(raw_path, workspace_root)
        targets = iter_target_files(resolved, max_depth, workspace_root=workspace_root)
        for fpath in targets:
            if fpath in seen:
                continue
            seen.add(fpath)
            # Defence in depth: a symlink discovered inside the workspace may
            # resolve to a target outside it. Refuse before reading.
            real = fpath.resolve()
            if not _within(real, workspace_root):
                raise WorkspaceAccessError(
                    f"Symlink '{fpath.name}' resolves outside the workspace root and was refused."
                )
            try:
                size = fpath.stat().st_size
            except OSError as exc:
                data.warnings.append(f"Could not stat {fpath}: {exc.strerror or exc}")
                continue
            if size > max_file:
                raise FileTooLargeError(
                    f"File '{fpath.name}' is {size} bytes, exceeding the "
                    f"{max_file}-byte single-file limit (HY3_MAX_FILE_SIZE_BYTES)."
                )
            if data.total_bytes + size > max_total:
                raise FileTooLargeError(
                    f"Total read size would exceed the {max_total}-byte limit "
                    "(HY3_MAX_TOTAL_SIZE_BYTES). Narrow the requested paths."
                )
            try:
                raw = fpath.read_bytes()
            except OSError as exc:
                data.warnings.append(f"Could not read {fpath}: {exc.strerror or exc}")
                continue
            if _looks_binary(raw):
                data.warnings.append(f"Skipped binary-looking file: {fpath.name}")
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                data.warnings.append(f"Skipped non-UTF-8 file: {fpath.name}")
                continue
            rel = fpath.relative_to(workspace_root)
            data.files.append(CollectedFile(rel_path=str(rel), content=text))
            data.structure.append(str(rel))
            data.total_bytes += size

    if not data.files:
        data.warnings.append("No readable allowed files were found in the given paths.")
    return data


def _build_user_prompt(
    data: ProjectContextData, settings: Settings, input: AnalyzeProjectContextInput
) -> str:
    workspace_root = settings.workspace_root
    files_payload = []
    for cf in data.files:
        files_payload.append({"path": cf.rel_path, "content": cf.content})
    return json.dumps(
        {
            "workspace_root": str(workspace_root) if workspace_root else None,
            "files": files_payload,
            "structure": data.structure,
            "warnings": data.warnings,
            "include_content_summary": input.include_content_summary,
            "output_language": input.output_language,
        },
        ensure_ascii=False,
        indent=2,
    )


async def run(
    data: AnalyzeProjectContextInput, settings: Settings | None = None
) -> AnalyzeProjectContextOutput:
    from ..config import load_settings

    settings = settings or load_settings()
    context = collect_context(data.paths, settings, max_depth=data.max_depth)
    client = get_client(settings)
    result = await client.generate_structured(
        system_prompt=load_prompt(PROMPT_NAME),
        user_prompt=_build_user_prompt(context, settings, data),
        response_model=AnalyzeProjectContextOutput,
    )
    # Surface collection-time warnings to the caller.
    if context.warnings:
        result = result.model_copy(update={"warnings": list(result.warnings) + context.warnings})
    return result
