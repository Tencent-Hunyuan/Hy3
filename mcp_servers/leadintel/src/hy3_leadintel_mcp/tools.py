from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .batch import score_leads, write_report
from .config import Settings
from .hy3_client import Hy3Client
from .knowledge import query_documents
from .lead_scoring import score_lead_text


SYSTEM = (
    "You are Hy3 LeadIntel, a B2B sales and research operations analyst. "
    "Be evidence-aware, concise, and action-oriented. Do not invent facts that are not in the input."
)


def analyze_lead_tool(settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    company = str(payload.get("company", "")).strip()
    industry = str(payload.get("industry", "")).strip()
    website = str(payload.get("website", "")).strip()
    notes = str(payload.get("notes", "")).strip()
    product_context = str(payload.get("product_context", "")).strip()
    combined = "\n".join([company, industry, website, notes, product_context])
    score = score_lead_text(combined)
    hy3 = Hy3Client(settings).complete(
        SYSTEM,
        json.dumps(
            {
                "task": "Analyze this B2B lead and produce ICP fit, likely pains, buying signals, risks, and next action.",
                "lead": {
                    "company": company,
                    "industry": industry,
                    "website": website,
                    "notes": notes,
                    "product_context": product_context,
                },
                "deterministic_score": score.__dict__,
            },
            ensure_ascii=False,
        ),
    )
    return {
        "company": company,
        "score": score.score,
        "priority": score.priority,
        "positive_signals": score.positive_signals,
        "risks": score.risks,
        "hy3_analysis": hy3.content,
        "hy3_mode": hy3.mode,
        "model": hy3.model,
    }


def query_knowledge_base_tool(settings: Settings, question: str, docs_dir: str, top_k: int) -> dict[str, Any]:
    citations = query_documents(settings.root, docs_dir, question, top_k)
    hy3 = Hy3Client(settings).complete(
        SYSTEM,
        json.dumps(
            {
                "task": "Answer the question using only the provided citations. Say what is missing if evidence is insufficient.",
                "question": question,
                "citations": [citation.__dict__ for citation in citations],
            },
            ensure_ascii=False,
        ),
    )
    return {
        "question": question,
        "answer": hy3.content,
        "citations": [citation.__dict__ for citation in citations],
        "hy3_mode": hy3.mode,
        "model": hy3.model,
    }


def generate_outreach_plan_tool(settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    hy3 = Hy3Client(settings).complete(
        SYSTEM,
        json.dumps(
            {
                "task": "Generate a B2B outreach plan with subject lines, first message, follow-up cadence, proof points, and CRM next steps.",
                "input": payload,
            },
            ensure_ascii=False,
        ),
    )
    return {
        "plan": hy3.content,
        "hy3_mode": hy3.mode,
        "model": hy3.model,
    }


def batch_score_leads_tool(settings: Settings, input_path: str, focus: str = "", output_path: str = "") -> dict[str, Any]:
    rows = score_leads(settings.root, input_path, focus=focus)
    output = write_report(settings.root, output_path, rows) if output_path else None
    hy3 = Hy3Client(settings).complete(
        SYSTEM,
        json.dumps(
            {
                "task": "Summarize the batch lead scoring result and recommend the top outreach order.",
                "focus": focus,
                "top_leads": rows[:5],
            },
            ensure_ascii=False,
        ),
    )
    return {
        "count": len(rows),
        "top_leads": rows[:10],
        "report_path": output,
        "hy3_summary": hy3.content,
        "hy3_mode": hy3.mode,
        "model": hy3.model,
    }


def status_tool(settings: Settings) -> dict[str, Any]:
    return {
        "server": "hy3-leadintel-mcp",
        "root": str(Path(settings.root)),
        "model": settings.model,
        "api_base": settings.api_base,
        "api_key_present": settings.api_key_present,
        "mode": "offline" if settings.offline else "real",
        "tools": ["analyze_lead", "query_knowledge_base", "generate_outreach_plan", "batch_score_leads", "hy3_leadintel_status"],
    }
