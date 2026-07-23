from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .config import load_settings
from .tools import (
    analyze_lead_tool,
    batch_score_leads_tool,
    generate_outreach_plan_tool,
    query_knowledge_base_tool,
    status_tool,
)


def build_app():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the package first: pip install . or uvx --from . hy3-leadintel-mcp") from exc

    settings = load_settings()
    app = FastMCP("hy3-leadintel-mcp")

    @app.tool()
    def analyze_lead(
        company: str,
        industry: str = "",
        website: str = "",
        notes: str = "",
        product_context: str = "",
    ) -> dict[str, Any]:
        """Analyze a B2B lead with Hy3 and return ICP fit, priority, buying signals, risks, and next action."""

        return analyze_lead_tool(
            settings,
            {
                "company": company,
                "industry": industry,
                "website": website,
                "notes": notes,
                "product_context": product_context,
            },
        )

    @app.tool()
    def query_knowledge_base(question: str, docs_dir: str = "examples/knowledge_base", top_k: int = 4) -> dict[str, Any]:
        """Search local product or market documents, then ask Hy3 to answer with grounded citations."""

        return query_knowledge_base_tool(settings, question, docs_dir, top_k)

    @app.tool()
    def generate_outreach_plan(
        company: str,
        objective: str,
        channel: str = "email",
        lead_context: str = "",
        evidence: str = "",
    ) -> dict[str, Any]:
        """Generate a sales outreach plan with message copy, follow-up cadence, proof points, and CRM actions."""

        return generate_outreach_plan_tool(
            settings,
            {
                "company": company,
                "objective": objective,
                "channel": channel,
                "lead_context": lead_context,
                "evidence": evidence,
            },
        )

    @app.tool()
    def batch_score_leads(input_path: str, focus: str = "", output_path: str = "") -> dict[str, Any]:
        """Read a local CSV or JSON lead list, score every lead, optionally export a JSON report, and summarize with Hy3."""

        return batch_score_leads_tool(settings, input_path, focus=focus, output_path=output_path)

    @app.tool()
    def hy3_leadintel_status() -> dict[str, Any]:
        """Report server configuration, model name, mode, root directory, and available LeadIntel MCP tools."""

        return status_tool(settings)

    return app


def selfcheck() -> int:
    settings = load_settings()
    print(json.dumps(status_tool(settings), ensure_ascii=False, indent=2))
    lead = analyze_lead_tool(
        settings,
        {
            "company": "Aurora Motion GmbH",
            "industry": "manufacturing automation",
            "notes": "Looking for export-ready hollow-cup motor suppliers; RFQ expected this quarter.",
            "product_context": "High-efficiency motors for robotics and medical devices.",
        },
    )
    print(f"[selfcheck] analyze_lead -> {lead['company']} {lead['priority']} score={lead['score']}")
    kb = query_knowledge_base_tool(settings, "What proof points support robotics motor outreach?", "examples/knowledge_base", 3)
    print(f"[selfcheck] query_knowledge_base -> {len(kb['citations'])} citation(s)")
    batch = batch_score_leads_tool(settings, "examples/leads/sample_leads.csv", focus="motor export")
    print(f"[selfcheck] batch_score_leads -> {batch['count']} lead(s)")
    print("[selfcheck] PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hy3 LeadIntel MCP Server")
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    parser.add_argument("--selfcheck", action="store_true", help="Run an offline-friendly local smoke check.")
    args = parser.parse_args(argv)

    if args.version:
        print(f"hy3-leadintel-mcp {__version__}")
        return 0
    if args.selfcheck:
        return selfcheck()

    app = build_app()
    app.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
