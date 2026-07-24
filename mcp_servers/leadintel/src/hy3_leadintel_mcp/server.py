from __future__ import annotations

import argparse
import json
import sys
from typing import Annotated
from typing import Any

from pydantic import Field

from . import __version__
from .config import load_settings
from .tools import (
    analyze_lead_tool,
    batch_score_leads_tool,
    generate_outreach_plan_tool,
    query_knowledge_base_tool,
    status_tool,
)

PARAMETER_DESCRIPTIONS = {
    "analyze_lead": {
        "company": "Company or organization name to analyze.",
        "industry": "Industry, vertical, or market segment for the lead.",
        "website": "Official website or public URL for the lead, if available.",
        "notes": "Free-form sales notes, public profile, buying signals, or CRM context.",
        "product_context": "Your product, offer, ICP, or sales context used to judge fit.",
    },
    "query_knowledge_base": {
        "question": "Question to answer using the local knowledge base.",
        "docs_dir": "Knowledge-base directory under HY3_LEADINTEL_ROOT.",
        "top_k": "Maximum number of grounded citations to retrieve, from 1 to 8.",
    },
    "generate_outreach_plan": {
        "company": "Target company or account name.",
        "objective": "Desired sales outcome, such as book a call, request RFQ, or send samples.",
        "channel": "Outreach channel, for example email, LinkedIn, WeChat, or phone.",
        "lead_context": "Known facts about the lead, pains, objections, or buying stage.",
        "evidence": "Product proof points, citations, or case facts to include in outreach.",
    },
    "batch_score_leads": {
        "input_path": "CSV or JSON lead file path under HY3_LEADINTEL_ROOT.",
        "focus": "Optional scoring focus, such as motor export, medical devices, or robotics.",
        "output_path": "Optional JSON report output path under HY3_LEADINTEL_ROOT.",
    },
}


def build_app():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the package first: pip install . or uvx --from . hy3-leadintel-mcp") from exc

    settings = load_settings()
    app = FastMCP("hy3-leadintel-mcp")

    @app.tool()
    def analyze_lead(
        company: Annotated[str, Field(description="Company or organization name to analyze.")],
        industry: Annotated[str, Field(description="Industry, vertical, or market segment for the lead.")] = "",
        website: Annotated[str, Field(description="Official website or public URL for the lead, if available.")] = "",
        notes: Annotated[str, Field(description="Free-form sales notes, public profile, buying signals, or CRM context.")] = "",
        product_context: Annotated[str, Field(description="Your product, offer, ICP, or sales context used to judge fit.")] = "",
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
    def query_knowledge_base(
        question: Annotated[str, Field(description="Question to answer using the local knowledge base.")],
        docs_dir: Annotated[str, Field(description="Knowledge-base directory under HY3_LEADINTEL_ROOT.")] = "examples/knowledge_base",
        top_k: Annotated[int, Field(description="Maximum number of grounded citations to retrieve, from 1 to 8.")] = 4,
    ) -> dict[str, Any]:
        """Search local product or market documents, then ask Hy3 to answer with grounded citations."""

        return query_knowledge_base_tool(settings, question, docs_dir, top_k)

    @app.tool()
    def generate_outreach_plan(
        company: Annotated[str, Field(description="Target company or account name.")],
        objective: Annotated[str, Field(description="Desired sales outcome, such as book a call, request RFQ, or send samples.")],
        channel: Annotated[str, Field(description="Outreach channel, for example email, LinkedIn, WeChat, or phone.")] = "email",
        lead_context: Annotated[str, Field(description="Known facts about the lead, pains, objections, or buying stage.")] = "",
        evidence: Annotated[str, Field(description="Product proof points, citations, or case facts to include in outreach.")] = "",
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
    def batch_score_leads(
        input_path: Annotated[str, Field(description="CSV or JSON lead file path under HY3_LEADINTEL_ROOT.")],
        focus: Annotated[str, Field(description="Optional scoring focus, such as motor export, medical devices, or robotics.")] = "",
        output_path: Annotated[str, Field(description="Optional JSON report output path under HY3_LEADINTEL_ROOT.")] = "",
    ) -> dict[str, Any]:
        """Read a local CSV or JSON lead list, score every lead, optionally export a JSON report, and summarize with Hy3."""

        return batch_score_leads_tool(settings, input_path, focus=focus, output_path=output_path)

    @app.tool()
    def hy3_leadintel_status() -> dict[str, Any]:
        """Report server configuration, model name, mode, root directory, and available LeadIntel MCP tools."""

        return status_tool(settings)

    apply_parameter_descriptions(app)
    return app


def apply_parameter_descriptions(app: Any) -> None:
    # FastMCP 1.28 wraps annotations in a generated model and can drop Field
    # descriptions. Patch the exposed MCP schema directly so clients see clear
    # parameter descriptions, as required by the Rhinobird issue.
    tools = getattr(getattr(app, "_tool_manager", None), "_tools", {})
    for tool_name, descriptions in PARAMETER_DESCRIPTIONS.items():
        tool = tools.get(tool_name)
        if not tool:
            continue
        properties = tool.parameters.setdefault("properties", {})
        for param_name, description in descriptions.items():
            properties.setdefault(param_name, {})["description"] = description


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
