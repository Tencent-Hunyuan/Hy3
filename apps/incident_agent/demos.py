from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class DemoIncident:
    id: str
    title: str
    summary: str
    task: str
    files: Mapping[str, str]


RETRY_DEMO = DemoIncident(
    id="retry-regression",
    title="Retry budget regression",
    summary="A client makes one more request than its configured retry budget.",
    task=(
        "Investigate why the retry regression test fails. Identify the root cause, "
        "cite exact evidence, and propose the smallest safe fix and verification plan."
    ),
    files={
        "client.py": """from __future__ import annotations

from collections.abc import Callable


def fetch_with_retries(transport: Callable[[], str], retries: int = 3) -> str:
    last_error: TimeoutError | None = None
    for _attempt in range(retries + 1):
        try:
            return transport()
        except TimeoutError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error
""",
        "test_client.py": """import pytest

from client import fetch_with_retries


def test_retry_budget_is_total_attempts():
    calls = 0

    def timeout():
        nonlocal calls
        calls += 1
        raise TimeoutError("gateway timeout")

    with pytest.raises(TimeoutError):
        fetch_with_retries(timeout, retries=3)

    assert calls == 3
""",
        "incident.log": """2026-07-12T09:12:03Z WARN catalog request timed out attempt=1
2026-07-12T09:12:06Z WARN catalog request timed out attempt=2
2026-07-12T09:12:09Z WARN catalog request timed out attempt=3
2026-07-12T09:12:12Z WARN catalog request timed out attempt=4
2026-07-12T09:12:12Z ERROR retry budget exceeded configured_retries=3
""",
    },
)


WORKER_DEMO = DemoIncident(
    id="worker-startup",
    title="Worker startup failure",
    summary="A deployment and configuration loader disagree on an environment key.",
    task=(
        "Investigate why the worker fails during startup. Compare the logs, loader, "
        "deployment configuration, and environment documentation. Provide a grounded fix."
    ),
    files={
        "config.py": """from __future__ import annotations

import os


def load_worker_config() -> dict[str, str]:
    return {
        "queue": os.environ["WORKER_QUEUE"],
        "region": os.getenv("WORKER_REGION", "ap-shanghai"),
    }
""",
        "deployment.toml": """[worker.environment]
WORKER_QUEUE_NAME = "critical-jobs"
WORKER_REGION = "ap-shanghai"
""",
        "environment.txt": """Required variables
WORKER_QUEUE_NAME: queue consumed by the worker
WORKER_REGION: deployment region (optional)
""",
        "startup.log": """2026-07-12T10:04:31Z INFO starting worker version=2.4.1
2026-07-12T10:04:31Z ERROR configuration failed
Traceback (most recent call last):
  File "config.py", line 8, in load_worker_config
    "queue": os.environ["WORKER_QUEUE"],
KeyError: 'WORKER_QUEUE'
""",
    },
)


DEMOS = (RETRY_DEMO, WORKER_DEMO)


def get_demo(demo_id: str) -> DemoIncident:
    for demo in DEMOS:
        if demo.id == demo_id:
            return demo
    raise KeyError(f"Unknown demo: {demo_id}")
