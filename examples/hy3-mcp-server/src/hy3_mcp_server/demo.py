"""Small CLI demos that exercise the MCP tool implementations."""

from __future__ import annotations

import argparse
import json

from .tools import answer_question, build_agent_plan, inspect_data, review_diff


def run_code_review() -> dict:
    diff = """
diff --git a/app.py b/app.py
@@
+user_input = request.args["q"]
+cursor.execute("select * from docs where title = '%s'" % user_input)
"""
    return review_diff(diff, focus="security and regression risk", thinking_mode="deep")


def run_document_qa() -> dict:
    docs = [
        {
            "id": "hy3-readme",
            "title": "Hy3 README",
            "text": "Hy3 is a 295B MoE model with 21B active parameters and OpenAI-compatible chat API examples.",
        },
        {
            "id": "issue-3",
            "title": "Rhino-Bird MCP issue",
            "text": "The MCP server must expose at least three tools and pass keys through environment variables.",
        },
    ]
    return answer_question("What role does Hy3 play in this MCP server?", docs, thinking_mode="deep")


def run_data_insight() -> dict:
    csv_data = "week,signups,retention\n2026-07-01,120,0.42\n2026-07-08,164,0.48\n"
    return inspect_data(csv_data, "What changed week over week?", thinking_mode="fast")


def run_agent_plan() -> dict:
    return build_agent_plan(
        "Review a pull request, summarize risk, and prepare a release note",
        "Available MCP tools include code review, document QA, and data insight.",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("demo", choices=["code-review", "document-qa", "data-insight", "agent-plan"])
    args = parser.parse_args()
    if args.demo == "code-review":
        result = run_code_review()
    elif args.demo == "document-qa":
        result = run_document_qa()
    elif args.demo == "data-insight":
        result = run_data_insight()
    else:
        result = run_agent_plan()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
