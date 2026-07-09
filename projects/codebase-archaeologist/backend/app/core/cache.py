"""
Analysis Cache — commit-hash-based caching for analysis results.

Each completed analysis is stored as:
  ~/.archaeologist/cache/{repo_name}/{commit_hash[:12]}.json

When a new analysis is requested, we check if the same commit has been
analyzed before.  If so, return the cached result immediately.
If the commit changed, run a full re-analysis and update the cache.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models import ArchitectureReport

logger = logging.getLogger(__name__)


class AnalysisCache:
    """File-based analysis cache keyed by repo name + commit hash."""

    def __init__(self, base_dir: str | None = None):
        import app.config
        self._base = Path(base_dir or app.config.get_settings().temp_dir).parent / "cache"
        self._base.mkdir(parents=True, exist_ok=True)

    # ── Public API ──────────────────────────────────────────────

    def lookup(self, repo_url: str, commit_hash: str) -> ArchitectureReport | None:
        """Return cached report for this repo+commit, or None."""
        path = self._cache_path(repo_url, commit_hash)
        if not path.exists():
            logger.debug("Cache miss: %s (%s)", repo_url, commit_hash[:12])
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            report = ArchitectureReport(**data["report"])
            logger.info(
                "Cache hit: %s (%s) — saved %s, analyzed at %s",
                repo_url,
                commit_hash[:12],
                data.get("cost_summary", "N/A"),
                data.get("cached_at", "unknown"),
            )
            return report
        except Exception as e:
            logger.warning("Corrupted cache entry for %s: %s", repo_url, e)
            return None

    def lookup_by_url(self, repo_url: str) -> tuple[ArchitectureReport | None, str]:
        """Return the *latest* cached report for any commit of this repo, plus its commit hash.

        Use this to serve instant results without cloning — commit may be stale
        vs remote HEAD, but the user gets an immediate result and can re-analyze
        if they want the latest commit.
        """
        repo_dir = self._repo_dir(repo_url)
        if not repo_dir.exists():
            return None, ""

        # Pick the newest cache entry by file modification time
        entries = sorted(
            repo_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not entries:
            return None, ""

        # Try entries newest-first until one deserialises successfully
        for entry in entries:
            try:
                data = json.loads(entry.read_text(encoding="utf-8"))
                report = ArchitectureReport(**data["report"])
                commit = data.get("commit_hash", entry.stem)
                logger.info(
                    "Cache hit (by URL): %s (%s) — saved %s, analyzed at %s",
                    repo_url,
                    commit[:12],
                    data.get("cost_summary", "N/A"),
                    data.get("cached_at", "unknown"),
                )
                return report, commit
            except Exception as e:
                logger.warning("Corrupted cache entry %s: %s", entry, e)
                continue

        return None, ""

    def store(
        self,
        repo_url: str,
        commit_hash: str,
        report: ArchitectureReport,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Persist an analysis result to the cache."""
        path = self._cache_path(repo_url, commit_hash)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload: dict[str, Any] = {
            "repo_url": repo_url,
            "commit_hash": commit_hash,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "report": report.model_dump(),
            **(metadata or {}),
        }

        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        logger.info("Cached analysis: %s (%s) → %s", repo_url, commit_hash[:12], path)
        return path

    def invalidate(self, repo_url: str, commit_hash: str | None = None) -> int:
        """Remove cached entries. If commit_hash is None, remove all for this repo."""
        count = 0
        if commit_hash:
            p = self._cache_path(repo_url, commit_hash)
            if p.exists():
                p.unlink()
                count = 1
        else:
            repo_dir = self._repo_dir(repo_url)
            if repo_dir.exists():
                for f in repo_dir.glob("*.json"):
                    f.unlink()
                    count += 1
        return count

    def list_entries(self) -> list[dict[str, str]]:
        """List all cached analyses for inspection."""
        entries: list[dict[str, str]] = []
        for repo_dir in self._base.iterdir():
            if not repo_dir.is_dir():
                continue
            for entry in repo_dir.glob("*.json"):
                entries.append({
                    "repo": repo_dir.name,
                    "commit": entry.stem,
                    "cached_at": datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc).isoformat(),
                })
        return entries

    # ── Internals ───────────────────────────────────────────────

    def _repo_dir(self, repo_url: str) -> Path:
        slug = self._slug(repo_url)
        return self._base / slug

    def _cache_path(self, repo_url: str, commit_hash: str) -> Path:
        return self._repo_dir(repo_url) / f"{commit_hash[:12]}.json"

    @staticmethod
    def _slug(repo_url: str) -> str:
        """Generate a safe directory name from a repo URL."""
        clean = repo_url.rstrip("/").replace("https://", "").replace("http://", "")
        clean = clean.replace("github.com/", "").replace("/", "-")
        # Sanitize to safe chars only
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in clean)
        return safe[:64]  # trim to reasonable length


# Singleton
_cache: AnalysisCache | None = None


def get_cache() -> AnalysisCache:
    global _cache
    if _cache is None:
        _cache = AnalysisCache()
    return _cache
