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
"""Tool internals: diff parsing, heuristics, profiling, prompts, in-process calls."""

from __future__ import annotations

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from hy3_mcp.prompts import (
    data_prompts,
    docs_prompts,
    research_prompts,
    review_prompts,
)
from hy3_mcp.schemas import Evidence
from hy3_mcp.sources.files import Chunk, ScoredChunk
from hy3_mcp.tools.analyze_data import profile_csv, profile_json, suggest_charts
from hy3_mcp.tools.review_code import parse_unified_diff, scan_heuristics

DEMO_DIFF = "examples/diffs/demo.diff"


# ---------------------------------------------------------------- diff parsing


def test_parse_unified_diff_exact_stats(examples_dir):
    text = (examples_dir / "diffs/demo.diff").read_text(encoding="utf-8")
    stats, added = parse_unified_diff(text)
    assert stats.files == ["app/config.py", "app/utils.py"]
    assert stats.hunks == 2
    assert stats.added_lines == 9
    assert stats.removed_lines == 2
    assert len(added) == 9


def test_parse_unified_diff_hunk_body_dashdash_plusplus():
    """Removed '--x' / added '++y' body lines must not be taken for file headers."""
    diff = (
        "--- a/cli.py\n"
        "+++ b/cli.py\n"
        "@@ -1,2 +1,2 @@\n"
        " import sys\n"
        "---x\n"  # removed line whose content is '--x'
        "+++y\n"  # added line whose content is '++y'
    )
    stats, added = parse_unified_diff(diff)
    assert stats.files == ["cli.py"]
    assert stats.hunks == 1
    assert stats.added_lines == 1
    assert stats.removed_lines == 1
    assert added == [("cli.py", 2, "++y")]


def test_parse_unified_diff_headers_after_tricky_hunk():
    """Real file headers are still recognized once a hunk body is consumed."""
    diff = (
        "--- a/one.py\n"
        "+++ b/one.py\n"
        "@@ -1 +1 @@\n"
        "--old\n"
        "++new\n"
        "--- a/two.py\n"
        "+++ b/two.py\n"
        "@@ -1 +1,2 @@\n"
        " ctx\n"
        "+added\n"
        "\\ No newline at end of file\n"
    )
    stats, added = parse_unified_diff(diff)
    assert stats.files == ["one.py", "two.py"]
    assert stats.hunks == 2
    assert stats.added_lines == 2
    assert stats.removed_lines == 1
    assert added == [("one.py", 1, "+new"), ("two.py", 2, "added")]


def test_scan_heuristics_exact_flags(examples_dir):
    text = (examples_dir / "diffs/demo.diff").read_text(encoding="utf-8")
    _, added = parse_unified_diff(text)
    flags = scan_heuristics(added)
    triples = [(f.category, f.file, f.line) for f in flags]
    assert triples == [
        ("security", "app/config.py", 13),
        ("correctness", "app/config.py", 14),
        ("maintainability", "app/config.py", 15),
        ("style", "app/config.py", 16),
        ("correctness", "app/utils.py", 3),
    ]
    assert flags[0].severity == "high"


# ------------------------------------------------------------------- profiling


def test_profile_csv_exact_numbers(examples_dir):
    profile = profile_csv(
        (examples_dir / "data/sales_sample.csv").read_text(encoding="utf-8")
    )
    assert profile.format == "csv"
    assert profile.rows == 30
    cols = {c.name: c for c in profile.columns}
    assert list(cols) == ["date", "region", "product", "units", "revenue"]

    assert cols["units"].dtype == "number"
    assert cols["units"].missing == 2
    assert (cols["units"].min, cols["units"].max, cols["units"].mean) == (5.0, 14.0, 9.25)

    assert cols["revenue"].dtype == "number"
    assert cols["revenue"].missing == 1
    assert (cols["revenue"].min, cols["revenue"].max) == (100.0, 317.5)
    assert cols["revenue"].mean == 209.6552

    assert cols["region"].dtype == "text"
    assert cols["region"].top_values == ["North (8)", "South (8)", "East (7)"]
    assert cols["product"].top_values == ["Doohickey (10)", "Gadget (10)", "Widget (10)"]


def test_profile_json_exact_numbers(examples_dir):
    profile = profile_json(
        (examples_dir / "data/metrics_sample.json").read_text(encoding="utf-8")
    )
    assert profile.format == "json"
    assert profile.rows == 8
    cols = {c.name: c for c in profile.columns}
    assert cols["p95_ms"].dtype == "number"
    assert cols["p95_ms"].missing == 1
    assert cols["p95_ms"].mean == 73.8
    assert cols["p50_ms"].mean == 18.475
    assert cols["error_rate"].mean == 0.0049
    assert cols["service"].top_values == ["auth (2)", "billing (2)", "gateway (2)"]


def test_profile_rejects_bad_input():
    with pytest.raises(ToolError, match="no data rows"):
        profile_csv("only_header\n")
    with pytest.raises(ToolError, match="invalid JSON"):
        profile_json("{nope")
    with pytest.raises(ToolError, match="array of record"):
        profile_json('{"a": 1}')


def test_suggest_charts_rules(examples_dir):
    profile = profile_csv(
        (examples_dir / "data/sales_sample.csv").read_text(encoding="utf-8")
    )
    charts = suggest_charts(profile)
    assert charts[0] == "Bar chart: mean units per date"
    assert any("Histogram" in c for c in charts)
    assert any("Scatter" in c for c in charts)
    assert len(charts) <= 4


# --------------------------------------------------------------------- prompts


