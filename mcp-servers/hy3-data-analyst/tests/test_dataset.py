from __future__ import annotations

import json
from pathlib import Path

import pytest

from hy3_data_analyst.config import Settings
from hy3_data_analyst.dataset import DatasetError, profile_dataset_file


def settings(data_dir: Path, *, max_file_bytes: int = 1_000_000) -> Settings:
    return Settings(
        api_base="http://127.0.0.1:8000/v1",
        api_key="EMPTY",
        model="hy3",
        data_dir=data_dir.resolve(),
        max_file_bytes=max_file_bytes,
        timeout_seconds=10,
    )


def test_profiles_csv_types_missing_values_and_numeric_stats(tmp_path: Path) -> None:
    dataset = tmp_path / "sales.csv"
    dataset.write_text(
        "date,units,revenue,active\n"
        "2026-07-01,2,3.5,true\n"
        "2026-07-02,,6.5,false\n",
        encoding="utf-8",
    )

    profile = profile_dataset_file("sales.csv", settings=settings(tmp_path))

    assert profile["rows_scanned"] == 2
    assert profile["truncated"] is False
    columns = {column["name"]: column for column in profile["columns"]}
    assert columns["date"]["type"] == "datetime"
    assert columns["units"]["type"] == "integer"
    assert columns["units"]["missing_count"] == 1
    assert columns["revenue"]["numeric"] == {"min": 3.5, "max": 6.5, "mean": 5.0}
    assert columns["active"]["type"] == "boolean"


def test_reads_json_wrapped_record_list_and_truncates(tmp_path: Path) -> None:
    (tmp_path / "records.json").write_text(
        json.dumps({"records": [{"id": 1}, {"id": 2}, {"id": 3}]}),
        encoding="utf-8",
    )

    profile = profile_dataset_file(
        "records.json",
        max_rows=2,
        sample_rows=1,
        settings=settings(tmp_path),
    )

    assert profile["rows_scanned"] == 2
    assert profile["truncated"] is True
    assert profile["sample_rows"] == [{"id": 1}]


def test_reads_jsonl_and_ignores_blank_lines(tmp_path: Path) -> None:
    (tmp_path / "events.jsonl").write_text('{"id": 1}\n\n{"id": 2}\n', encoding="utf-8")

    profile = profile_dataset_file("events.jsonl", settings=settings(tmp_path))

    assert profile["rows_scanned"] == 2


def test_rejects_path_outside_data_directory(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    outside = tmp_path / "secret.csv"
    outside.write_text("token\nnot-a-real-secret\n", encoding="utf-8")

    with pytest.raises(DatasetError, match="must stay inside"):
        profile_dataset_file(str(outside), settings=settings(data_dir))


def test_rejects_oversized_file(tmp_path: Path) -> None:
    (tmp_path / "large.csv").write_text("column\n123456789\n", encoding="utf-8")

    with pytest.raises(DatasetError, match="exceeding"):
        profile_dataset_file("large.csv", settings=settings(tmp_path, max_file_bytes=4))


@pytest.mark.parametrize("value", [0, -1, 100_001, True])
def test_rejects_invalid_max_rows(tmp_path: Path, value: int) -> None:
    (tmp_path / "one.csv").write_text("id\n1\n", encoding="utf-8")

    with pytest.raises(DatasetError, match="max_rows"):
        profile_dataset_file("one.csv", max_rows=value, settings=settings(tmp_path))
