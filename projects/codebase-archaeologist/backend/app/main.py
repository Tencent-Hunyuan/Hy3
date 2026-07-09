"""
FastAPI application — REST API + SSE streaming for the Codebase Archaeologist.

Endpoints:
  POST /api/analyze        — Start a new analysis job
  GET  /api/jobs/{id}      — Get job status
  GET  /api/jobs/{id}/sse  — SSE progress stream
  POST /api/qa             — Ask a question about an analyzed repo
  GET  /api/health         — Health check
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.core.cache import get_cache
from app.core.hy3_client import Hy3Client
from app.core.job_manager import JobManager, get_job_manager
from app.core.vector_store import get_vector_store
from app.models import ArchitectureReport, JobPhase, JobStatus
from app.pipeline.orchestrator import Pipeline
from app.pipeline.prompts import QA_SYSTEM, QA_USER_TEMPLATE

logger = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="Codebase Archaeologist",
    description="Hy3-powered intelligent codebase understanding engine",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response models ───────────────────────────────────

class AnalyzeRequest(BaseModel):
    repo_url: str


class AnalyzeResponse(BaseModel):
    job_id: str


class QARequest(BaseModel):
    job_id: str
    question: str


class QAResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]] = []


# ── Shared state ──────────────────────────────────────────────

def _get_pipeline() -> Pipeline:
    return Pipeline(settings)


def _get_hy3() -> Hy3Client:
    return Hy3Client(settings)


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def start_analysis(request: AnalyzeRequest):
    """Start a new codebase analysis job."""
    jobs = get_job_manager()
    job_id = jobs.create_job()
    pipeline = _get_pipeline()

    # Launch analysis in background
    asyncio.create_task(_run_analysis(job_id, request.repo_url, pipeline, jobs))

    return AnalyzeResponse(job_id=job_id)


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get current status of an analysis job."""
    jobs = get_job_manager()
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs/{job_id}/sse")
async def stream_job_progress(job_id: str):
    """SSE endpoint for real-time progress updates."""
    jobs = get_job_manager()

    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    queue = jobs.subscribe(job_id)

    async def event_stream():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {data}\n\n"

                    # Check if job is done
                    try:
                        parsed = json.loads(data)
                        phase = parsed.get("phase", "")
                        if phase in (JobPhase.DONE.value, JobPhase.FAILED.value):
                            break
                    except Exception:
                        pass

                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            jobs.unsubscribe(job_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/jobs/{job_id}/report")
async def get_report(job_id: str):
    """Get the final architecture report + token usage for a completed job."""
    jobs = get_job_manager()
    report = jobs.get_result(job_id)
    if not report:
        job = jobs.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=400, detail=f"Report not ready. Current phase: {job.phase}")
    usage = jobs.get_token_usage(job_id) or {}
    return {"report": report.model_dump(), "usage": usage}


@app.get("/api/jobs/{job_id}/usage")
async def get_usage(job_id: str):
    """Get token usage stats for a job."""
    jobs = get_job_manager()
    usage = jobs.get_token_usage(job_id)
    if not usage:
        raise HTTPException(status_code=404, detail="Usage data not available")
    return usage


@app.get("/api/cache")
async def list_cache():
    """List all cached analyses."""
    cache = get_cache()
    return {"entries": cache.list_entries()}


@app.delete("/api/cache")
async def clear_cache(repo_url: str | None = None, commit_hash: str | None = None):
    """Invalidate cached analyses."""
    cache = get_cache()
    if repo_url:
        count = cache.invalidate(repo_url, commit_hash)
    else:
        count = 0
        for entry in cache.list_entries():
            count += cache.invalidate(entry["repo"])
    return {"cleared": count}


# ── PR Impact Analysis ────────────────────────────────────────

class PRImpactRequest(BaseModel):
    repo_url: str
    pr_number: int
    pr_title: str = ""
    changed_files: list[str] = []
    lines_added: int = 0
    lines_removed: int = 0
    pr_diff: str = ""


@app.post("/api/pr-impact")
async def analyze_pr_impact(request: PRImpactRequest):
    """Analyze architectural impact of a pull request."""
    jobs = get_job_manager()
    job_id = jobs.create_job()
    asyncio.create_task(_run_pr_impact(job_id, request, jobs))
    return {"job_id": job_id}


