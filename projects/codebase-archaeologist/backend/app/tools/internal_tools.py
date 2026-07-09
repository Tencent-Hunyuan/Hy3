"""
Internal tool implementations — direct Python function calls.

These tools are registered in the ToolRegistry and callable by Hy3
through Function Calling during Phase 2.5 (Planning) and Phase 3 (ReAct).

Each tool is defined as:
  1. An async handler function
  2. A JSON Schema for its parameters
  3. A registration call
"""

from __future__ import annotations

import os
import re
import ast as py_ast
import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Any

import git
import networkx as nx

from app.models import DepGraph, DepNode, DepEdge, CycleInfo, FileInfo, FileManifest, FileTag

# ═══════════════════════════════════════════════════════════════
# Schema definitions (used for registration)
# ═══════════════════════════════════════════════════════════════

GIT_CLONE_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "GitHub repository URL"},
        "branch": {"type": "string", "description": "Branch name, default 'main'"},
    },
    "required": ["url"],
}

FILE_TREE_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Root directory path"},
        "max_depth": {"type": "integer", "description": "Max directory depth, default 5"},
        "exclude": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Patterns to exclude",
        },
    },
    "required": ["path"],
}

FILE_READ_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Absolute file path"},
    },
    "required": ["path"],
}

GREP_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Root directory to search in"},
        "pattern": {"type": "string", "description": "Regex pattern to search for"},
        "glob": {"type": "string", "description": "File glob filter, e.g. '*.py'"},
    },
    "required": ["path", "pattern"],
}

AST_PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Absolute file path"},
    },
    "required": ["path"],
}

DEP_GRAPH_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "enum": ["dependents_of", "dependencies_of", "top_modules", "cycles", "orphans"],
            "description": "Graph query type",
        },
        "node": {"type": "string", "description": "File path (for dependents_of / dependencies_of)"},
    },
    "required": ["query"],
}

WEB_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query string"},
        "max_results": {"type": "integer", "description": "Max results, default 5"},
    },
    "required": ["query"],
}


# ═══════════════════════════════════════════════════════════════
# Tool implementations
# ═══════════════════════════════════════════════════════════════

# ── git_clone ─────────────────────────────────────────────────

_CLONE_TIMEOUT = 120  # seconds — max time to wait for git clone


def _clone_sync(url: str, dest: str, branch: str = "") -> git.Repo:
    """Synchronous clone — disables HTTP/2 to avoid libcurl+GitHub framing errors."""
    # Force HTTP/1.1: GitHub + libcurl HTTP/2 often fails with
    # "Error in the HTTP2 framing layer" on macOS.
    os.environ.setdefault("GIT_HTTP_VERSION", "1.1")

    clone_kwargs: dict[str, Any] = {
        "depth": 1,
        "single_branch": True,
    }
    if branch:
        clone_kwargs["branch"] = branch
        return git.Repo.clone_from(url, dest, **clone_kwargs)

    from git.exc import GitCommandError
    for try_branch in ("main", "master"):
        try:
            clone_kwargs["branch"] = try_branch
            return git.Repo.clone_from(url, dest, **clone_kwargs)
        except GitCommandError:
            shutil.rmtree(dest, ignore_errors=True)
            continue
    # Last resort: let git auto-detect HEAD
    return git.Repo.clone_from(url, dest, depth=1)


async def git_clone(url: str, branch: str = "") -> dict[str, Any]:
    """Clone a GitHub repository to a temporary directory (non-blocking, with timeout)."""
    dest = tempfile.mkdtemp(prefix="archaeologist_")
    try:
        loop = asyncio.get_running_loop()
        task = loop.run_in_executor(None, _clone_sync, url, dest, branch)
        repo = await asyncio.wait_for(task, timeout=_CLONE_TIMEOUT)
        return {
            "local_path": dest,
            "branch": branch,
            "commit": repo.head.commit.hexsha,
            "clone_time_s": 0,
        }
    except asyncio.TimeoutError:
        return {"error": f"Clone timed out after {_CLONE_TIMEOUT}s. Check the repo URL or network."}
    except git.GitCommandError as e:
        return {"error": f"Clone failed: {e}"}
    except Exception as e:
        return {"error": f"Clone failed ({type(e).__name__}): {e}"}


# ── file_tree ────────────────────────────────────────────────

