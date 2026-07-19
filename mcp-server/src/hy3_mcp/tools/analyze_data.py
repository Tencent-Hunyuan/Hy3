# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""analyze_data — deterministic CSV/JSON profiling + Hy3 analysis narrative."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from ..prompts import data_prompts
from ..schemas import ColumnProfile, DataReport, TableProfile
from . import ToolDeps, safe_info

__all__ = ["register", "profile_csv", "profile_json", "suggest_charts"]


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _profile_columns(rows: list[dict[str, object]]) -> list[ColumnProfile]:
    order: list[str] = []
    for row in rows:
        for key in row:
            if key not in order:
                order.append(key)

    profiles: list[ColumnProfile] = []
    for name in order:
        values = [row.get(name) for row in rows]
        present = [v for v in values if not _is_missing(v)]
        missing = len(values) - len(present)

        numbers: list[float] = []
        for v in present:
            if isinstance(v, bool):
                continue
            try:
                numbers.append(float(v))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass

        if not present:
            dtype = "empty"
        elif len(numbers) == len(present):
            dtype = "number"
        elif not numbers:
            dtype = "text"
        else:
            dtype = "mixed"

        col = ColumnProfile(name=name, dtype=dtype, missing=missing)  # type: ignore[arg-type]
        if dtype == "number" and numbers:
            col.min = round(min(numbers), 4)
            col.max = round(max(numbers), 4)
            col.mean = round(sum(numbers) / len(numbers), 4)
        if dtype in ("text", "mixed"):
            counts = Counter(str(v) for v in present)
            top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
            col.top_values = [f"{value} ({count})" for value, count in top]
        profiles.append(col)
    return profiles


def profile_csv(text: str) -> TableProfile:
    """Deterministic profile of CSV text (header row required)."""
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(r) for r in reader]
    if not rows:
        raise ToolError("CSV has no data rows (a header line plus data is required)")
    return TableProfile(format="csv", rows=len(rows), columns=_profile_columns(rows))


def profile_json(text: str) -> TableProfile:
    """Deterministic profile of a JSON array of flat record objects."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ToolError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, list) or not data or not all(
        isinstance(r, dict) for r in data
    ):
        raise ToolError("JSON must be a non-empty array of record objects")
    return TableProfile(format="json", rows=len(data), columns=_profile_columns(data))


def suggest_charts(profile: TableProfile) -> list[str]:
    """Rule-based chart suggestions, independent of the LLM narrative."""
    numeric = [c for c in profile.columns if c.dtype == "number"]
    textual = [c for c in profile.columns if c.dtype == "text"]
    out: list[str] = []
    if textual and numeric:
        out.append(f"Bar chart: mean {numeric[0].name} per {textual[0].name}")
    for col in numeric[:2]:
        out.append(f"Histogram of {col.name} (range {col.min}..{col.max})")
    if len(numeric) >= 2:
        out.append(f"Scatter plot: {numeric[0].name} vs {numeric[1].name}")
    if not out:
        out.append("Table view (no numeric columns detected)")
    return out[:4]


def register(app: FastMCP, deps: ToolDeps) -> None:
    @app.tool(
        name="analyze_data",
        description=(
            "数据分析：读取沙箱内的 CSV 或 JSON 记录数组，先用纯 Python 计算确定性数据画像"
            "（行列数、类型、缺失、min/max/mean、Top 类别），再由 Hy3 撰写分析叙事与图表建议。 "
            "Data analysis: reads a sandboxed CSV or JSON records file, computes a "
            "deterministic profile (rows, dtypes, missing, min/max/mean, top categories) "
            "in pure Python, then asks Hy3 for the narrative and chart ideas."
        ),
    )
    async def analyze_data(
        path: Annotated[
            str,
            Field(
                description=(
                    "CSV（.csv，含表头）或 JSON 记录数组（.json）文件的沙箱内相对路径。 "
                    "Sandbox-relative path of a .csv (with header) or .json (array of "
                    "records) file."
                )
            ),
        ],
        question: Annotated[
            str,
            Field(
                description=(
                    "希望重点分析的问题（可留空做整体概览）。 "
                    "Optional focus question; empty = general overview."
                )
            ),
        ] = "",
        ctx: Context = None,  # type: ignore[assignment]
    ) -> DataReport:
        text = deps.reader.read_text(path)
        lower = path.lower()
        if lower.endswith(".csv"):
            profile = profile_csv(text)
        elif lower.endswith(".json"):
            profile = profile_json(text)
        else:
            raise ToolError("unsupported data file: only .csv and .json are accepted")

        await safe_info(
            ctx,
            f"analyze_data: {profile.format} profile ready "
            f"({profile.rows} rows x {len(profile.columns)} cols), asking Hy3",
        )
        system, user = data_prompts(question, profile)
        reply = await deps.client.chat(
            task="data", system=system, user=user, reasoning_effort="no_think"
        )
        return DataReport(
            markdown=reply.text,
            profile=profile,
            chart_suggestions=suggest_charts(profile),
            mode=deps.settings.mode,
        )