@app.post("/api/qa/stream")
async def ask_question_stream(request: QARequest):
    """Ask a question — SSE streaming response with Hy3 cache optimization.

    Uses mixed retrieval: structured (DepGraph/Report) + semantic (VectorStore).
    Response streams token-by-token via SSE.
    """
    jobs = get_job_manager()
    report = jobs.get_result(request.job_id)

    if not report:
        raise HTTPException(status_code=400, detail="Analysis not complete. Run analysis first.")

    # ── Structured retrieval ──────────────────────────────────
    structured_results: list[str] = []

    structured_results.append(
        f"架构: {report.overview.architecture_style}\n"
        f"摘要: {report.overview.summary[:500]}"
    )

    keywords = request.question.lower().split()
    for mod in report.modules:
        mod_text = f"{mod.name} ({mod.path}): {mod.responsibility}"
        if any(kw in mod_text.lower() for kw in keywords):
            structured_results.append(mod_text)

    for risk in report.risks:
        loc_str = ", ".join(risk.location) if isinstance(risk.location, list) else str(risk.location)
        risk_text = f"[{risk.severity}] {risk.risk_type}: {loc_str} — {risk.impact}"
        if any(kw in risk_text.lower() for kw in keywords):
            structured_results.append(risk_text)

    for chain in report.call_chains:
        chain_text = f"调用链 '{chain.name}': {' → '.join(chain.sequence)}"
        if any(kw in chain_text.lower() for kw in keywords):
            structured_results.append(chain_text)

    all_context = "\n\n".join(structured_results[:10])[:8000]

    hy3 = _get_hy3()

    user_msg = QA_USER_TEMPLATE.format(
        repo_name=getattr(report.overview, 'language', '') or "analyzed repository",
        architecture_style=report.overview.architecture_style,
        context_snippets=all_context,
        question=request.question,
    )

    async def generate():
        """SSE event generator for streaming QA."""
        import time
        t0 = time.monotonic()
        full_answer = ""

        try:
            stream = await hy3.chat_stream(
                messages=[
                    {"role": "system", "content": QA_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                model=settings.hy3_model,
                max_tokens=2048,
                temperature=0.3,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_answer += token
                    yield f"data: {json.dumps({'token': token})}\n\n"

            elapsed = time.monotonic() - t0
            yield f"data: {json.dumps({'done': True, 'elapsed_ms': int(elapsed * 1000), 'full_answer': full_answer})}\n\n"

        except Exception as e:
            logger.exception("QA stream failed")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/qa", response_model=QAResponse)
async def ask_question(request: QARequest):
    """Ask a question about an analyzed codebase (non-streaming fallback)."""
    jobs = get_job_manager()
    report = jobs.get_result(request.job_id)

    if not report:
        raise HTTPException(status_code=400, detail="Analysis not complete. Run analysis first.")

    structured_results: list[str] = []
    structured_results.append(
        f"Architecture: {report.overview.architecture_style}\n"
        f"Summary: {report.overview.summary[:500]}"
    )

    keywords = request.question.lower().split()
    for mod in report.modules:
        mod_text = f"{mod.name} ({mod.path}): {mod.responsibility}"
        if any(kw in mod_text.lower() for kw in keywords):
            structured_results.append(mod_text)

    for risk in report.risks:
        loc_str = ", ".join(risk.location) if isinstance(risk.location, list) else str(risk.location)
        risk_text = f"[{risk.severity}] {risk.risk_type}: {loc_str} — {risk.impact}"
        if any(kw in risk_text.lower() for kw in keywords):
            structured_results.append(risk_text)

    for chain in report.call_chains:
        chain_text = f"Call chain '{chain.name}': {' → '.join(chain.sequence)}"
        if any(kw in chain_text.lower() for kw in keywords):
            structured_results.append(chain_text)

    all_context = "\n\n".join(structured_results[:10])[:8000]

    hy3 = _get_hy3()
    user_msg = QA_USER_TEMPLATE.format(
        repo_name=getattr(report.overview, 'language', '') or "analyzed repository",
        architecture_style=report.overview.architecture_style,
        context_snippets=all_context,
        question=request.question,
    )

    response = await hy3.reader(
        system_prompt=QA_SYSTEM,
        user_content=user_msg,
        max_tokens=4096,
    )

    sources: list[dict[str, Any]] = []
    for item in structured_results[:3]:
        if "(" in item and ")" in item:
            path = item.split("(")[1].split(")")[0] if ")" in item.split("(")[1] else ""
            sources.append({"path": path, "type": "structured"})

    return QAResponse(answer=response.content, sources=sources)


# ── Background analysis runner ────────────────────────────────

async def _run_analysis(
    job_id: str,
    repo_url: str,
    pipeline: Pipeline,
    jobs: JobManager,
) -> None:
    """Run analysis in background and update job status."""
    try:
        progress_cb = await jobs.create_progress_callback(job_id)
        report = await pipeline.analyze(repo_url, progress=progress_cb)
        jobs.set_token_usage(job_id, {
            "calls": pipeline.hy3.usage.call_count,
            "prompt_tokens": pipeline.hy3.usage.prompt_tokens,
            "completion_tokens": pipeline.hy3.usage.completion_tokens,
            "cache_read_tokens": pipeline.hy3.usage.cache_read_tokens,
            "total_cost_yuan": round(pipeline.hy3.usage.total_cost_yuan, 6),
            "latency_ms": round(pipeline.hy3.usage.total_latency_ms, 0),
        })
        jobs.complete(job_id, report)
    except Exception as e:
        logger.exception("Analysis job %s failed", job_id)
        jobs.fail(job_id, str(e))


async def _run_pr_impact(
    job_id: str,
    request: PRImpactRequest,
    jobs: JobManager,
) -> None:
    """Run PR impact analysis in background."""
    from backend.app.pipeline.prompts import PR_IMPACT_SYSTEM, PR_IMPACT_USER_TEMPLATE
    try:
        progress_cb = await jobs.create_progress_callback(job_id)

        # Step 1: Clone & build dep graph (use cache if available)
        # For simplicity we do a quick clone, but ideally this reuses an existing analysis
        pipeline = _get_pipeline()
        await progress_cb(JobPhase.INGESTING, 10, "Cloning repository for PR analysis...")
        manifest, _ = await pipeline._phase1_ingest(request.repo_url)

        await progress_cb(JobPhase.GRAPHING, 25, "Building dependency graph...")
        dep_graph = await pipeline._phase2_dep_graph(manifest)

        await progress_cb(JobPhase.ANALYZING, 40, "Analyzing PR impact...")

        # Build graph summary
        graph_summary = json.dumps({
            "core_modules": [
                {"path": m.path, "pagerank": m.pagerank, "in": m.in_degree, "out": m.out_degree}
                for m in dep_graph.core_modules[:20]
            ],
            "entry_points": dep_graph.entry_points,
        }, indent=2, ensure_ascii=False)

        # Find affected dependents for each changed file
        changed_deps_parts: list[str] = []
        for f in request.changed_files:
            deps = [e.source for e in dep_graph.edges if e.target == f]
            changed_deps_parts.append(f"{f}: depended on by [{', '.join(deps[:10])}]")

        changed_deps = "\n".join(changed_deps_parts) or "No dependents found"

        user_msg = PR_IMPACT_USER_TEMPLATE.format(
            pr_number=request.pr_number,
            pr_title=request.pr_title,
            changed_files=len(request.changed_files),
            lines_added=request.lines_added,
            lines_removed=request.lines_removed,
            graph_summary=graph_summary,
            changed_deps=changed_deps,
            pr_diff=request.pr_diff[:15000],
        )

        hy3 = _get_hy3()
        response = await hy3.planner(
            system_prompt=PR_IMPACT_SYSTEM,
            user_content=user_msg,
            max_tokens=4096,
        )

        from app.models import PRImpactReport
        import json as _json
        try:
            data = pipeline._parse_json(response.content)
            report = PRImpactReport(
                pr_number=request.pr_number,
                pr_title=request.pr_title,
                changed_files=len(request.changed_files),
                lines_added=request.lines_added,
                lines_removed=request.lines_removed,
                impacts=data.get("impacts", []),
                review_order=data.get("review_order", []),
            )
        except Exception:
            report = PRImpactReport(
                pr_number=request.pr_number,
                pr_title=request.pr_title,
                changed_files=len(request.changed_files),
                lines_added=request.lines_added,
                lines_removed=request.lines_removed,
                review_order=request.changed_files,
            )

        await progress_cb(JobPhase.DONE, 100, "PR impact analysis complete")
        jobs.complete(job_id, report)

        # Clean up clone
        import shutil
        if manifest.local_path:
            shutil.rmtree(manifest.local_path, ignore_errors=True)

    except Exception as e:
        logger.exception("PR impact analysis %s failed", job_id)
        jobs.fail(job_id, str(e))
