from __future__ import annotations

from pathlib import Path


def fixture_root() -> Path:
    return _data_root("fixtures")


def evaluation_root() -> Path:
    return _data_root("evals")


def default_result_root() -> Path:
    return Path.cwd() / "replaylab-results"


def _data_root(name: str) -> Path:
    packaged = Path(__file__).resolve().parent / "data" / name
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[3] / name
