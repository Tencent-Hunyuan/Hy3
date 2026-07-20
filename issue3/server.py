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


def main() -> None:
    """以 stdio 模式启动 MCP Server。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
