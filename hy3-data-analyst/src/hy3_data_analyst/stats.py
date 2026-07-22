"""Statistical summary generation (pure pandas, no API calls)."""

import pandas as pd


def generate_stats(df: pd.DataFrame) -> str:
    """Generate a Markdown-formatted statistical summary of the DataFrame.

    Includes shape, missing values, numeric column statistics, and top categories.
    """
    lines: list[str] = []
    lines.append("## 数据统计摘要 / Data Statistical Summary")
    lines.append("")

    # Shape
    rows, cols = df.shape
    lines.append(f"- **数据形状 / Shape**: {rows} 行 × {cols} 列")
    lines.append("")

    # Missing values
    missing = df.isnull().sum()
    missing_pct = (missing / rows * 100) if rows > 0 else missing * 0
    missing_info = pd.DataFrame({
        "列名 / Column": missing.index,
        "缺失数 / Missing": missing.values,
        "缺失率 / Rate(%)": [f"{v:.2f}%" for v in missing_pct.values],
    })
    has_missing = (missing > 0).any()
    if has_missing:
        lines.append("### 缺失值统计 / Missing Values")
        lines.append("")
        mask = (missing > 0).values
        lines.append(missing_info[mask].to_markdown(index=False))
    else:
        lines.append("### 缺失值统计 / Missing Values")
        lines.append("")
        lines.append("无缺失值 / No missing values.")
    lines.append("")

    # Numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        lines.append("### 数值列统计 / Numeric Column Statistics")
        lines.append("")
        stats_df = df[numeric_cols].describe(percentiles=[0.25, 0.5, 0.75])
        stats_df.index = ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
        lines.append(stats_df.to_markdown(floatfmt=".2f"))
    else:
        lines.append("### 数值列统计 / Numeric Column Statistics")
        lines.append("")
        lines.append("无数值列 / No numeric columns.")
    lines.append("")

    # Top categories for categorical columns (first 3)
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    cat_cols = cat_cols[:3]
    if cat_cols:
        lines.append("### 分类列频数统计 / Categorical Value Counts (Top 5)")
        lines.append("")
        for col in cat_cols:
            counts = df[col].value_counts().head(5)
            lines.append(f"**{col}**:")
            for val, cnt in counts.items():
                lines.append(f"  - {val}: {cnt}")
            lines.append("")
    else:
        lines.append("### 分类列频数统计 / Categorical Value Counts")
        lines.append("")
        lines.append("无分类列 / No categorical columns.")
        lines.append("")

    return "\n".join(lines)
