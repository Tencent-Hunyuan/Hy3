#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export HY3_MOCK=1
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON="python3"

"$PYTHON" - <<'PY'
import json
from server import clarify_or_plan, run_deep_research, critique_and_finalize, get_research_status

plan = json.loads(clarify_or_plan("MCP 深度研究助手应如何设计"))
print("plan session", plan["session_id"])
print("sub_questions", len(plan["plan"]["sub_questions"]))

run = json.loads(run_deep_research(session_id=plan["session_id"], max_iterations=2))
print("evidence", run["evidence_count"], "iterations", run["iterations"])
print("draft_head", run["draft_markdown"][:180].replace("\n", " "))

final = json.loads(critique_and_finalize(session_id=plan["session_id"]))
print("report_head", final["report_markdown"][:180].replace("\n", " "))

st = json.loads(get_research_status(plan["session_id"]))
print("status", st["has_draft"], st["has_report"], "gaps", st["gaps"])
print("OK")
PY
