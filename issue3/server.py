"""Hy3 MCP Server — 数据分析助手：读取 CSV/JSON + 网络搜索 + Hy3 推理。"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def _load_dotenv() -> None:
    """从 server.py 同目录的 .env 加载环境变量（不覆盖已有值）。"""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    try:
        text = env_path.read_text(encoding="utf-8-sig")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, val = line.partition("=")
        name = name.strip().lstrip("﻿")
        val = val.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = val


_load_dotenv()

import pandas as pd
from mcp.server.fastmcp import FastMCP
from openai import OpenAI

mcp = FastMCP(
    "hy3-data-analysis",
    instructions=(
        "数据分析助手：读取 CSV/JSON 数据集，进行统计分析和可视化建议。"
        "使用流程：load_dataset 预览数据 → hy3_analyze 深入分析 → hy3_chart_guide 获取图表方案。"
        "可选使用 web_search 获取外部信息辅助分析。"
    ),
)


def _workspace_root() -> Path:
    raw = os.environ.get("HY3_MCP_ROOT", os.getcwd())
    return Path(raw).expanduser().resolve()


def _safe_path(rel_or_abs: str) -> Path:
    """只允许访问 HY3_MCP_ROOT 目录内的文件，拒绝越界和隐藏文件。"""
    root = _workspace_root()
    p = Path(rel_or_abs).expanduser()
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    try:
        p.relative_to(root)
    except ValueError as e:
        raise ValueError(f"路径超出工作区 {root}: {p}") from e

    # 拒绝隐藏文件
    if p.name.startswith(".") and p.name not in (".", ".."):
        raise ValueError(f"不允许访问隐藏文件: {p.name}")

    return p


def _check_extension(path: Path) -> str:
    """检查文件扩展名是否支持，返回小写扩展名。"""
    ext = path.suffix.lower()
    if ext not in (".csv", ".json", ".jsonl"):
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .csv / .json / .jsonl")
    return ext


@mcp.tool()
def load_dataset(path: str, max_rows: int = 50) -> str:
    """读取 CSV 或 JSON 数据集文件，返回结构摘要、统计信息和数据预览。

    Args:
        path: 数据集文件路径，相对于工作区根目录（HY3_MCP_ROOT）。支持 .csv / .json / .jsonl。
        max_rows: 预览时最多返回的行数，默认 50。
    """
    if max_rows < 1:
        max_rows = 50

    try:
        file_path = _safe_path(path)
    except ValueError as e:
        return f"[错误] {e}"

    try:
        ext = _check_extension(file_path)
    except ValueError as e:
        return f"[错误] {e}"

    if not file_path.is_file():
        return f"[错误] 文件不存在: {file_path}"

    file_size = file_path.stat().st_size

    try:
        if ext == ".csv":
            df = pd.read_csv(file_path, encoding="utf-8")
        elif ext == ".jsonl":
            records = []
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            df = pd.DataFrame(records)
        else:  # .json
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # 尝试展开单层嵌套
                df = pd.json_normalize(data, max_level=1)
            else:
                return f"[错误] JSON 数据结构不支持，需为数组或对象，实际: {type(data).__name__}"
    except Exception as e:
        return f"[错误] 文件解析失败: {e}"

    total_rows = len(df)
    columns = df.columns.tolist()
    dtypes = {col: str(df[col].dtype) for col in columns}

    # null 统计
    null_counts = {col: int(df[col].isna().sum()) for col in columns}

    # 数值列统计
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    stats = {}
    if numeric_cols:
        desc = df[numeric_cols].describe()
        for col in numeric_cols:
            stats[col] = {
                "min": round(float(desc.loc["min", col]), 2) if not pd.isna(desc.loc["min", col]) else None,
                "max": round(float(desc.loc["max", col]), 2) if not pd.isna(desc.loc["max", col]) else None,
                "mean": round(float(desc.loc["mean", col]), 2) if not pd.isna(desc.loc["mean", col]) else None,
                "std": round(float(desc.loc["std", col]), 2) if not pd.isna(desc.loc["std", col]) else None,
            }

    # 构建输出
    lines = [
        f"工作区: {_workspace_root()}",
        f"文件: {file_path}",
        f"大小: {file_size:,} 字节",
        f"格式: {ext}",
        f"总行数: {total_rows}",
        f"列数: {len(columns)}",
        "",
        "--- 字段信息 ---",
    ]
    for col in columns:
        null_info = f", 空值: {null_counts[col]}" if null_counts.get(col) else ""
        lines.append(f"  {col}: {dtypes.get(col, 'unknown')}{null_info}")

    if stats:
        lines.append("")
        lines.append("--- 数值列统计 ---")
        for col, s in stats.items():
            lines.append(f"  {col}: min={s['min']}, max={s['max']}, mean={s['mean']}, std={s['std']}")

    # 预览数据
    preview_rows = min(max_rows, total_rows)
    lines.append("")
    lines.append(f"--- 数据预览 (前 {preview_rows} 行) ---")
    preview_df = df.head(preview_rows).copy()
    # 截断长文本单元格
    for col in preview_df.columns:
        preview_df[col] = preview_df[col].astype(str).apply(lambda x: x[:80] + "..." if len(x) > 80 else x)
    lines.append(preview_df.to_string(index=True, max_colwidth=40))

    if total_rows > preview_rows:
        lines.append(f"\n... (共 {total_rows} 行，仅显示前 {preview_rows} 行)")

    return "\n".join(lines)


def _hy3_client() -> tuple[OpenAI, str]:
    api_key = os.environ.get("HY3_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未设置环境变量 HY3_API_KEY，请在 .env 文件或环境变量中配置")
    base_url = os.environ.get("HY3_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    model = os.environ.get("HY3_MODEL", "tencent/hy3:free")
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
    return client, model


def _call_hy3_with_retry(
    messages: list[dict],
    max_tokens: int = 4096,
    reasoning_effort: str = "high",
    max_retries: int = 2,
) -> str:
    """调用 Hy3 API，支持 60s 超时和最多 2 次重试。"""
    client, model = _hy3_client()
    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens,
                extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning_effort}},
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))  # 指数退避
    return f"[Hy3 API 调用失败，已重试 {max_retries} 次] {last_error}"


def _search_tavily(query: str, max_results: int) -> list[dict] | None:
    """Tavily 搜索，失败返回 None。"""
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results, search_depth="basic")
        results = response.get("results", [])
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": (r.get("content", "") or "")[:300]}
            for r in results[:max_results]
        ]
    except Exception:
        return None


def _search_ddg(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo 搜索，失败返回空列表。"""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": (r.get("body", "") or "")[:300],
                })
        return results
    except Exception:
        return []


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """搜索网络信息，用于辅助数据分析。优先使用 Tavily API，未配置时自动回退 DuckDuckGo。

    Args:
        query: 搜索查询字符串。
        max_results: 最多返回的结果数，默认 5。
    """
    if not query.strip():
        return "[错误] query 不能为空"

    if max_results < 1:
        max_results = 5
    if max_results > 10:
        max_results = 10

    source = "DuckDuckGo"
    results = _search_tavily(query, max_results)

    if results is not None:
        if len(results) > 0:
            source = "Tavily"
        else:
            # Tavily 返回空结果，回退到 DuckDuckGo
            results = _search_ddg(query, max_results)
    else:
        results = _search_ddg(query, max_results)

    if not results:
        return "[错误] 搜索失败：Tavily API Key 未配置且 DuckDuckGo 搜索不可用。请设置 TAVILY_API_KEY 环境变量或检查网络连接。"

    lines = [f"搜索源: {source}", f"查询: {query}", f"结果数: {len(results)}", ""]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   URL: {r['url']}")
        lines.append(f"   摘要: {r['snippet']}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def hy3_analyze(dataset_path: str, question: str, include_web: bool = False) -> str:
    """加载数据集并用 Hy3 进行深度数据分析，输出结构化分析报告。

    自动先调用 load_dataset 获取数据摘要，然后组装包含数据上下文和用户问题的
    prompt 发送给 Hy3 API。可选结合网络搜索结果增强分析。

    Args:
        dataset_path: 数据集文件路径，相对于工作区根目录。
        question: 要分析的具体问题，越具体越好。
        include_web: 是否结合网络搜索获取外部信息辅助分析，默认 False。
    """
    if not question.strip():
        return "[错误] question 不能为空"

    env_key = os.environ.get("HY3_API_KEY", "").strip()
    if not env_key:
        return "[错误] 未设置 HY3_API_KEY 环境变量。请在 .env 文件或环境变量中配置 API Key。"

    # Step 1: 加载数据
    data_summary = load_dataset(dataset_path, max_rows=30)
    if data_summary.startswith("[错误]"):
        return data_summary

    # Step 2: 可选网络搜索
    web_context = ""
    if include_web:
        web_result = web_search(question, max_results=3)
        if not web_result.startswith("[错误]"):
            web_context = f"\n\n网络搜索补充信息:\n{web_result}"

    # Step 3: 组装 prompt 调用 Hy3
    system_prompt = (
        "你是一个资深数据分析师。请基于提供的数据集摘要和用户问题，用中文给出结构化分析报告。"
        "报告格式：1) 关键发现 2) 趋势分析 3) 异常点（如有）4) 统计结论 5) 建议。"
        "用分点方式回答，引用具体数据支撑观点。"
    )
    user_prompt = (
        f"数据集摘要:\n{data_summary}\n{web_context}\n\n用户问题: {question}\n\n请给出分析报告。"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    result = _call_hy3_with_retry(messages, max_tokens=4096, reasoning_effort="high")
    return result


@mcp.tool()
def hy3_chart_guide(dataset_path: str, goal: str) -> str:
    """基于数据集特征和可视化目标，用 Hy3 推荐最佳图表方案并生成可执行的 Python 绘图代码。

    自动先调用 load_dataset 获取数据结构和统计摘要，然后让 Hy3 根据数据特征
    （字段类型、分布）推荐图表类型、轴映射方案和预处理步骤。

    Args:
        dataset_path: 数据集文件路径，相对于工作区根目录。
        goal: 可视化目标描述，如「对比各区域销售额」「展示时间趋势」「分析年龄分布」。
    """
    if not goal.strip():
        return "[错误] goal 不能为空"

    env_key = os.environ.get("HY3_API_KEY", "").strip()
    if not env_key:
        return "[错误] 未设置 HY3_API_KEY 环境变量。请在 .env 文件或环境变量中配置 API Key。"

    # Step 1: 加载数据特征
    data_summary = load_dataset(dataset_path, max_rows=20)
    if data_summary.startswith("[错误]"):
        return data_summary

    # Step 2: 组装 prompt 调用 Hy3
    system_prompt = (
        "你是一个数据可视化专家。请基于数据集摘要和可视化目标，用中文给出图表方案。"
        "输出格式：\n"
        "1. 推荐图表类型及理由（1-2 句话）\n"
        "2. 轴映射方案 (x, y, color, facet 等)\n"
        "3. 数据预处理建议（如需聚合、筛选、归一化）\n"
        "4. Python 绘图代码 (优先 matplotlib，如适合交互则用 plotly)\n"
        "代码需包含数据加载、预处理和绘图完整流程，路径使用占位符 'DATASET_PATH'。"
    )
    user_prompt = (
        f"数据集摘要:\n{data_summary}\n\n可视化目标: {goal}\n\n请给出图表方案。"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    result = _call_hy3_with_retry(messages, max_tokens=4096, reasoning_effort="low")
    return result


def main() -> None:
    """以 stdio 模式启动 MCP Server。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
