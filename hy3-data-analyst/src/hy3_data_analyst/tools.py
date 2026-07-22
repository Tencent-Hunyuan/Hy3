"""MCP tool registration. Defines 4 tools: list, stats, plot, ask."""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .data_utils import get_workspace_root, read_dataframe, safe_path
from .plot import plot_chart as _plot_chart
from .stats import generate_stats

mcp = FastMCP("hy3-data-analyst")


@mcp.tool()
def list_data_files(path: str = ".") -> str:
    """列出工作区内指定目录下的数据文件（.csv, .json, .xlsx, .xls）。
    List data files (.csv, .json, .xlsx, .xls) under the given directory inside the workspace.

    Args:
        path: 相对于工作区根目录的路径，默认为当前目录 / Relative path, defaults to workspace root.
    """
    try:
        target = safe_path(path)
        if not target.is_dir():
            target = target.parent
    except ValueError as e:
        return str(e)

    supported = {".csv", ".json", ".xlsx", ".xls"}
    files: list[str] = []
    try:
        for f in sorted(target.iterdir()):
            if f.is_file() and f.suffix.lower() in supported:
                size_kb = f.stat().st_size / 1024
                files.append(f"  - {f.name} ({size_kb:.1f} KB)")
    except PermissionError:
        return f"无法访问目录 / Cannot access directory: {target}"

    if not files:
        return f"目录 {target} 下未找到支持的数据文件。\nNo supported data files found under {target}.\n支持的格式: .csv, .json, .xlsx, .xls"

    return f"## 数据文件列表 / Data Files in {target}\n\n" + "\n".join(files)


@mcp.tool()
def stats_summary(file_path: str) -> str:
    """生成数据文件的统计摘要（行数、缺失值、数值统计、分类频数）。
    Generate statistical summary for a data file (shape, missing values, numeric stats, top categories).

    Args:
        file_path: 数据文件路径（相对或绝对）/ Path to the data file (relative or absolute).
    """
    try:
        p = safe_path(file_path)
        df = read_dataframe(p)
        return generate_stats(df)
    except Exception as e:
        return f"错误 / Error: {str(e)}"


@mcp.tool()
def plot_chart(
    file_path: str,
    x_column: str = "",
    y_column: str = "",
    chart_type: str = "line",
    title: str = "数据图表",
) -> str:
    """根据数据文件绘制图表并保存为 PNG，返回图片路径和趋势分析。
    Plot a chart from the data file, save as PNG, and return the image path with trend analysis.

    Args:
        file_path: 数据文件路径 / Path to the data file.
        x_column: X 轴列名（留空自动选择）/ X-axis column (auto-select if empty).
        y_column: Y 轴列名（留空自动选择）/ Y-axis column (auto-select if empty).
        chart_type: 图表类型: line, bar, scatter, hist (默认 line).
        title: 图表标题 / Chart title.
    """
    try:
        p = safe_path(file_path)
        df = read_dataframe(p)
        img_path, trend = _plot_chart(
            df,
            x_col=x_column,
            y_col=y_column,
            chart_type=chart_type,
            title=title,
            source_name=p.stem,
        )
        return (
            f"## 图表已生成 / Chart Generated\n\n"
            f"**图片路径 / Image Path**: {img_path}\n\n"
            f"**图表类型 / Chart Type**: {chart_type}\n"
            f"**X 轴 / X-Axis**: {x_column or '(自动选择 / auto)'}\n"
            f"**Y 轴 / Y-Axis**: {y_column or '(自动选择 / auto)'}\n\n"
            f"**趋势分析 / Trend Analysis**: {trend}"
        )
    except Exception as e:
        return f"错误 / Error: {str(e)}"


@mcp.tool()
def ask_data(file_path: str, question: str) -> str:
    """基于数据文件的内容回答自然语言问题（调用 Hy3 API）。
    Answer a natural language question about the data file content (via Hy3 API).

    Args:
        file_path: 数据文件路径 / Path to the data file.
        question: 你想问的问题 / The question you want to ask about the data.
    """
    try:
        p = safe_path(file_path)
        df = read_dataframe(p)

        # Build a prompt with data sample
        sample_rows = min(len(df), 100)
        data_preview = df.head(sample_rows).to_string()
        columns_info = "\n".join(
            f"  - {c} (dtype: {df[c].dtype})" for c in df.columns
        )
        full_prompt = (
            f"数据文件: {p.name}\n"
            f"行数: {len(df)}, 列数: {len(df.columns)}\n"
            f"列信息:\n{columns_info}\n\n"
            f"数据样本 (前 {sample_rows} 行):\n{data_preview}\n\n"
            f"问题: {question}\n\n"
            f"请基于上述数据回答问题，给出具体的分析和见解。如果数据不足以回答问题，请明确指出。\n"
            f"Please answer based on the data above. Provide specific analysis and insights. "
            f"If the data is insufficient, state so clearly."
        )

        # Lazy import to avoid forcing API key at module load time
        from .hy3_client import ask_hy3

        answer = ask_hy3(full_prompt)
        return f"## 智能问答 / AI Q&A\n\n**问题 / Question**: {question}\n\n**回答 / Answer**:\n{answer}"
    except RuntimeError as e:
        return f"错误 / Error: {str(e)}"
    except Exception as e:
        return f"错误 / Error: {str(e)}"
