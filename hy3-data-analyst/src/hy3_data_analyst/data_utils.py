"""Safe file I/O and path handling for data files."""

from pathlib import Path

import pandas as pd

from .config import WORKSPACE_ROOT


def get_workspace_root() -> Path:
    return WORKSPACE_ROOT


def safe_path(rel_or_abs: str) -> Path:
    """Resolve a path and ensure it stays inside the workspace root.

    Raises ValueError if the resolved path escapes the workspace (directory traversal).
    """
    p = Path(rel_or_abs)
    if not p.is_absolute():
        p = WORKSPACE_ROOT / p
    resolved = p.resolve()
    try:
        resolved.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        raise ValueError(
            f"路径不在工作区内: {rel_or_abs}。只允许访问 {WORKSPACE_ROOT} 下的文件。\n"
            f"Path escapes workspace: {rel_or_abs}. Only files under {WORKSPACE_ROOT} are allowed."
        )
    return resolved


def read_dataframe(file_path: Path) -> pd.DataFrame:
    """Read a CSV, JSON, or Excel file into a pandas DataFrame.

    Raises FileNotFoundError if the file doesn't exist, ValueError for unsupported formats.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在 / File not found: {file_path}")

    suffix = file_path.suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(file_path)
        elif suffix == ".json":
            return pd.read_json(file_path)
        elif suffix in (".xlsx", ".xls"):
            return pd.read_excel(file_path)
        else:
            raise ValueError(
                f"不支持的文件格式: {suffix}。支持的格式: .csv, .json, .xlsx, .xls\n"
                f"Unsupported file format: {suffix}. Supported: .csv, .json, .xlsx, .xls"
            )
    except Exception as e:
        raise RuntimeError(
            f"读取文件失败 / Failed to read file: {file_path}\n{str(e)}"
        ) from e
