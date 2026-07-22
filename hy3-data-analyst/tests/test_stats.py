"""Tests for stats module."""

import pandas as pd

from hy3_data_analyst.stats import generate_stats


def test_generate_stats_basic():
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "age": [25, 30, 35],
        "score": [88.5, 92.0, 76.3],
    })
    result = generate_stats(df)
    assert "3 行" in result or "3 rows" in result
    assert "age" in result
    assert "score" in result
    assert "name" in result


def test_generate_stats_with_missing():
    df = pd.DataFrame({
        "x": [1.0, None, 3.0],
        "y": ["a", "b", None],
    })
    result = generate_stats(df)
    assert "缺失" in result or "Missing" in result or "missing" in result


def test_generate_stats_no_numeric():
    df = pd.DataFrame({"label": ["x", "y", "z"]})
    result = generate_stats(df)
    assert "无数值列" in result or "No numeric" in result


def test_generate_stats_no_categorical():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
    result = generate_stats(df)
    assert "无分类列" in result or "No categorical" in result
