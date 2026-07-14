"""Application service that connects diff collection, prompts, and Hy3."""

from __future__ import annotations

from .git_service import DiffSource, GitService
from .hy3_client import Analyzer
from .prompts import SYSTEM_PROMPT, build_user_prompt


class ReviewService:
    """Execute the four read-only code review workflows."""

    def __init__(self, git_service: GitService, analyzer: Analyzer) -> None:
        self.git_service = git_service
        self.analyzer = analyzer

    async def run(
        self,
        *,
        task: str,
        repository_path: str = ".",
        source: DiffSource = "working_tree",
        base_ref: str | None = None,
        target_ref: str | None = None,
        provided_diff: str | None = None,
        focus: str = "all",
        language: str = "Chinese",
        test_framework: str | None = None,
        reasoning_effort: str | None = None,
    ) -> str:
        """Collect context and ask Hy3 to perform a single scenario-specific task."""
        payload = self.git_service.collect_diff(
            repository_path=repository_path,
            source=source,
            base_ref=base_ref,
            target_ref=target_ref,
            provided_diff=provided_diff,
        )
        prompt = build_user_prompt(
            task=task,
            payload=payload,
            focus=focus,
            language=language,
            test_framework=test_framework,
        )
        return await self.analyzer.analyze(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            reasoning_effort=reasoning_effort,
        )
