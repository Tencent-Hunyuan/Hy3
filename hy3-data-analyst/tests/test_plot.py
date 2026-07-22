"""Tests for plot module."""

import pandas as pd
import pytest

from hy3_data_analyst.plot import _auto_select_columns, plot_chart, SUPPORTED_CHARTS


class TestAutoSelect:
    def test_prefer_given_columns(self):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        x, y = _auto_select_columns(df, "x", "y")
        assert x == "x"
        assert y == "y"

    def test_fallback_first_cols(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        x, y = _auto_select_columns(df)
        assert x == "a"
        assert y == "b"


class TestPlotChart:
    def test_line_chart_saves_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hy3_data_analyst.plot.WORKSPACE_ROOT", tmp_path)
        df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 15]})
        path, trend = plot_chart(df, "x", "y", "line", "Test Chart", source_name="test")
        assert path.exists()
        assert path.suffix == ".png"
        assert "趋势" in trend or "Trend" in trend

    def test_bar_chart_saves_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hy3_data_analyst.plot.WORKSPACE_ROOT", tmp_path)
        df = pd.DataFrame({"cat": ["A", "B", "C"], "val": [10, 20, 15]})
        path, trend = plot_chart(df, "cat", "val", "bar", "Test Bar", source_name="test")
        assert path.exists()

    def test_scatter_chart(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hy3_data_analyst.plot.WORKSPACE_ROOT", tmp_path)
        df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 15]})
        path, trend = plot_chart(df, "x", "y", "scatter", "Test Scatter", source_name="test")
        assert path.exists()
        assert "散点" in trend or "Scatter" in trend

    def test_hist_chart(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hy3_data_analyst.plot.WORKSPACE_ROOT", tmp_path)
        df = pd.DataFrame({"val": [1, 2, 2, 3, 3, 3, 4, 5]})
        path, trend = plot_chart(df, "", "val", "hist", "Test Hist", source_name="test")
        assert path.exists()

    def test_invalid_chart_type(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hy3_data_analyst.plot.WORKSPACE_ROOT", tmp_path)
        df = pd.DataFrame({"x": [1]})
        with pytest.raises(ValueError, match="不支持的图表类型"):
            plot_chart(df, "x", "x", "pie", "Bad", source_name="test")
