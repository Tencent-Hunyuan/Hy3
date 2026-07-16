"""数据加载与摘要模块。

读取 CSV/JSON 文件，生成结构化摘要供 LLM 分析使用。

用法：
    from hy3_mcp_server.data_loader import load_dataframe, summarize, run_query
    df = load_dataframe("data.csv")
    summary = summarize(df)           # 获取数据摘要
    result = run_query(df, group_by="专业", columns=["薪资"], agg="mean")  # 精确聚合
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def load_dataframe(file_path: str, format: str = "auto") -> pd.DataFrame:
    """读取 CSV/JSON 文件为 DataFrame。"""
    p = Path(file_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")

    if format == "auto":
        ext = p.suffix.lower()
        if ext == ".csv":
            format = "csv"
        elif ext in (".json", ".jsonl"):
            format = "json"
        else:
            raise ValueError(f"无法推断格式（扩展名: {ext}），请指定 format 参数")

    if format == "csv":
        return pd.read_csv(p)
    elif format == "json":
        return pd.read_json(p, lines=p.suffix.lower() == ".jsonl")
    else:
        raise ValueError(f"不支持的格式: {format}，仅支持 csv / json")


def summarize(df: pd.DataFrame) -> dict:
    """生成数据摘要：基本信息、数值统计、分类分布、相关性、预览行。"""
    rows, cols = df.shape
    result: dict = {
        "shape": {"rows": rows, "columns": cols},
        "column_names": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": df.isnull().sum().to_dict(),
    }

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        desc = df[numeric_cols].describe(percentiles=[0.25, 0.5, 0.75]).to_dict()
        result["numeric_stats"] = desc

    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if cat_cols:
        cat_dist = {}
        for col in cat_cols:
            vc = df[col].value_counts()
            cat_dist[col] = {
                "unique_count": int(vc.shape[0]),
                "top_10": vc.head(10).to_dict(),
            }
        result["categorical_distribution"] = cat_dist

    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr()
        pairs = []
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                pairs.append({
                    "col_a": numeric_cols[i],
                    "col_b": numeric_cols[j],
                    "correlation": round(corr.iloc[i, j], 4),
                })
        pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        result["top_correlations"] = pairs[:10]

    result["preview_rows"] = json.loads(df.head(5).to_json(orient="records", force_ascii=False))
    return result


def run_query(
    df: pd.DataFrame,
    operation: str = "head",
    columns: list[str] | None = None,
    group_by: str | list[str] | None = None,
    agg: str = "mean",
    filter_expr: str | None = None,
    sort_by: str | None = None,
    ascending: bool = True,
    limit: int = 50,
) -> dict:
    """本地精确查询/聚合，返回 {"records": [...], "total_rows": N}。"""
    result_df = df.copy()

    if filter_expr:
        result_df = result_df.query(filter_expr)

    if columns:
        valid = [c for c in columns if c in result_df.columns]
        if valid:
            if group_by:
                gb_cols = [group_by] if isinstance(group_by, str) else group_by
                result_df = result_df.groupby(gb_cols)[valid].agg(agg).reset_index()
            else:
                result_df = result_df[valid]
        else:
            return {"error": f"指定的列不存在: {columns}"}
    elif group_by:
        gb_cols = [group_by] if isinstance(group_by, str) else group_by
        numeric = result_df.select_dtypes(include="number").columns.tolist()
        if numeric:
            result_df = result_df.groupby(gb_cols)[numeric].agg(agg).reset_index()
        else:
            result_df = result_df.groupby(gb_cols).size().reset_index(name="count")

    if operation == "describe":
        return {"statistics": json.loads(result_df.describe().to_json())}

    if sort_by and sort_by in result_df.columns:
        result_df = result_df.sort_values(sort_by, ascending=ascending)

    result_df = result_df.head(limit)
    records = json.loads(result_df.to_json(orient="records", force_ascii=False))
    return {"records": records, "total_rows": len(records)}
