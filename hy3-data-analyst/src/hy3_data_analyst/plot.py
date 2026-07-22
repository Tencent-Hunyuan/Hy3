"""Chart plotting with matplotlib + seaborn."""

import os
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for headless environments
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .config import WORKSPACE_ROOT

# Set seaborn style
sns.set_style("whitegrid")
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

SUPPORTED_CHARTS = {"line", "bar", "scatter", "hist"}


def _auto_select_columns(df: pd.DataFrame, prefer_x: str = "", prefer_y: str = "") -> tuple[str, str]:
    """Pick x and y columns. If not specified, prefer date-like columns or first columns."""
    cols = df.columns.tolist()
    if not cols:
        raise ValueError("DataFrame 没有列 / DataFrame has no columns.")

    # Try to find a date-like column for x
    date_candidates = [c for c in cols if "date" in c.lower() or "time" in c.lower() or "日期" in c]

    x = prefer_x if prefer_x and prefer_x in cols else ""
    y = prefer_y if prefer_y and prefer_y in cols else ""

    if not x:
        if date_candidates:
            x = date_candidates[0]
        else:
            x = cols[0]

    if not y:
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            for c in numeric_cols:
                if c != x:
                    y = c
                    break
            if not y:
                y = numeric_cols[0]
        else:
            y = cols[1] if len(cols) > 1 else cols[0]

    return x, y


def _analyze_trend(df: pd.DataFrame, x_col: str, y_col: str, chart_type: str) -> str:
    """Generate a brief trend analysis text based on chart type."""
    if chart_type in ("line", "bar"):
        if pd.api.types.is_numeric_dtype(df[y_col]):
            vals = df[y_col].dropna()
            if len(vals) >= 2:
                first = vals.iloc[0]
                last = vals.iloc[-1]
                if last > first * 1.05:
                    return f"趋势: 上升 (首值={first:.2f}, 末值={last:.2f}) / Trend: Upward ({first:.2f} → {last:.2f})"
                elif last < first * 0.95:
                    return f"趋势: 下降 (首值={first:.2f}, 末值={last:.2f}) / Trend: Downward ({first:.2f} → {last:.2f})"
                else:
                    return f"趋势: 平稳 (首值={first:.2f}, 末值={last:.2f}) / Trend: Stable ({first:.2f} → {last:.2f})"
        return "趋势: 无法判断（非数值列）/ Trend: Cannot determine (non-numeric column)."
    elif chart_type == "hist":
        if pd.api.types.is_numeric_dtype(df[y_col]):
            skew = df[y_col].skew()
            if skew > 0.5:
                return f"直方图显示右偏分布 (偏度={skew:.2f}) / Histogram shows right-skewed distribution (skew={skew:.2f})."
            elif skew < -0.5:
                return f"直方图显示左偏分布 (偏度={skew:.2f}) / Histogram shows left-skewed distribution (skew={skew:.2f})."
            else:
                return f"直方图显示近似对称分布 (偏度={skew:.2f}) / Histogram shows approximately symmetric distribution (skew={skew:.2f})."
        return "直方图分析: 非数值列 / Histogram: non-numeric column."
    else:
        return "散点图: 无明确趋势，请观察分布 / Scatter plot: no clear trend, observe distribution."


def plot_chart(
    df: pd.DataFrame,
    x_col: str = "",
    y_col: str = "",
    chart_type: str = "line",
    title: str = "数据图表",
    source_name: str = "data",
) -> tuple[Path, str]:
    """Draw a chart and save as PNG.

    Returns (absolute_path_to_png, trend_analysis_text).
    """
    chart_type = chart_type.lower()
    if chart_type not in SUPPORTED_CHARTS:
        raise ValueError(
            f"不支持的图表类型: {chart_type}。支持: {', '.join(sorted(SUPPORTED_CHARTS))}\n"
            f"Unsupported chart type: {chart_type}. Supported: {', '.join(sorted(SUPPORTED_CHARTS))}"
        )

    x_col, y_col = _auto_select_columns(df, x_col, y_col)

    fig, ax = plt.subplots(figsize=(10, 6))

    if chart_type == "line":
        ax.plot(df[x_col], df[y_col], marker="o", linewidth=2)
    elif chart_type == "bar":
        ax.bar(df[x_col].astype(str), df[y_col])
        plt.xticks(rotation=45, ha="right")
    elif chart_type == "scatter":
        ax.scatter(df[x_col], df[y_col], alpha=0.7)
    elif chart_type == "hist":
        ax.hist(df[y_col].dropna(), bins=20, edgecolor="white")

    ax.set_title(title, fontsize=14)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    plt.tight_layout()

    # Save to charts/ directory
    charts_dir = WORKSPACE_ROOT / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = source_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    fname = f"{safe_name}_{timestamp}.png"
    save_path = charts_dir / fname
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    trend = _analyze_trend(df, x_col, y_col, chart_type)

    return save_path.resolve(), trend