def test_prompts_carry_evidence():
    stats, _ = parse_unified_diff("--- a/x\n+++ b/x\n@@ -1 +1,2 @@\n line\n+new\n")
    system, user = review_prompts("+new line", stats, focus="security")
    assert "[hy3-mcp" not in system  # marker is added by Hy3Client, not here
    assert "=== BEGIN DIFF ===" in user and "+new line" in user

    ranked = [ScoredChunk(chunk=Chunk("d.md", 0, "Hy3 has 256K context."), score=3)]
    _, user = docs_prompts("context?", ranked)
    assert "[chunk 1 | d.md#0]" in user and "256K" in user

    profile = profile_json('[{"a": 1}, {"a": 2}]')
    _, user = data_prompts("trend?", profile)
    assert "PROFILE JSON" in user and '"rows": 2' in user

    evidence = [Evidence(kind="search", ref="T <http://u>", snippet="snip")]
    _, user = research_prompts("topic", evidence)
    assert "[source 1 | search:T <http://u>]" in user and "snip" in user


# ------------------------------------------------- in-process tool invocations


async def test_review_input_validation(offline_app):
    with pytest.raises(ToolError, match="exactly one"):
        await offline_app.call_tool("review_code", {})
    with pytest.raises(ToolError, match="exactly one"):
        await offline_app.call_tool(
            "review_code", {"diff_text": "+x", "path": DEMO_DIFF}
        )


async def test_review_code_offline_end_to_end(offline_app):
    _, result = await offline_app.call_tool("review_code", {"path": DEMO_DIFF})
    assert result["mode"] == "offline"
    assert result["stats"]["hunks"] == 2
    assert len(result["heuristic_flags"]) == 5
    assert result["markdown"].startswith("> OFFLINE DEMO MODE")
    assert result["markdown"].rstrip().endswith("<!-- effort=high -->")


async def test_review_focus_filters_flags(offline_app):
    _, result = await offline_app.call_tool(
        "review_code", {"path": DEMO_DIFF, "focus": "security"}
    )
    assert [f["category"] for f in result["heuristic_flags"]] == ["security"]


async def test_ask_docs_offline_end_to_end(offline_app):
    _, result = await offline_app.call_tool(
        "ask_docs",
        {"question": "What is the context length of Hy3?", "docs_path": "examples/docs"},
    )
    assert result["mode"] == "offline"
    assert result["searched_files"] == 2
    assert result["citations"][0]["file"].endswith("hy3_intro.md")
    assert "256K" in result["markdown"]
    assert result["markdown"].rstrip().endswith("<!-- effort=no_think -->")


async def test_ask_docs_absolute_docs_dir_outside_root(tmp_path):
    """An explicit absolute HY3_MCP_DOCS_DIR outside HY3_MCP_ROOT must work."""
    from hy3_mcp.server import build_app
    from hy3_mcp.settings import Settings

    root = tmp_path / "root"
    kb = tmp_path / "kb"
    root.mkdir()
    kb.mkdir()
    (kb / "intro.md").write_text(
        "# Hy3\nHy3 supports a 256K context window.", encoding="utf-8"
    )
    settings = Settings.from_env(
        {
            "HY3_MCP_OFFLINE": "1",
            "HY3_MCP_ROOT": str(root),
            "HY3_MCP_DOCS_DIR": str(kb),
        }
    )
    app = build_app(settings)
    _, result = await app.call_tool(
        "ask_docs", {"question": "What is the context window of Hy3?"}
    )
    assert result["searched_files"] == 1
    assert result["citations"][0]["file"] == "intro.md"


async def test_ask_docs_no_hit_skips_llm(offline_app):
    _, result = await offline_app.call_tool(
        "ask_docs",
        {"question": "zzzz qqqq xxxx", "docs_path": "examples/docs"},
    )
    assert result["citations"] == []
    assert "OFFLINE DEMO MODE" not in result["markdown"]  # no LLM call happened
    assert "No relevant content" in result["markdown"]


async def test_analyze_data_offline_end_to_end(offline_app):
    _, result = await offline_app.call_tool(
        "analyze_data", {"path": "examples/data/sales_sample.csv"}
    )
    assert result["profile"]["rows"] == 30
    assert result["chart_suggestions"][0] == "Bar chart: mean units per date"
    assert "30 rows and 5 columns" in result["markdown"]


async def test_analyze_data_rejects_other_extensions(offline_app):
    with pytest.raises(ToolError, match="csv and .json"):
        await offline_app.call_tool("analyze_data", {"path": "examples/diffs/demo.diff"})


async def test_deep_research_offline_end_to_end(offline_app):
    _, result = await offline_app.call_tool(
        "deep_research",
        {
            "topic": "Hy3 agent capabilities",
            "source_paths": ["examples/docs/hy3_intro.md"],
            "max_sources": 3,
        },
    )
    assert result["search_provider"] == "offline"
    kinds = [e["kind"] for e in result["evidence"]]
    assert kinds.count("search") == 3 and kinds.count("file") == 1
    assert "Research notes" in result["markdown"]
    assert result["markdown"].rstrip().endswith("<!-- effort=high -->")


async def test_deep_research_refuses_without_sources(offline_app):
    with pytest.raises(ToolError, match="no evidence"):
        await offline_app.call_tool(
            "deep_research", {"topic": "anything", "use_search": False}
        )


async def test_hy3_status_counts_usage(offline_app):
    _, before = await offline_app.call_tool("hy3_status", {})
    assert before["mode"] == "offline"
    assert before["api_key_present"] is False
    assert before["usage"]["calls"] == 0
    await offline_app.call_tool("review_code", {"diff_text": "+eval(x)"})
    _, after = await offline_app.call_tool("hy3_status", {})
    assert after["usage"]["calls"] == 1
