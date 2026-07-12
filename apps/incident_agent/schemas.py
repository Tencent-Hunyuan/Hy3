from __future__ import annotations

from pydantic import BaseModel


class DemoResponse(BaseModel):
    id: str
    title: str
    summary: str
    task: str


class StatusResponse(BaseModel):
    ready: bool
    model: str
    endpoint: str
