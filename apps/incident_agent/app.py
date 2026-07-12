from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from hy3_code_review_mcp.config import Hy3Settings, load_default_dotenv

from .agent import (
    AgentChatClient,
    AgentConfigurationError,
    _settings_ready,
    get_agent_client,
    investigate,
)
from .demos import DEMOS, get_demo
from .schemas import DemoResponse, StatusResponse
from .workspace import MAX_FILE_BYTES, WorkspaceError, incident_workspace, validate_files


app = FastAPI(
    title="Hy3 Incident Agent",
    description="Investigate trusted engineering incident files with Hy3 and bounded tools.",
    version="0.1.0",
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_configured_agent_client() -> AgentChatClient:
    try:
        return get_agent_client()
    except AgentConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _settings() -> Hy3Settings:
    load_default_dotenv()
    return Hy3Settings.from_env()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status", response_model=StatusResponse)
def status() -> StatusResponse:
    settings = _settings()
    return StatusResponse(
        ready=_settings_ready(settings),
        model=settings.model,
        endpoint=urlparse(settings.base_url).hostname or "not-configured",
    )


@app.get("/api/demos", response_model=list[DemoResponse])
def demos() -> list[DemoResponse]:
    return [
        DemoResponse(
            id=demo.id,
            title=demo.title,
            summary=demo.summary,
            task=demo.task,
        )
        for demo in DEMOS
    ]


def event_stream(
    task: str,
    raw_files: Sequence[tuple[str, bytes]],
    client: AgentChatClient,
) -> Iterator[str]:
    with incident_workspace(raw_files) as root:
        for event in investigate(task, root, client):
            yield json.dumps(event, ensure_ascii=False) + "\n"


@app.post("/api/investigate")
async def investigate_endpoint(
    task: Annotated[str, Form()],
    client: Annotated[AgentChatClient, Depends(get_configured_agent_client)],
    demo_id: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile], File()] = [],
) -> StreamingResponse:
    normalized_task = task.strip()
    if not normalized_task:
        raise HTTPException(status_code=422, detail="Incident task must not be blank.")
    if len(normalized_task) > 2_000:
        raise HTTPException(
            status_code=422,
            detail="Incident task must be at most 2,000 characters.",
        )
    if demo_id and files:
        raise HTTPException(
            status_code=422,
            detail="Choose a demo or upload files, not both.",
        )

    if demo_id:
        try:
            demo = get_demo(demo_id)
        except KeyError as exc:
            raise HTTPException(status_code=422, detail=str(exc.args[0])) from exc
        raw_files = [
            (name, content.encode("utf-8"))
            for name, content in demo.files.items()
        ]
    else:
        raw_files = []
        for upload in files:
            content = await upload.read(MAX_FILE_BYTES + 1)
            raw_files.append((upload.filename or "", content))

    try:
        validate_files(raw_files)
    except WorkspaceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return StreamingResponse(
        event_stream(normalized_task, raw_files, client),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
