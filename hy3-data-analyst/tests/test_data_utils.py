"""Tests for data_utils: safe_path, read_dataframe."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from hy3_data_analyst.data_utils import read_dataframe, safe_path


class TestSafePath:
    def test_relative_path_stays_in_workspace(self, monkeypatch, tmp_path):
        monkeypatch.setattr("hy3_data_analyst.data_utils.WORKSPACE_ROOT", tmp_path)
        (tmp_path / "subdir").mkdir()
        result = safe_path("subdir")
        assert result == tmp_path / "subdir"

    def test_absolute_path_outside_workspace_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr("hy3_data_analyst.data_utils.WORKSPACE_ROOT", tmp_path)
        outside = tmp_path.parent / "outside_dir"
        outside.mkdir(parents=True, exist_ok=True)
        with pytest.raises(ValueError, match="路径不在工作区内"):
            safe_path(str(outside))


class TestReadDataframe:
    def test_read_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n")
        df = read_dataframe(csv_file)
        assert df.shape == (2, 2)

    def test_read_json(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text('[{"a": 1, "b": 2}, {"a": 3, "b": 4}]')
        df = read_dataframe(json_file)
        assert df.shape == (2, 2)

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="文件不存在"):
            read_dataframe(tmp_path / "nope.csv")

    def test_unsupported_format(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        with pytest.raises(RuntimeError, match="不支持的文件格式"):
            read_dataframe(f)
