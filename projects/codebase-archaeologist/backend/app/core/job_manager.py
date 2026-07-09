"""
Job Manager — stateful job tracking with SSE progress streaming.

Each analysis job goes through the phase state machine:
  PENDING → INGESTING → GRAPHING → PLANNING → ANALYZING →
  CONSISTENCY_CHECK → SYNTHESIZING → GENERATING → DONE (or FAILED)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from typing import Any

from app.models import ArchitectureReport, JobPhase, JobStatus, PRImpactReport

logger = logging.getLogger(__name__)


class JobManager:
    """In-memory job tracker with SSE fan-out."""

    def __init__(self):
        self._jobs: dict[str, JobStatus] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._results: dict[str, ArchitectureReport | PRImpactReport] = {}
        self._token_usage: dict[str, dict[str, Any]] = {}  # job_id → usage dict

    def create_job(self) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid.uuid4())[:12]
        self._jobs[job_id] = JobStatus(job_id=job_id)
        logger.info("Created job: %s", job_id)
        return job_id

    def get_job(self, job_id: str) -> JobStatus | None:
        return self._jobs.get(job_id)

    def get_result(self, job_id: str) -> ArchitectureReport | PRImpactReport | None:
        return self._results.get(job_id)

    def update(
        self,
        job_id: str,
        phase: JobPhase,
        progress_pct: int,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Update job progress and broadcast to subscribers."""
        job = self._jobs.get(job_id)
        if not job:
            return

        job.phase = phase
        job.progress_pct = progress_pct
        job.message = message

        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

        # Broadcast SSE event
        event = job.model_dump_json()
        for queue in self._subscribers.get(job_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop event if subscriber is slow

    def complete(
        self,
        job_id: str,
        result: ArchitectureReport | PRImpactReport,
    ) -> None:
        """Mark job as done and store result."""
        self._results[job_id] = result
        self.update(job_id, JobPhase.DONE, 100, "Analysis complete", result=result)

    def set_token_usage(self, job_id: str, usage: dict[str, Any]) -> None:
        """Store token usage stats for a completed job."""
        self._token_usage[job_id] = usage

    def get_token_usage(self, job_id: str) -> dict[str, Any] | None:
        return self._token_usage.get(job_id)

    def fail(self, job_id: str, error: str) -> None:
        self.update(job_id, JobPhase.FAILED, 0, "Analysis failed", error=error)

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """Create an SSE subscription queue for a job.

        Returns an asyncio.Queue that receives JSON status events.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers[job_id].append(queue)

        # Send current state immediately
        job = self._jobs.get(job_id)
        if job:
            queue.put_nowait(job.model_dump_json())

        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        subs = self._subscribers.get(job_id, [])
        if queue in subs:
            subs.remove(queue)

    async def create_progress_callback(self, job_id: str):
        """Return an async progress callback bound to a job."""
        async def callback(phase: JobPhase, pct: int, message: str, data: Any = None):
            kwargs = {}
            if data is not None:
                if isinstance(data, dict):
                    kwargs = data
                else:
                    kwargs["result"] = data
            self.update(job_id, phase, pct, message, **kwargs)
        return callback


# Singleton
_job_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
