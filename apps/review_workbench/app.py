from __future__ import annotations

from dataclasses import asdict
from time import perf_counter
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from openai import APITimeoutError

from hy3_code_review_mcp.config import Hy3Settings, load_default_dotenv
from hy3_code_review_mcp.hy3_client import Hy3Client
from hy3_code_review_mcp.review import (
    review_patch_with_client,
    suggest_tests_with_client,
)

from .examples import EXAMPLES
from .schemas import (
    DemoExampleResponse,
    Hy3Response,
    ReviewPayload,
    StatusResponse,
    TestPlanPayload,
)


app = FastAPI(
    title="Hy3 Review Workbench",
    description="Review code changes and generate test plans with Hy3.",
    version="0.1.0",
)


def _settings() -> Hy3Settings:
    load_default_dotenv()
    return Hy3Settings.from_env()


def _is_ready(settings: Hy3Settings) -> bool:
    hostname = (urlparse(settings.base_url).hostname or "").lower()
    is_local = hostname in {"localhost", "127.0.0.1", "::1"}
    has_key = bool(settings.api_key and settings.api_key != "EMPTY")
    return bool(settings.base_url and settings.model and (is_local or has_key))


def get_hy3_client() -> Hy3Client:
    settings = _settings()
    if not _is_ready(settings):
        raise HTTPException(
            status_code=503,
            detail="Hy3 API is not configured. Add credentials to .env and retry.",
        )
    return Hy3Client(settings)


def _duration_metadata(metadata: dict[str, object], started: float) -> dict[str, object]:
    return {
        **metadata,
        "duration_ms": max(0, round((perf_counter() - started) * 1_000)),
    }


def _upstream_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (TimeoutError, APITimeoutError)):
        return HTTPException(status_code=504, detail="Hy3 request timed out. Try again.")
    return HTTPException(
        status_code=502,
        detail="Hy3 request failed. Check the endpoint and try again.",
    )


@app.get("/api/status", response_model=StatusResponse)
def status() -> StatusResponse:
    settings = _settings()
    endpoint = urlparse(settings.base_url).hostname or "not-configured"
    return StatusResponse(
        ready=_is_ready(settings),
        model=settings.model,
        endpoint=endpoint,
    )


@app.get("/api/examples", response_model=list[DemoExampleResponse])
def examples() -> list[dict[str, str]]:
    return [asdict(example) for example in EXAMPLES]


@app.post("/api/review", response_model=Hy3Response)
async def review(
    payload: ReviewPayload,
    client: Hy3Client = Depends(get_hy3_client),
) -> Hy3Response:
    started = perf_counter()
    try:
        result = await run_in_threadpool(
            review_patch_with_client,
            payload.patch_text,
            client,
            payload.language,
            payload.focus,
            payload.context,
        )
    except Exception as exc:
        raise _upstream_error(exc) from exc

    return Hy3Response(
        content=result["review"],
        metadata=_duration_metadata(result["metadata"], started),
    )


@app.post("/api/tests", response_model=Hy3Response)
async def test_plan(
    payload: TestPlanPayload,
    client: Hy3Client = Depends(get_hy3_client),
) -> Hy3Response:
    started = perf_counter()
    try:
        result = await run_in_threadpool(
            suggest_tests_with_client,
            payload.diff_text,
            client,
            payload.test_framework,
            payload.risk_level,
        )
    except Exception as exc:
        raise _upstream_error(exc) from exc

    return Hy3Response(
        content=result["test_suggestions"],
        metadata=_duration_metadata(result["metadata"], started),
    )
