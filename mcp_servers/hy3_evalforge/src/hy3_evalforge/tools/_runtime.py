"""Safe construction and error rendering for tool workflow invocations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.providers.hy3 import Hy3Provider
from hy3_evalforge.settings import Settings


def workflow_dependencies() -> tuple[Settings, ArtifactStore, Hy3Provider]:
    """Build dependencies only on invocation, so discovery never needs an API key."""
    settings = Settings.from_environment()
    store = ArtifactStore(settings.allowed_root, max_file_bytes=settings.max_file_bytes)
    return settings, store, Hy3Provider(settings)


async def safe_tool_call(operation: Callable[[], Awaitable[Any]]) -> dict[str, object]:
    """Return safe structured failures instead of leaking framework or provider internals."""
    try:
        result = await operation()
        return result.model_dump(mode="json")
    except EvalForgeError as exc:
        return exc.to_payload()
    except Exception:
        return EvalForgeError(
            ErrorCode.PROVIDER_ERROR, "EvalForge could not complete the requested workflow."
        ).to_payload()
