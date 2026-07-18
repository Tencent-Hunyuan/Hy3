#!/usr/bin/env bash
# 本地冒烟：不经过 MCP 客户端，直接调用 tool 函数（mock）。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export HY3_MOCK=1
PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi
"$PYTHON" - <<'PY'
from server import web_search, fetch_url, hy3_analyze, hy3_research_report

print("== web_search ==")
print(web_search("Hy3 MCP deep research", 3)[:400], "...\n")

print("== fetch_url ==")
print(fetch_url("https://example.com", 500)[:400], "...\n")

print("== hy3_analyze ==")
print(hy3_analyze("Hy3 适合做什么？", "Hy3 是腾讯混元面向 Agent/代码场景的模型。")[:500], "...\n")

print("== hy3_research_report ==")
print(hy3_research_report("Hy3 深度研究助手", "证据：MCP + 搜索 + Hy3 分析可组成研究流水线。")[:500], "...")
print("\nOK")
PY
