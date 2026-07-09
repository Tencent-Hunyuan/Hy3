"""
Pipeline Orchestrator — drives the 6-phase analysis lifecycle.

Design doc reference: §4 (Core Analysis Pipeline)

Phase 1:  Repo Ingest         (pure engineering)
Phase 2:  Dependency Graph    (pure engineering)
Phase 2.5: Strategy Planning  (Hy3 Planner)
Phase 3:  Batch Analysis      (Hy3 ReAct Agent loop)
Phase 3.5: Consistency Check  (Hy3 Planner)
Phase 4:  Knowledge Synthesis (Hy3 Synthesizer)
Phase 5:  Artifact Generation (pure engineering)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

import git
import networkx as nx
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.core.hy3_client import Hy3Client
from app.models import (
    AnalysisPlan,
    ArchitectureReport,
    BatchFinding,
    BatchPlan,
    ConsistencyReport,
    DepEdge,
    DepGraph,
    DepNode,
    FileInfo,
    FileManifest,
    FileTag,
    JobPhase,
)
from app.pipeline.prompts import (
    CONSISTENCY_SYSTEM,
    CONSISTENCY_USER_TEMPLATE,
    PLANNER_SYSTEM,
    PLANNER_USER_TEMPLATE,
    READER_SYSTEM,
    READER_USER_TEMPLATE,
    SYNTHESIZER_SYSTEM,
    SYNTHESIZER_USER_TEMPLATE,
)
from app.tools.internal_tools import (
    ast_parse,
    dep_graph_query,
    file_read,
    file_tree,
    git_clone,
    grep_search,
    set_active_dep_graph,
)
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ── Type for progress callback ────────────────────────────────
ProgressCallback = Callable[[JobPhase, int, str, dict[str, Any] | None], Any]


# ═══════════════════════════════════════════════════════════════
# Pipeline class
# ═══════════════════════════════════════════════════════════════

class Pipeline:
    """Orchestrates the full 6-phase analysis lifecycle."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.hy3 = Hy3Client(self.settings)
        self.tools = ToolRegistry.get_instance()
        self._register_tools()

    # ── Public API ────────────────────────────────────────────

    async def analyze(
        self,
        repo_url: str,
        *,
        progress: ProgressCallback | None = None,
    ) -> ArchitectureReport:
        """Run full analysis pipeline on a GitHub repository."""
        import atexit
        from app.core.cache import get_cache

        local_path = ""

        try:
            # ── Cache check (before cloning!) ────────────────
            # If we've already analyzed this repo (any commit), serve the
            # cached result instantly.  The user can re-analyze to get the
            # latest commit — this avoids the 10-120 s clone penalty on
            # every re-visit.
            cache = get_cache()
            cached, cached_commit = cache.lookup_by_url(repo_url)
            if cached:
                await self._notify(
                    progress, JobPhase.DONE, 100,
                    f"已有缓存 — 直接展示之前的分析结果 (commit {cached_commit[:12]})",
                    cached,
                )
                return cached
            # ─────────────────────────────────────────────────

            # Phase 1
            await self._notify(progress, JobPhase.INGESTING, 5, "Cloning repository...")
            result = await self._phase1_ingest(repo_url)
            manifest = result[0]
            commit_hash = result[1] if len(result) > 1 else "0000000000000000000000000000000000000000"
            local_path = manifest.local_path

            # ── Precise cache match (exact commit) ───────────
            # Double-check after clone — if we already cached this exact
            # commit previously, skip re-analysis.  (lookup_by_url above
            # serves the latest cached commit; this serves an exact match.)
            cached = cache.lookup(repo_url, commit_hash)
            if cached:
                await self._notify(
                    progress, JobPhase.DONE, 100,
                    f"Cache hit — using previous analysis for commit {commit_hash[:12]}",
                    cached,
                )
                return cached
            # ─────────────────────────────────────────────────

            # Phase 2
            await self._notify(progress, JobPhase.GRAPHING, 15, "Building dependency graph...")
            dep_graph = await self._phase2_dep_graph(manifest)

            # Phase 2.5
            await self._notify(progress, JobPhase.PLANNING, 25, "Planning analysis strategy...")
            analysis_plan = await self._phase25_planning(manifest, dep_graph)

            # Phase 3
            await self._notify(
                progress, JobPhase.ANALYZING, 30,
                f"Analyzing code in {len(analysis_plan.batches)} batches...",
            )
            batch_findings = await self._phase3_batch_analysis(
                manifest, dep_graph, analysis_plan, progress
            )

            # Phase 3.5
            await self._notify(
                progress, JobPhase.CONSISTENCY_CHECK, 80,
                "Checking cross-batch consistency...",
            )
            consistency = await self._phase35_consistency_check(
                manifest, dep_graph, batch_findings
            )

            # Phase 4
            await self._notify(
                progress, JobPhase.SYNTHESIZING, 88,
                "Synthesizing architecture report...",
            )
            report = await self._phase4_synthesis(
                manifest, dep_graph, batch_findings, consistency
            )

            # ── Enrich report with ground-truth dependency data ──
            # Hy3 synthesizer may skip or mangle module depends_on/depended_by.
            # Patch them from the locally-built dependency graph (Phase 2) which
            # has exact import-level accuracy.
            self._patch_module_deps(report, dep_graph)

            # ── Persist to cache ────────────────────────────
            cache.store(
                repo_url, commit_hash, report,
                metadata={
                    "cost_summary": self.hy3.usage.summary(),
                    "total_cost_yuan": round(self.hy3.usage.total_cost_yuan, 6),
                    "api_calls": self.hy3.usage.call_count,
                    "repo_name": manifest.repo_name,
                    "language": manifest.language,
                    "framework": manifest.framework,
                    "code_files": manifest.code_files,
                    "total_files": manifest.total_files,
                },
            )
            # ─────────────────────────────────────────────────

            # Phase 5
            await self._notify(progress, JobPhase.DONE, 100, "Analysis complete.", report)
            return report

        finally:
            # Clean up cloned repo — temp directory, not persisted
            if local_path:
                try:
                    shutil.rmtree(local_path, ignore_errors=True)
                    logger.debug("Cleaned up: %s", local_path)
                except Exception:
                    pass

    # ═══════════════════════════════════════════════════════════
    # Phase 1: Repo Ingest
    # ═══════════════════════════════════════════════════════════

    async def _phase1_ingest(self, repo_url: str) -> tuple[FileManifest, str]:
        result = await git_clone(repo_url)
        if "error" in result:
            raise RuntimeError(f"Clone failed: {result['error']}")

        local_path = result["local_path"]
        commit_hash = result.get("commit", "0000000000000000000000000000000000000000")
        root = Path(local_path)

        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

        # Detect language and framework
        language, framework = self._detect_project_type(root)

        # Scan files
        files: list[FileInfo] = []
        total_tokens = 0
        for file_path in root.rglob("*"):
            if self._should_skip(file_path):
                continue

            rel_path = str(file_path.relative_to(root))
            info = self._categorize_file(file_path, rel_path, language)
            files.append(info)
            total_tokens += info.estimated_tokens

        manifest = FileManifest(
            repo_name=repo_name,
            repo_url=repo_url,
            local_path=local_path,
            language=language,
            framework=framework,
            total_files=len(files),
            code_files=sum(1 for f in files if not f.is_binary),
            estimated_total_tokens=total_tokens,
            files=files,
        )
        return manifest, commit_hash

    # ═══════════════════════════════════════════════════════════
    # Phase 2: Dependency Graph
    # ═══════════════════════════════════════════════════════════

    async def _phase2_dep_graph(self, manifest: FileManifest) -> DepGraph:
        root = Path(manifest.local_path)

        # Build graph
        G = nx.DiGraph()
        import_map: dict[str, set[str]] = {}  # file → {imported files}

        for finfo in manifest.files:
            if finfo.is_binary:
                continue
            p = root / finfo.path
            G.add_node(finfo.path)

            try:
                imports = self._extract_imports(p, manifest.language)
            except Exception:
                imports = set()

            # Resolve imports to repo-internal files
            resolved = self._resolve_imports(imports, manifest.files, finfo.path, manifest.language)
            import_map[finfo.path] = resolved

            for target in resolved:
                if target in G:
                    G.add_edge(finfo.path, target)

        # Compute metrics (use numpy backend, not scipy)
        try:
            pagerank = nx.pagerank(G, alpha=self.settings.dep_graph_pagerank_alpha)
        except Exception:
            pagerank = {n: 1.0 / max(G.number_of_nodes(), 1) for n in G.nodes()}

        nodes = []
        for node_path in G.nodes():
            nodes.append(DepNode(
                path=node_path,
                pagerank=round(pagerank.get(node_path, 0.0), 6),
                in_degree=G.in_degree(node_path),
                out_degree=G.out_degree(node_path),
            ))

        edges = [
            DepEdge(source=src, target=tgt)
            for src, tgt in G.edges()
        ]

        core = sorted(nodes, key=lambda n: n.pagerank, reverse=True)[:20]

        # Detect cycles (nx.simple_cycles can return mixed types — normalize to str)
        cycles: list[dict[str, Any]] = []
        try:
            raw = list(nx.simple_cycles(G))
            for c in raw:
                if len(c) > self.settings.dep_graph_max_cycle_length:
                    continue
                cycle_nodes = [str(n) for n in c]
                cycles.append({"nodes": cycle_nodes, "length": len(cycle_nodes)})
            cycles = cycles[:20]
        except Exception:
            pass

        # Entry points
        entry_points = [
            f.path for f in manifest.files
            if FileTag.ENTRY_POINT in f.tags
        ]
        if not entry_points:
            # Heuristic: nodes with high PageRank but low in_degree are likely entries
            entry_candidates = sorted(nodes, key=lambda n: (-n.pagerank, n.in_degree))[:3]
            entry_points = [n.path for n in entry_candidates if n.in_degree <= 5]

        # Orphans
        orphans = [n.path for n in nodes if G.in_degree(n.path) == 0 and G.out_degree(n.path) == 0]

        # Config files
        config_files = [f.path for f in manifest.files if FileTag.CONFIG in f.tags]

        dep_graph = DepGraph(
            nodes=nodes,
            edges=edges,
            core_modules=core,
            entry_points=entry_points,
            cycles=cycles,
            orphans=orphans,
            config_files=config_files,
        )

        set_active_dep_graph(dep_graph, G)
        return dep_graph

    # ═══════════════════════════════════════════════════════════
    # Phase 2.5: Strategy Planning (Hy3 Planner)
    # ═══════════════════════════════════════════════════════════

    async def _phase25_planning(
        self, manifest: FileManifest, dep_graph: DepGraph
    ) -> AnalysisPlan:
        # Build directory tree string
        tree_result = await file_tree(manifest.local_path, max_depth=5)
        dir_tree = json.dumps(tree_result.get("tree", {}), indent=2)[:3000]

        # Core modules summary
        core_str = "\n".join(
            f"  {m.path} (PR={m.pagerank:.4f}, in={m.in_degree}, out={m.out_degree})"
            for m in dep_graph.core_modules[:20]
        )

        # Cycles
        cycles_str = "\n".join(
            f"  Cycle of {c.length}: {' → '.join(c.nodes)}"
            for c in dep_graph.cycles[:10]
        ) or "  None detected"

        # Orphans
        orphans_str = "\n".join(f"  {o}" for o in dep_graph.orphans[:20]) or "  None"

        # Size distribution
        size_buckets = {"0-500行": 0, "500-2000行": 0, "2000-5000行": 0, "5000+行": 0}
        for f in manifest.files:
            if f.lines <= 500:
                size_buckets["0-500行"] += 1
            elif f.lines <= 2000:
                size_buckets["500-2000行"] += 1
            elif f.lines <= 5000:
                size_buckets["2000-5000行"] += 1
            else:
                size_buckets["5000+行"] += 1
        size_dist = "\n".join(f"  {k}: {v} files" for k, v in size_buckets.items())

        user_msg = PLANNER_USER_TEMPLATE.format(
            repo_name=manifest.repo_name,
            language=manifest.language,
            framework=manifest.framework,
            code_files=manifest.code_files,
            total_files=manifest.total_files,
            estimated_tokens=manifest.estimated_total_tokens,
            dir_tree=dir_tree,
            core_modules=core_str,
            entry_points=", ".join(dep_graph.entry_points),
            cycles=cycles_str,
            orphans=orphans_str,
            size_distribution=size_dist,
        )

        response = await self.hy3.planner(
            system_prompt=PLANNER_SYSTEM,
            user_content=user_msg,
            max_tokens=4096,
        )

        try:
            plan_data = self._parse_json(response.content)

            # Sanitize Hy3 output: fill missing batch ids, handle string depends_on
            for i, b in enumerate(plan_data.get("batches", [])):
                if "id" not in b or b["id"] is None:
                    b["id"] = i + 1
                if not isinstance(b["id"], int):
                    try:
                        b["id"] = int(b["id"])
                    except (ValueError, TypeError):
                        b["id"] = i + 1

                # Clean depends_on: strings → ints
                deps = b.get("depends_on", [])
                if isinstance(deps, list):
                    clean_deps: list[int] = []
                    for d in deps:
                        if isinstance(d, int):
                            clean_deps.append(d)
                        elif isinstance(d, str):
                            try:
                                clean_deps.append(int(d))
                            except ValueError:
                                pass  # drop unresolvable string refs
                    b["depends_on"] = clean_deps
                else:
                    b["depends_on"] = []

                # Ensure estimated_tokens is an int
                if "estimated_tokens" not in b or not isinstance(b.get("estimated_tokens"), (int, float)):
                    b["estimated_tokens"] = 0

            return AnalysisPlan(**plan_data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Planner JSON parse failed: %s, using fallback", e)
            return self._fallback_plan(manifest, dep_graph)

    # ═══════════════════════════════════════════════════════════
    # Phase 3: Batch Analysis (ReAct Agent loop)
    # ═══════════════════════════════════════════════════════════

    async def _phase3_batch_analysis(
        self,
        manifest: FileManifest,
        dep_graph: DepGraph,
        plan: AnalysisPlan,
        progress: ProgressCallback | None = None,
    ) -> list[BatchFinding]:
        batches = plan.batches
        total = len(batches)
        findings: list[BatchFinding] = []
        previous_summaries: list[str] = []

        for i, batch in enumerate(batches):
            pct = 30 + int((i / total) * 50) if total > 0 else 50
            await self._notify(
                progress, JobPhase.ANALYZING, pct,
                f"Batch {batch.id}/{total}: analyzing {', '.join(batch.files[:3])}..."
                + (f" (+{len(batch.files) - 3} more)" if len(batch.files) > 3 else ""),
                {"current_batch": batch.id, "total_batches": total},
            )

            finding = await self._analyze_single_batch(
                manifest, batch, total, previous_summaries,
                plan.strategy, plan.focus_dimensions, plan.special_instructions,
            )
            findings.append(finding)

            # Accumulate summary for next batches
            summary = self._summarize_finding(finding)
            previous_summaries.append(summary)

        return findings

    async def _analyze_single_batch(
        self,
        manifest: FileManifest,
        batch: BatchPlan,
        total_batches: int,
        previous_summaries: list[str],
        strategy: str,
        focus_dimensions: list[str],
        special_instructions: str,
    ) -> BatchFinding:
        root = Path(manifest.local_path)

        # Read all files in batch (with hard token cap to avoid context overflow / OOM)
        HARD_CAP_TOKENS = self.settings.max_context_tokens - 10_000  # leave headroom for prompt + previous summaries
        files_content_parts: list[str] = []
        total_tokens = 0

        for file_path in batch.files:
            # Stop reading if we've already hit the hard cap
            if total_tokens >= HARD_CAP_TOKENS:
                files_content_parts.append(f"\n... ({len(batch.files) - len(files_content_parts)} more files skipped to stay within context limit)\n")
                break

            result = await file_read(str(root / file_path))
            if "error" in result:
                if "not found" not in result.get("error", "").lower():
                    files_content_parts.append(f"\n## {file_path}\n[Read error: {result['error']}]\n")
                continue
            content = result["content"]
            est_tokens = max(len(content) // 3, 1)

            if total_tokens + est_tokens > HARD_CAP_TOKENS:
                # Truncate this file instead of skipping it entirely
                available = HARD_CAP_TOKENS - total_tokens
                truncated_chars = max(available * 3, 500)
                truncated = content[:truncated_chars]
                files_content_parts.append(
                    f"\n## {file_path}\n```{result['language']}\n{truncated}\n... [截断: 超出上下文限制]\n```\n"
                )
                total_tokens = HARD_CAP_TOKENS  # mark as full
            else:
                files_content_parts.append(
                    f"\n## {file_path}\n```{result['language']}\n{content}\n```\n"
                )
                total_tokens += est_tokens

        files_content = "\n".join(files_content_parts)

        # Safety: if content is still over ~250K chars, hard-truncate
        if len(files_content) > 250_000 * 3:
            files_content = files_content[:250_000 * 3] + "\n... [内容过长，已强制截断]\n"

        # Build previous summaries
        prev_text = "\n---\n".join(
            f"Batch {i + 1} summary:\n{s}" for i, s in enumerate(previous_summaries)
        ) or "(This is the first batch — no previous summaries)"

        # Get tool schemas for ReAct mode
        tool_schemas = self.tools.get_schemas_for([
            "grep_search", "file_read", "ast_parse", "dep_graph_query"
        ])

        user_msg = READER_USER_TEMPLATE.format(
            repo_name=manifest.repo_name,
            batch_id=batch.id,
            total_batches=total_batches,
            strategy=strategy,
            focus_dimensions=", ".join(focus_dimensions),
            previous_summaries=prev_text,
            rationale=batch.rationale,
            special_instructions=special_instructions,
            files_content=files_content,
        )

        # ReAct agent loop
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": READER_SYSTEM},
            {"role": "user", "content": user_msg},
        ]

        for round_num in range(self.settings.max_react_rounds_per_batch):
            is_last = round_num == self.settings.max_react_rounds_per_batch - 1
            effective_tool_choice = (
                "auto" if round_num < 2 and not is_last
                else "none"
            )

            try:
                response = await asyncio.wait_for(
                    self.hy3.chat(
                        messages=messages,
                        reasoning_effort="medium" if round_num == 0 else "low",
                        temperature=0.1,
                        max_tokens=16384,
                        tools=tool_schemas if effective_tool_choice == "auto" else None,
                        tool_choice=effective_tool_choice,
                    ),
                    timeout=180,  # per-round timeout — move on if Hy3 takes too long
                )
            except asyncio.TimeoutError:
                logger.warning("Batch %d round %d timed out", batch.id, round_num + 1)
                # Return what we have so far
                return BatchFinding(
                    batch_id=batch.id,
                    files_analyzed=batch.files,
                    clues_for_next=f"Analysis timed out after {round_num + 1} rounds",
                )

            # No tool calls → final response
            if not response.tool_calls or response.finish_reason == "stop":
                try:
                    finding_data = self._parse_json(response.content)
                    finding_data = self._normalize_finding(finding_data)
                    finding_data["batch_id"] = batch.id
                    finding_data.setdefault("files_analyzed", batch.files)
                    return BatchFinding(**finding_data)
                except (json.JSONDecodeError, ValidationError) as e:
                    logger.warning("Batch %d JSON parse failed: %s", batch.id, e)
                    return BatchFinding(
                        batch_id=batch.id,
                        files_analyzed=batch.files,
                        clues_for_next=response.content[:500],
                    )

            # Execute tool calls
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls,
            }
            messages.append(assistant_msg)

            for tc in response.tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                result = await self.tools.execute(tool_name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False)[:4000],
                })

        # Max rounds exceeded — return partial result
        return BatchFinding(
            batch_id=batch.id,
            files_analyzed=batch.files,
            clues_for_next=f"Analysis incomplete after {self.settings.max_react_rounds_per_batch} rounds",
        )

    # ═══════════════════════════════════════════════════════════
    # Phase 3.5: Consistency Check (Hy3 Planner)
    # ═══════════════════════════════════════════════════════════

    async def _phase35_consistency_check(
        self,
        manifest: FileManifest,
        dep_graph: DepGraph,
        findings: list[BatchFinding],
    ) -> ConsistencyReport:
        # Summarize each finding
        summaries = []
        for f in findings:
            summary = self._summarize_finding(f)
            summaries.append(f"## Batch {f.batch_id}\n{summary}")

        batch_text = "\n\n".join(summaries)

        graph_ctx = f"Core modules: {', '.join(m.path for m in dep_graph.core_modules[:10])}"

        user_msg = CONSISTENCY_USER_TEMPLATE.format(
            repo_name=manifest.repo_name,
            code_files=manifest.code_files,
            num_batches=len(findings),
            batch_findings_summary=batch_text,
            graph_context=graph_ctx,
        )

        response = await self.hy3.planner(
            system_prompt=CONSISTENCY_SYSTEM,
            user_content=user_msg,
            max_tokens=16384,
        )

        try:
            data = self._parse_json(response.content)
            return ConsistencyReport(**data)
        except (json.JSONDecodeError, ValidationError):
            return ConsistencyReport()

    # ═══════════════════════════════════════════════════════════
    # Phase 4: Knowledge Synthesis (Hy3 Synthesizer)
    # ═══════════════════════════════════════════════════════════

    async def _phase4_synthesis(
        self,
        manifest: FileManifest,
        dep_graph: DepGraph,
        findings: list[BatchFinding],
        consistency: ConsistencyReport,
    ) -> ArchitectureReport:
        # Graph summary
        graph_summary = json.dumps({
            "nodes": [n.model_dump() for n in dep_graph.nodes[:100]],  # limit to avoid huge payload
            "core_modules": [
                {"path": m.path, "pagerank": m.pagerank, "in": m.in_degree, "out": m.out_degree}
                for m in dep_graph.core_modules[:15]
            ],
            "entry_points": dep_graph.entry_points,
            "cycles": dep_graph.cycles[:10] if isinstance(dep_graph.cycles, list) else [],
        }, indent=2, ensure_ascii=False, default=str)

        # Batch findings (summarized)
        findings_summary = json.dumps(
            [self._finding_to_dict(f) for f in findings],
            indent=2, ensure_ascii=False,
        )

        consistency_json = consistency.model_dump_json(indent=2)

        user_msg = SYNTHESIZER_USER_TEMPLATE.format(
            repo_name=manifest.repo_name,
            language=manifest.language,
            framework=manifest.framework,
            code_files=manifest.code_files,
            total_files=manifest.total_files,
            estimated_tokens=manifest.estimated_total_tokens,
            graph_summary=graph_summary,
            consistency_report=consistency_json,
            batch_findings=findings_summary,
        )

        # JSON Schema for ArchitectureReport
        schema = self._arch_report_schema()

        response = await self.hy3.synthesizer(
            system_prompt=SYNTHESIZER_SYSTEM,
            user_content=user_msg,
            json_schema=schema,
        )

        try:
            data = self._parse_json(response.content)
            return ArchitectureReport(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error("Synthesizer JSON parse failed: %s", e)
            return ArchitectureReport(
                overview={"architecture_style": "Unknown", "summary": response.content[:500]},
            )

    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════

    def _register_tools(self) -> None:
        """Register all internal tools with the registry."""
        from app.tools.internal_tools import (
            AST_PARSE_SCHEMA,
            DEP_GRAPH_QUERY_SCHEMA,
            FILE_READ_SCHEMA,
            FILE_TREE_SCHEMA,
            GIT_CLONE_SCHEMA,
            GREP_SEARCH_SCHEMA,
        )
        self.tools.register("git_clone", "Clone a GitHub repository", GIT_CLONE_SCHEMA, git_clone)
        self.tools.register("file_tree", "Get directory tree", FILE_TREE_SCHEMA, file_tree)
        self.tools.register("file_read", "Read a file's content", FILE_READ_SCHEMA, file_read)
        self.tools.register("grep_search", "Search with regex in the repo", GREP_SEARCH_SCHEMA, grep_search)
        self.tools.register("ast_parse", "Parse Python AST to extract imports, functions, classes", AST_PARSE_SCHEMA, ast_parse)
        self.tools.register("dep_graph_query", "Query the dependency graph", DEP_GRAPH_QUERY_SCHEMA, dep_graph_query)

    def _detect_project_type(self, root: Path) -> tuple[str, str]:
        """Detect primary language and framework."""
        language = "unknown"
        framework = "none"

        if (root / "pyproject.toml").exists() or (root / "setup.py").exists() or (root / "requirements.txt").exists():
            language = "python"
            if (root / "pyproject.toml").exists():
                try:
                    content = (root / "pyproject.toml").read_text()
                    if "fastapi" in content.lower():
                        framework = "FastAPI"
                    elif "django" in content.lower():
                        framework = "Django"
                    elif "flask" in content.lower():
                        framework = "Flask"
                except Exception:
                    pass
        elif (root / "package.json").exists():
            language = "javascript"
            try:
                import json as _json
                pkg = _json.loads((root / "package.json").read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    framework = "Next.js"
                elif "react" in deps:
                    framework = "React"
                elif "vue" in deps:
                    framework = "Vue"
                elif "express" in deps:
                    framework = "Express"
            except Exception:
                pass
        elif (root / "go.mod").exists():
            language = "go"

        return language, framework

    def _should_skip(self, path: Path) -> bool:
        """Determine if a file/directory should be excluded."""
        name = path.name
        # Skip hidden files/dirs
        if name.startswith(".") and name not in (".env.example",):
            return True
        # Skip common ignore dirs
        skip_dirs = {
            "node_modules", "__pycache__", ".git", "venv", ".venv",
            ".idea", ".vscode", "dist", "build", ".next", ".mypy_cache",
            ".pytest_cache", ".ruff_cache", "target",
        }
        if any(p in skip_dirs for p in path.parts):
            return True
        # Skip binary files
        binary_exts = {
            ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
            ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
            ".mp3", ".mp4", ".wav", ".avi", ".mov",
            ".zip", ".tar", ".gz", ".7z", ".rar",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".ttf", ".otf", ".woff", ".woff2", ".eot",
            ".db", ".sqlite", ".sqlite3",
        }
        if path.is_file() and path.suffix.lower() in binary_exts:
            return True
        # Skip files > 5MB
        if path.is_file() and path.stat().st_size > 5 * 1024 * 1024:
            return True
        # Skip test directories (configurable)
        if "test" in path.parts or "tests" in path.parts or path.name.startswith("test_"):
            return True

        return False

    def _categorize_file(self, path: Path, rel_path: str, language: str) -> FileInfo:
        """Categorize a single file."""
        ext = path.suffix.lower()
        code_exts = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rs",
            ".cpp", ".c", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
            ".scala", ".vue", ".svelte", ".css", ".scss", ".less",
            ".html", ".htm", ".xml", ".yaml", ".yml", ".toml", ".json",
            ".md", ".rst", ".txt", ".sh", ".bash", ".zsh", ".fish",
            ".sql", ".graphql", ".proto",
        }

        is_binary = ext not in code_exts
        lines = 0
        tags: list[FileTag] = []

        if not is_binary:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                lines = content.count("\n") + 1
            except Exception:
                is_binary = True

        est_tokens = 0 if is_binary else max(lines * 4, 100)  # rough: ~4 chars per token, min 100 tokens

        # Tagging
        file_lower = rel_path.lower()
        if any(kw in file_lower for kw in ["main", "app", "index", "__main__", "server"]):
            tags.append(FileTag.ENTRY_POINT)
        if any(kw in file_lower for kw in ["config", "settings", ".env", "constants"]):
            tags.append(FileTag.CONFIG)
        if "core" in path.parts:
            tags.append(FileTag.CORE)

        if not tags:
            tags.append(FileTag.UNKNOWN)

        return FileInfo(
            path=rel_path,
            language=self._ext_to_lang(ext),
            lines=max(lines, 1) if not is_binary else 0,
            estimated_tokens=est_tokens,
            tags=tags,
            is_binary=is_binary,
        )

    def _extract_imports(self, path: Path, language: str) -> set[str]:
        """Extract import statements from a file using AST (Python) or tree-sitter (JS/TS)."""
        imports: set[str] = set()

        if language == "python" and path.suffix == ".py":
            try:
                source = path.read_text(encoding="utf-8")
                tree = __import__("ast").parse(source)
                for node in __import__("ast").walk(tree):
                    if isinstance(node, __import__("ast").Import):
                        for alias in node.names:
                            imports.add(alias.name.split(".")[0])
                    elif isinstance(node, __import__("ast").ImportFrom):
                        if node.module:
                            imports.add(node.module.split(".")[0])
            except Exception:
                pass

        elif language in ("javascript", "typescript") and path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            imports |= self._extract_imports_ts(path)

        elif language == "go" and path.suffix == ".go":
            imports |= self._extract_imports_go(path)

        return imports

    def _extract_imports_ts(self, path: Path) -> set[str]:
        """Extract JS/TS imports using tree-sitter for precise AST parsing."""
        imports: set[str] = set()
        try:
            content = path.read_text(encoding="utf-8")
            lang_lib = "typescript" if path.suffix in (".ts", ".tsx") else "javascript"
            lang_module = __import__(f"tree_sitter_{lang_lib}", fromlist=["language"])
            tree_sitter = __import__("tree_sitter")

            parser = tree_sitter.Parser()
            parser.set_language(lang_module.language())
            tree = parser.parse(content.encode("utf-8"))

            # Walk all import_statement and call_expression(require) nodes
            def _walk(node):
                if node.type == "import_statement":
                    # import X from 'y' → get the 'y' string node
                    source_child = node.child_by_field_name("source")
                    if source_child and source_child.type == "string":
                        raw = content[source_child.start_byte:source_child.end_byte]
                        imports.add(raw.strip("'\"").split("/")[0])
                elif node.type == "call_expression":
                    fn = node.child_by_field_name("function")
                    if fn and content[fn.start_byte:fn.end_byte] == "require":
                        args = node.child_by_field_name("arguments")
                        if args and args.named_child_count > 0:
                            first = args.named_child(0)
                            if first and first.type == "string":
                                raw = content[first.start_byte:first.end_byte]
                                imports.add(raw.strip("'\"").split("/")[0])
                for child in node.children:
                    _walk(child)

            _walk(tree.root_node)
        except Exception:
            # Fall back to regex
            import re
            pattern = re.compile(
                r'(?:import\s+(?:[\w*\s{},]*)\s+from\s+["\']([^"\']+)["\'])|'
                r'(?:require\s*\(\s*["\']([^"\']+)["\']\s*\))'
            )
            try:
                for m in pattern.finditer(content):
                    mod = m.group(1) or m.group(2)
                    if mod:
                        imports.add(mod.split("/")[0])
            except Exception:
                pass

        return imports

    def _extract_imports_go(self, path: Path) -> set[str]:
        """Extract Go imports."""
        imports: set[str] = set()
        import re
        try:
            content = path.read_text(encoding="utf-8")
            # Match `import "pkg"` or `import ( "pkg1" \n "pkg2" )`
            block = re.findall(r'import\s*\(\s*([^)]+)\s*\)', content)
            for b in block:
                for m in re.finditer(r'"([^"]+)"', b):
                    imports.add(m.group(1).split("/")[0])
            for m in re.finditer(r'import\s+"([^"]+)"', content):
                imports.add(m.group(1).split("/")[0])
        except Exception:
            pass
        return imports

    def _resolve_imports(
        self,
        imports: set[str],
        all_files: list[FileInfo],
        current_path: str,
        language: str,
    ) -> set[str]:
        """Resolve external import names to repo-internal file paths."""
        resolved: set[str] = set()
        file_paths = {f.path: f for f in all_files}
        file_names = {Path(f.path).stem: f.path for f in all_files}

        for imp in imports:
            # Relative import (Python)
            if imp.startswith("."):
                current_dir = str(Path(current_path).parent)
                depth = len(imp) - len(imp.lstrip("."))
                parts = imp.lstrip(".").split(".")
                candidate = str(Path(current_dir).parent if depth > 1 else Path(current_dir))
                candidate = str(Path(candidate) / "/".join(parts))
                # Try variations
                for suffix in [".py", "/__init__.py", ".js", ".ts", "/index.js", "/index.ts"]:
                    test = candidate + suffix
                    test = test.replace("\\", "/")
                    for fp in file_paths:
                        if fp.endswith(test) or test.endswith(fp):
                            resolved.add(fp)
                            break
                continue

            # Absolute module name
            parts = imp.split(".")
            # Try matching by path segments
            for fp, finfo in file_paths.items():
                path_parts = fp.replace("\\", "/").split("/")
                stem = Path(fp).stem
                if parts[0] == stem or parts[0] in path_parts:
                    resolved.add(fp)
                    continue
                # Match full dotted path
                dotted = fp.replace("/", ".").replace(".py", "").replace(".js", "").replace(".ts", "")
                if imp in dotted or dotted.endswith("." + imp):
                    resolved.add(fp)

        return resolved

    def _fallback_plan(self, manifest: FileManifest, dep_graph: DepGraph) -> AnalysisPlan:
        """Generate a simple plan when Hy3 planning fails — uses tighter token budget per batch."""
        MAX_BATCH_TOKENS = 80_000  # much tighter than 200K to keep API calls fast
        batches: list[BatchPlan] = []
        batch_id = 0
        current_batch_files: list[str] = []
        current_tokens = 0

        # Priority: core modules first, then rest by PageRank
        core_paths = {m.path for m in dep_graph.core_modules[:20]}
        entry_paths = set(dep_graph.entry_points)

        priority_order = sorted(
            [f for f in manifest.files if not f.is_binary],
            key=lambda f: (
                0 if f.path in entry_paths else 1 if f.path in core_paths else 2,
                -(next((m.pagerank for m in dep_graph.core_modules if m.path == f.path), 0)),
                f.path,
            ),
        )

        for f in priority_order:
            if current_tokens + f.estimated_tokens > MAX_BATCH_TOKENS:
                if current_batch_files:
                    batch_id += 1
                    batches.append(BatchPlan(
                        id=batch_id,
                        files=current_batch_files,
                        rationale="Fallback plan — grouped by token budget",
                        estimated_tokens=current_tokens,
                    ))
                    current_batch_files = []
                    current_tokens = 0
            current_batch_files.append(f.path)
            current_tokens += f.estimated_tokens

        if current_batch_files:
            batch_id += 1
            batches.append(BatchPlan(
                id=batch_id,
                files=current_batch_files,
                rationale="Fallback plan — grouped by token budget",
                estimated_tokens=current_tokens,
            ))

        return AnalysisPlan(
            strategy="Token-budget-based batch analysis (fallback)",
            focus_dimensions=["code structure", "dependencies"],
            batches=batches,
            special_instructions="",
        )

    def _summarize_finding(self, finding: BatchFinding) -> str:
        """Condense a BatchFinding into a 1-2K token summary for cross-batch context."""
        parts = [f"Files: {', '.join(finding.files_analyzed)}"]

        if finding.module_roles:
            parts.append("Roles: " + "; ".join(
                f"{m.path} → {m.responsibility[:100]}" for m in finding.module_roles[:5]
            ))

        if finding.design_patterns:
            parts.append("Patterns: " + "; ".join(
                f"{p.pattern} @ {p.location}" for p in finding.design_patterns[:5]
            ))

        if finding.risks:
            parts.append("Risks: " + "; ".join(
                f"[{r.severity}] {r.risk_type}" for r in finding.risks[:5]
            ))

        if finding.clues_for_next:
            parts.append(f"Clues: {finding.clues_for_next}")

        return "\n".join(parts)

    def _finding_to_dict(self, finding: BatchFinding) -> dict[str, Any]:
        """Convert a BatchFinding to a dict for JSON serialization."""
        d = finding.model_dump()
        # Truncate large fields
        for key in ("module_roles", "key_abstractions", "data_flows"):
            if key in d and len(d[key]) > 20:
                d[key] = d[key][:20]
        return d

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Extract and parse JSON from LLM output, handling markdown fences."""
        text = text.strip()
        # Remove markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove opening fence
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove closing fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return json.loads(text)

    def _normalize_finding(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize Hy3's JSON output to match BatchFinding's list-based schema.

        Hy3 sometimes outputs dicts instead of lists for module_roles, patterns, etc.
        """
        # Convert dict to list for module_roles
        if isinstance(data.get("module_roles"), dict):
            items = []
            for path, info in data["module_roles"].items():
                if isinstance(info, dict):
                    items.append({
                        "path": path,
                        "responsibility": info.get("responsibility", str(info)[:200]),
                        "stability": info.get("stability", "medium"),
                    })
                else:
                    items.append({"path": path, "responsibility": str(info)[:200]})
            data["module_roles"] = items

        # Convert dict to list for key_abstractions
        if isinstance(data.get("key_abstractions"), dict):
            items = []
            for name, info in data["key_abstractions"].items():
                if isinstance(info, dict):
                    items.append({
                        "name": name,
                        "kind": info.get("kind", info.get("intent", ""))[:50],
                        "location": info.get("location", ""),
                        "role": info.get("role", str(info.get("intent", "")))[:200],
                    })
                else:
                    items.append({"name": name, "kind": "", "role": str(info)[:200]})
            data["key_abstractions"] = items

        # Convert dict to list for data_flows
        if isinstance(data.get("data_flows"), dict):
            items = []
            for name, desc in data["data_flows"].items():
                if isinstance(desc, dict):
                    items.append({"description": f"{name}: {desc.get('description', str(desc))}"})
                else:
                    items.append({"description": f"{name}: {str(desc)[:200]}"})
            data["data_flows"] = items

        # Convert dict to list for design_patterns
        if isinstance(data.get("design_patterns"), dict):
            items = []
            for pattern_name, info in data["design_patterns"].items():
                if isinstance(info, dict):
                    items.append({
                        "pattern": pattern_name,
                        "location": info.get("location", ""),
                        "appropriateness": info.get("appropriateness", "appropriate"),
                        "note": str(info.get("note", info))[:200],
                    })
                else:
                    items.append({"pattern": pattern_name, "note": str(info)[:200]})
            data["design_patterns"] = items

        # Convert dict to list for risks
        if isinstance(data.get("risks"), dict):
            items = []
            for risk_key, risk_info in data["risks"].items():
                if isinstance(risk_info, dict):
                    items.append({
                        "severity": risk_info.get("severity", "medium"),
                        "risk_type": risk_info.get("risk_type", risk_key),
                        "location": risk_info.get("location", []) if isinstance(risk_info.get("location"), list) else [str(risk_info.get("location", ""))],
                        "impact": risk_info.get("impact", ""),
                        "fix_suggestion": risk_info.get("fix_suggestion", ""),
                    })
                else:
                    items.append({"severity": "medium", "risk_type": risk_key, "location": [], "impact": str(risk_info)[:200]})
            data["risks"] = items

        # Convert dict/anything to string for clues_for_next
        if isinstance(data.get("clues_for_next"), dict):
            data["clues_for_next"] = "; ".join(f"{k}: {v}" for k, v in data["clues_for_next"].items())
        elif isinstance(data.get("clues_for_next"), list):
            data["clues_for_next"] = "; ".join(str(c) for c in data["clues_for_next"])

        return data

    @staticmethod
    def _arch_report_schema() -> dict[str, Any]:
        """Generate the JSON Schema for ArchitectureReport."""
        return {
            "type": "object",
            "properties": {
                "overview": {
                    "type": "object",
                    "properties": {
                        "architecture_style": {"type": "string"},
                        "language": {"type": "string"},
                        "framework": {"type": "string"},
                        "summary": {"type": "string"},
                        "reading_guide": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["architecture_style", "language", "framework", "summary", "reading_guide"],
                },
                "modules": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "path": {"type": "string"},
                            "responsibility": {"type": "string"},
                            "exports": {"type": "array", "items": {"type": "string"}},
                            "depends_on": {"type": "array", "items": {"type": "string"}},
                            "depended_by": {"type": "array", "items": {"type": "string"}},
                            "stability": {"type": "string"},
                        },
                        "required": ["name", "path", "responsibility"],
                    },
                },
                "call_chains": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "sequence": {"type": "array", "items": {"type": "string"}},
                            "description": {"type": "string"},
                        },
                        "required": ["name", "sequence", "description"],
                    },
                },
                "design_patterns": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "location": {"type": "string"},
                            "appropriateness": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["pattern", "location"],
                    },
                },
                "risks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "severity": {"type": "string"},
                            "risk_type": {"type": "string"},
                            "location": {"type": "array", "items": {"type": "string"}},
                            "impact": {"type": "string"},
                            "fix_suggestion": {"type": "string"},
                        },
                        "required": ["severity", "risk_type", "location"],
                    },
                },
                "metrics": {
                    "type": "object",
                    "properties": {
                        "total_modules": {"type": "integer"},
                        "total_classes": {"type": "integer"},
                        "avg_dependency_depth": {"type": "number"},
                        "god_class_candidates": {"type": "array", "items": {"type": "string"}},
                        "test_coverage_estimate": {"type": "string"},
                    },
                },
            },
            "required": ["overview", "modules", "call_chains", "design_patterns", "risks", "metrics"],
        }

    @staticmethod
    def _ext_to_lang(ext: str) -> str:
        lang_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "javascript", ".tsx": "typescript", ".go": "go",
            ".java": "java", ".rs": "rust", ".cpp": "cpp", ".c": "c",
            ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin",
            ".css": "css", ".html": "html", ".json": "json", ".yaml": "yaml",
            ".yml": "yaml", ".toml": "toml", ".md": "markdown", ".sql": "sql",
        }
        return lang_map.get(ext, ext.lstrip("."))

    @staticmethod
    def _patch_module_deps(report: ArchitectureReport, dep_graph: DepGraph) -> None:
        """Overwrite module dependency fields with ground-truth data from Phase 2.

        Hy3's synthesizer often omits or hallucinates depends_on/depended_by,
        but we already have exact import-level edges from the local DepGraph build.
        This ensures the frontend dependency graph always renders correctly.
        """
        # Build lookup: file path → set of depends_on paths, set of depended_by paths
        dep_on: dict[str, set[str]] = {}
        dep_by: dict[str, set[str]] = {}

        for edge in dep_graph.edges:
            dep_on.setdefault(edge.source, set()).add(edge.target)
            dep_by.setdefault(edge.target, set()).add(edge.source)

        # Also add orphans (zero-degree nodes) so they show up
        for node in dep_graph.nodes:
            dep_on.setdefault(node.path, set())
            dep_by.setdefault(node.path, set())

        for mod in report.modules:
            path = mod.path
            # Try exact match first, then suffix match (Hy3 might use relative paths)
            deps_on = dep_on.get(path)
            if deps_on is None:
                # Search by suffix match
                for k, v in dep_on.items():
                    if k.endswith(path) or path.endswith(k):
                        deps_on = v
                        break
            if deps_on is None:
                deps_on = set()

            deps_by = dep_by.get(path)
            if deps_by is None:
                for k, v in dep_by.items():
                    if k.endswith(path) or path.endswith(k):
                        deps_by = v
                        break
            if deps_by is None:
                deps_by = set()

            mod.depends_on = sorted(deps_on)
            mod.depended_by = sorted(deps_by)

    @staticmethod
    async def _notify(
        callback: ProgressCallback | None,
        phase: JobPhase,
        pct: int,
        message: str,
        data: Any = None,
    ) -> None:
        if callback:
            if asyncio.iscoroutinefunction(callback):
                await callback(phase, pct, message, data)
            else:
                callback(phase, pct, message, data)
