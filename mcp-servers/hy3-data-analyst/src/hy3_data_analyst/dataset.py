"""Safe, dependency-light CSV/JSON profiling."""

from __future__ import annotations

import csv
import json
import math
import os
import re
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any

from .config import Settings

SUPPORTED_SUFFIXES = {".csv", ".json", ".jsonl", ".ndjson"}
_INTEGER_RE = re.compile(r"^[+-]?\d+$")
_MISSING_STRINGS = {"", "na", "n/a", "null", "none", "nan"}


class DatasetError(ValueError):
    """Raised when a dataset cannot be read safely."""


def profile_dataset_file(
    file_path: str,
    *,
    max_rows: int = 10_000,
    sample_rows: int = 5,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Return a JSON-serializable profile for a local CSV, JSON, or JSONL file."""
    config = settings or Settings.from_env()
    max_rows = _bounded_int("max_rows", max_rows, minimum=1, maximum=100_000)
    sample_rows = _bounded_int("sample_rows", sample_rows, minimum=0, maximum=20)
    path = _resolve_path(file_path, config)
    rows, truncated = _read_rows(path, max_rows=max_rows)
    columns = _ordered_columns(rows)

    return {
        "source": {
            "file": str(path.relative_to(config.data_dir)),
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": path.stat().st_size,
        },
        "rows_scanned": len(rows),
        "truncated": truncated,
        "column_count": len(columns),
        "columns": [_column_profile(name, rows) for name in columns],
        "sample_rows": rows[:sample_rows],
    }


def _resolve_path(file_path: str, settings: Settings) -> Path:
    if not file_path.strip():
        raise DatasetError("file_path must not be empty")
    root = settings.data_dir
    candidate = Path(file_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()

    try:
        inside_root = os.path.commonpath((str(root), str(candidate))) == str(root)
    except ValueError:
        inside_root = False
    if not inside_root:
        raise DatasetError(f"file_path must stay inside HY3_DATA_DIR ({root})")
    if not candidate.exists():
        raise DatasetError(f"dataset not found: {file_path}")
    if not candidate.is_file():
        raise DatasetError(f"dataset is not a regular file: {file_path}")
    if candidate.suffix.lower() not in SUPPORTED_SUFFIXES:
        allowed = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise DatasetError(f"unsupported dataset format; expected one of: {allowed}")
    size = candidate.stat().st_size
    if size > settings.max_file_bytes:
        raise DatasetError(
            f"dataset is {size} bytes, exceeding HY3_MAX_FILE_BYTES={settings.max_file_bytes}"
        )
    return candidate


def _read_rows(path: Path, *, max_rows: int) -> tuple[list[dict[str, Any]], bool]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        row_iter = _iter_csv(path)
    elif suffix in {".jsonl", ".ndjson"}:
        row_iter = _iter_jsonl(path)
    else:
        row_iter = _iter_json(path)

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(row_iter):
        if index >= max_rows:
            return rows, True
        rows.append(_normalize_row(row))
    return rows, False


def _iter_csv(path: Path) -> Iterator[dict[str, Any]]:
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
        with handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise DatasetError("CSV file has no header row")
            for row in reader:
                yield dict(row)
    except UnicodeDecodeError as exc:
        raise DatasetError("dataset must be UTF-8 encoded") from exc
    except csv.Error as exc:
        raise DatasetError(f"invalid CSV: {exc}") from exc


def _iter_json(path: Path) -> Iterator[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except UnicodeDecodeError as exc:
        raise DatasetError("dataset must be UTF-8 encoded") from exc
    except json.JSONDecodeError as exc:
        raise DatasetError(f"invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    records: Iterable[Any]
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        list_values = [value for value in payload.values() if isinstance(value, list)]
        records = list_values[0] if len(payload) == 1 and list_values else [payload]
    else:
        raise DatasetError("JSON root must be an object, an array of objects, or an object list")

    for index, record in enumerate(records, start=1):
        if not isinstance(record, Mapping):
            raise DatasetError(f"JSON record {index} is not an object")
        yield dict(record)


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise DatasetError(f"invalid JSONL on line {line_number}") from exc
                if not isinstance(record, Mapping):
                    raise DatasetError(f"JSONL record on line {line_number} is not an object")
                yield dict(record)
    except UnicodeDecodeError as exc:
        raise DatasetError("dataset must be UTF-8 encoded") from exc


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _normalize_value(value) for key, value in row.items()}


def _normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _ordered_columns(rows: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for row in rows:
        for name in row:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
    return ordered


def _column_profile(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [row.get(name) for row in rows]
    present = [value for value in values if not _is_missing(value)]
    inferred_type = _infer_type(present)
    result: dict[str, Any] = {
        "name": name,
        "type": inferred_type,
        "non_null_count": len(present),
        "missing_count": len(values) - len(present),
        "unique_count": len({_stable_value(value) for value in present}),
    }
    if inferred_type in {"integer", "number"} and present:
        numbers = [_to_float(value) for value in present]
        result["numeric"] = {
            "min": min(numbers),
            "max": max(numbers),
            "mean": round(fmean(numbers), 6),
        }
    return result


def _infer_type(values: list[Any]) -> str:
    if not values:
        return "empty"
    if all(_is_boolean(value) for value in values):
        return "boolean"
    if all(_is_integer(value) for value in values):
        return "integer"
    if all(_is_number(value) for value in values):
        return "number"
    if all(_is_datetime(value) for value in values):
        return "datetime"
    return "string"


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and value.strip().lower() in _MISSING_STRINGS


def _is_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    return isinstance(value, str) and value.strip().lower() in {"true", "false"}


def _is_integer(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, str) and bool(_INTEGER_RE.fullmatch(value.strip()))


def _is_number(value: Any) -> bool:
    try:
        _to_float(value)
    except (TypeError, ValueError):
        return False
    return True


def _to_float(value: Any) -> float:
    if isinstance(value, bool):
        raise TypeError("booleans are not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite numbers are not supported")
    return number


def _is_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    candidate = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return True


def _stable_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _bounded_int(name: str, value: int, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DatasetError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise DatasetError(f"{name} must be between {minimum} and {maximum}")
    return value