async def file_tree(
    path: str,
    max_depth: int = 5,
    exclude: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a directory tree."""
    exclude = exclude or ["__pycache__", "node_modules", ".git", "venv", ".venv", ".idea"]
    root = Path(path)
    if not root.exists():
        return {"error": f"Path does not exist: {path}"}

    tree: dict[str, Any] = {"name": root.name, "type": "directory", "children": []}
    file_count = 0

    def _walk(current: Path, node: dict[str, Any], depth: int):
        nonlocal file_count
        if depth > max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda e: (e.is_file(), e.name))
        except PermissionError:
            return

        for entry in entries:
            if entry.name in exclude or entry.name.startswith("."):
                continue
            if entry.is_dir():
                child = {"name": entry.name, "type": "directory", "children": []}
                node["children"].append(child)
                _walk(entry, child, depth + 1)
            elif entry.is_file():
                child = {"name": entry.name, "type": "file"}
                node["children"].append(child)
                file_count += 1

    _walk(root, tree, 1)
    return {"tree": tree, "file_count": file_count}


# ── file_read ────────────────────────────────────────────────

async def file_read(path: str) -> dict[str, Any]:
    """Read a file's content with metadata."""
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if p.stat().st_size > 5 * 1024 * 1024:
        return {"error": f"File too large (>5MB): {path}"}

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"error": f"Read failed: {e}"}

    lines = content.split("\n")
    ext = p.suffix.lstrip(".")
    language_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "jsx": "javascript", "tsx": "typescript", "go": "go",
        "java": "java", "rs": "rust", "cpp": "cpp", "c": "c",
        "h": "c", "hpp": "cpp", "rb": "ruby", "php": "php",
        "swift": "swift", "kt": "kotlin", "scala": "scala",
    }

    return {
        "content": content,
        "lines": len(lines),
        "language": language_map.get(ext, ext),
        "size_bytes": p.stat().st_size,
    }


# ── grep_search ──────────────────────────────────────────────

async def grep_search(path: str, pattern: str, glob: str = "*") -> dict[str, Any]:
    """Search a repository for a regex pattern."""
    root = Path(path)
    matches: list[dict[str, Any]] = []

    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return {"error": f"Invalid regex: {e}"}

    glob_exts = None
    if glob and glob != "*":
        glob_exts = set(glob.replace("*", "").split())

    for file_path in root.rglob("**/*"):
        if file_path.is_dir():
            continue
        if any(part.startswith(".") for part in file_path.parts):
            continue
        if any(skip in file_path.parts for skip in ["node_modules", "__pycache__", ".git", "venv"]):
            continue
        if glob_exts and file_path.suffix not in glob_exts:
            continue
        if file_path.stat().st_size > 5 * 1024 * 1024:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for lineno, line in enumerate(content.split("\n"), 1):
            if compiled.search(line):
                matches.append({
                    "file": str(file_path.relative_to(root)),
                    "line": lineno,
                    "content": line.strip()[:200],
                })
                if len(matches) >= 200:
                    break
        if len(matches) >= 200:
            break

    return {"matches": matches, "count": len(matches), "truncated": len(matches) >= 200}


# ── ast_parse ────────────────────────────────────────────────

async def ast_parse(path: str) -> dict[str, Any]:
    """Parse a Python file's AST to extract imports, functions, and classes."""
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if p.suffix != ".py":
        return {"error": "AST parse only supports Python files"}

    try:
        source = p.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"Read failed: {e}"}

    try:
        tree = py_ast.parse(source)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}

    imports: list[str] = []
    functions: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []

    for node in py_ast.walk(tree):
        if isinstance(node, py_ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, py_ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)
        elif isinstance(node, py_ast.FunctionDef):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "decorators": [
                    py_ast.unparse(d) for d in node.decorator_list
                ] if node.decorator_list else [],
            })
        elif isinstance(node, py_ast.ClassDef):
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "bases": [py_ast.unparse(b) for b in node.bases],
            })

    return {
        "imports": imports,
        "functions": functions,
        "classes": classes,
    }


# ── dep_graph_query ──────────────────────────────────────────

# Module-level reference to the active DepGraph (set after Phase 2)
_active_dep_graph: DepGraph | None = None
_active_graph_obj: nx.DiGraph | None = None


def set_active_dep_graph(dep_graph: DepGraph, graph_obj: nx.DiGraph) -> None:
    """Store the active dependency graph for querying."""
    global _active_dep_graph, _active_graph_obj
    _active_dep_graph = dep_graph
    _active_graph_obj = graph_obj


async def dep_graph_query(query: str, node: str = "") -> dict[str, Any]:
    """Query the active dependency graph."""
    if _active_dep_graph is None:
        return {"error": "No dependency graph has been built yet"}

    if query == "dependents_of":
        if not node:
            return {"error": "Node path required for dependents_of"}
        if _active_graph_obj:
            deps = list(_active_graph_obj.predecessors(node))
        else:
            deps = [e.source for e in _active_dep_graph.edges if e.target == node]
        return {"dependents": deps, "count": len(deps)}

    if query == "dependencies_of":
        if not node:
            return {"error": "Node path required for dependencies_of"}
        if _active_graph_obj:
            deps = list(_active_graph_obj.successors(node))
        else:
            deps = [e.target for e in _active_dep_graph.edges if e.source == node]
        return {"dependencies": deps, "count": len(deps)}

    if query == "top_modules":
        top = sorted(_active_dep_graph.core_modules, key=lambda n: n.pagerank, reverse=True)[:20]
        return {
            "modules": [
                {"path": m.path, "pagerank": round(m.pagerank, 4), "in_degree": m.in_degree}
                for m in top
            ]
        }

    if query == "cycles":
        return {"cycles": [c.model_dump() for c in _active_dep_graph.cycles]}

    if query == "orphans":
        return {"orphans": _active_dep_graph.orphans}

    return {"error": f"Unknown query type: {query}"}
