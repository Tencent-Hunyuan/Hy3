"""Hy3 数据分析 MCP Server（stdio 模式）。

提供 4 个工具：load_dataset / analyze_data / describe_chart / query_data。

启动方式：
    PYTHONPATH=src python -m hy3_mcp_server.server
"""

from __future__ import annotations

import json
import re

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .data_loader import load_dataframe, run_query, summarize
from .llm_client import LLMClient

load_dotenv()

mcp = FastMCP("hy3-data-analysis")


# ──── 内部工具函数 ────


def _coerce_records(data_records):
    """将输入转为 list[dict] 格式。"""
    if not data_records:
        return None
    if isinstance(data_records, str):
        try:
            data_records = json.loads(data_records)
        except (ValueError, TypeError):
            return None
    if isinstance(data_records, dict):
        if isinstance(data_records.get("records"), list):
            data_records = data_records["records"]
        else:
            data_records = [data_records]
    if isinstance(data_records, list) and all(isinstance(r, dict) for r in data_records):
        return data_records
    return None


def _extract_spec(model_text: str) -> dict | None:
    """从模型输出提取 JSON spec。"""
    fence = re.search(r"```json\s*(\{.*?\})\s*```", model_text, re.DOTALL)
    if not fence:
        try:
            obj = json.loads(model_text.strip())
            return obj if isinstance(obj, dict) else None
        except (ValueError, TypeError):
            return None
    try:
        obj = json.loads(fence.group(1))
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        return None


def _normalize_chart_spec(model_text: str, records: list | None) -> str:
    """归一化为 Vega-Lite spec 代码块。"""
    spec = _extract_spec(model_text)
    if spec is None:
        return model_text
    if records:
        data_block = spec.get("data")
        if not isinstance(data_block, dict):
            data_block = {}
        data_block["values"] = records
        spec["data"] = data_block
    new_json = json.dumps(spec, ensure_ascii=False, indent=2)
    return f"```json\n{new_json}\n```"


def _is_vague_question(question: str) -> bool:
    """判断是否为模糊问题，需自动生成综合分析。"""
    if not question or not question.strip():
        return True
    vague_patterns = [
        r"^分析一?下?$",
        r"^帮我[看分]析?",
        r"^看看[这个数据]*",
        r"^分析[这个数据]*$",
        r"^[有什么]*(发现|洞察|结论|趋势|规律|特征|特点)",
        r"^概况",
        r"^overview",
        r"^analyze",
        r"^look at",
        r"^what.*(find|see|insight|trend)",
    ]
    q = question.strip().lower()
    return any(re.search(p, q, re.IGNORECASE) for p in vague_patterns)


# ──── MCP 工具 ────


@mcp.tool()
def load_dataset(file_path: str, format: str = "auto") -> str:
    """读取本地 CSV/JSON 文件，返回数据结构摘要（列信息、统计、分布、相关性）。

    参数:
        file_path: 文件路径
        format: csv / json / auto（默认按扩展名推断）
    """
    df = load_dataframe(file_path, format)
    return json.dumps(summarize(df), ensure_ascii=False, indent=2)


@mcp.tool()
def analyze_data(file_path: str, question: str = "", evidence: str = "") -> str:
    """调用 Hy3 分析数据。question 为空或模糊时自动生成综合报告。

    参数:
        file_path: 文件路径
        question: 分析问题（留空自动生成综合报告）
        evidence: 可选，query_data 的聚合结果 JSON（为精确分析提供依据）
    """
    df = load_dataframe(file_path)
    data_summary = summarize(df)

    if _is_vague_question(question):
        system_prompt = (
            "你是一名资深数据分析师。请基于以下数据摘要，生成一份结构化的综合分析报告。\n"
            "报告需涵盖：\n"
            "1. 数据概况（规模、维度、完整性）\n"
            "2. 关键发现（分布特征、分类变量集中度、数值变量统计特征）\n"
            "3. 相关性与趋势（变量间关联、潜在因果方向）\n"
            "4. 异常与关注点（极端值、分布偏斜、潜在数据质量问题）\n"
            "5. 业务洞察与建议（基于数据特征可推导的决策建议）\n\n"
            "使用中文回答，用 Markdown 格式组织，结论有数据支撑。"
        )
        user_content = f"数据摘要（JSON）:\n{json.dumps(data_summary, ensure_ascii=False)}"
    else:
        system_prompt = (
            "你是一名严谨的数据分析助手。只依据给定的数据摘要与统计证据作答，"
            "缺乏依据时明确说明，不臆造数据或结论。"
            "若问题需要全量聚合但未提供统计证据，应提示先用 query_data 聚合。"
        )
        user_content = (
            f"数据摘要（JSON）:\n{json.dumps(data_summary, ensure_ascii=False)}\n\n"
            + (f"统计证据（来自 query_data）:\n{evidence}\n\n" if evidence else "")
            + f"分析问题:\n{question}"
        )

    client = LLMClient()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    return client.chat(messages)


@mcp.tool()
def describe_chart(
    file_path: str,
    columns: list[str],
    chart_intent: str = "",
    data_records: str = "",
) -> str:
    """根据指定列推荐图表类型，输出 Vega-Lite v5 JSON spec。

    参数:
        file_path: 文件路径
        columns: 要可视化的列名列表
        chart_intent: 可选，图表意图（如"各专业薪资对比"）
        data_records: 可选，query_data 的聚合结果 JSON（覆盖图表数据源）
    """
    df = load_dataframe(file_path)
    data_summary = summarize(df)
    records = _coerce_records(data_records)

    intent_line = f"\n用户意图: {chart_intent}" if chart_intent else ""
    client = LLMClient()
    messages = [
        {
            "role": "system",
            "content": (
                "你是数据可视化专家。根据数据摘要与指定列，推荐最合适的图表类型，"
                "并输出一个完整的 Vega-Lite v5 spec JSON（用 ```json 代码块包裹）。\n"
                "要求：\n"
                "- spec 必须包含 $schema、title、description、mark、encoding 字段\n"
                "- data.values 填入摘要中的预览数据即可\n"
                "- 图表标题用中文\n"
                "- 只输出一个 ```json 代码块，不要额外文字"
            ),
        },
        {
            "role": "user",
            "content": (
                f"数据摘要:\n{json.dumps(data_summary, ensure_ascii=False)}\n\n"
                f"要可视化的列: {columns}{intent_line}"
            ),
        },
    ]
    model_output = client.chat(messages)
    return _normalize_chart_spec(model_output, records)


@mcp.tool()
def query_data(
    file_path: str,
    operation: str = "head",
    columns: list[str] | None = None,
    group_by: str | None = None,
    agg: str = "mean",
    filter_expr: str | None = None,
    sort_by: str | None = None,
    ascending: bool = True,
    limit: int = 50,
) -> str:
    """本地精确查询/聚合（不调用 LLM），结果可传给 analyze_data 或 describe_chart。

    参数:
        file_path: 文件路径
        operation: head / describe / aggregate（默认 head）
        columns: 操作的列名列表
        group_by: 分组列名
        agg: 聚合函数 mean / sum / count / min / max
        filter_expr: 过滤表达式（如 "学历 == '硕士'"）
        sort_by: 排序列
        ascending: 排序方向（默认升序）
        limit: 返回行数上限（默认 50）
    """
    df = load_dataframe(file_path)
    result = run_query(
        df,
        operation=operation,
        columns=columns,
        group_by=group_by,
        agg=agg,
        filter_expr=filter_expr,
        sort_by=sort_by,
        ascending=ascending,
        limit=limit,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
