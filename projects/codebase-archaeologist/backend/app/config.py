"""
Central configuration — loaded from env / .env via Pydantic Settings.

All tunable knobs live here so that prompt-engineering experiments
and cost tuning don't require code changes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        env_prefix="ARCHAEOLOGIST_",
        extra="ignore",
    )

    # ── Hy3 API ──────────────────────────────────────────────
    hy3_api_key: str = ""
    hy3_base_url: str = "https://tokenhub.tencentmaas.com/v1"
    hy3_model: str = "hy3"
    hy3_max_retries: int = 2
    hy3_request_timeout: int = 180  # seconds — per-request timeout

    # ── Prompt cache key (shared across all calls) ───────────
    prompt_cache_key: str = "archaeologist-v2"

    # ── Repository analysis ──────────────────────────────────
    max_repo_size_mb: int = 500
    max_file_size_mb: int = 5
    clone_depth: int = 1  # shallow clone
    temp_dir: str = str(Path.home() / ".archaeologist" / "repos")

    # ── Dependency graph ─────────────────────────────────────
    dep_graph_pagerank_alpha: float = 0.85
    dep_graph_max_cycle_length: int = 20

    # ── Batch analysis (Phase 3) ─────────────────────────────
    max_context_tokens: int = 120_000  # batch payload cap — keep total under Hy3's soft limit
    max_batch_output_tokens: int = 16_384
    max_react_rounds_per_batch: int = 5
    batch_summary_max_tokens: int = 2_000

    # ── Phase 3.5 consistency check ──────────────────────────
    consistency_check_max_tokens: int = 50_000  # all findings at once

    # ── Phase 4 synthesis ────────────────────────────────────
    synthesis_max_tokens: int = 16_384

    # ── Question answering ───────────────────────────────────
    qa_max_context_tokens: int = 16_000
    qa_retrieval_top_k: int = 15

    # ── Vector search (ChromaDB) ─────────────────────────────
    chroma_persist_dir: str = str(Path.home() / ".archaeologist" / "chroma")
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"

    # ── MCP tools ────────────────────────────────────────────
    mcp_enabled: bool = True
    tavily_api_key: str = ""

    # ── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Logging ──────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
