from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from replaylab.builtins import FixtureNotFoundError, FixtureStore, FixtureSummary
from replaylab.export import export_report_json, export_report_markdown
from replaylab.hy3 import Hy3Provider, Hy3ProviderError, Hy3Settings
from replaylab.imports import ImportRejectedError, parse_imported_task
from replaylab.providers import StaticProvider
from replaylab.resources import fixture_root as default_fixture_root
from replaylab.schemas import ReplayReport, TaskSpec
from replaylab.service import ProviderOutputError, ReplayLabService
from replaylab.validation import OutputValidationError


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    live_provider_configured: bool


class AnalyzeRequest(ApiModel):
    fixture_id: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    task: TaskSpec | None = None
    provider: Literal["fake", "hy3"] = "fake"

    @model_validator(mode="after")
    def require_one_input(self) -> AnalyzeRequest:
        if (self.fixture_id is None) == (self.task is None):
            raise ValueError("provide exactly one of fixture_id or task")
        return self


class ImportRequest(ApiModel):
    filename: Annotated[str, Field(min_length=1, max_length=120)]
    content_type: Annotated[str, Field(min_length=1, max_length=100)]
    content: Annotated[str, Field(min_length=1, max_length=128_000)]


class ExportPayload(ApiModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    json_export: str = Field(serialization_alias="json")
    markdown_export: str = Field(serialization_alias="markdown")


class AnalyzeResponse(ApiModel):
    report: ReplayReport
    exports: ExportPayload


def create_app(*, fixture_root: Path | None = None) -> FastAPI:
    root = fixture_root or default_fixture_root()
    fixture_store = FixtureStore(root)
    application = FastAPI(
        title="Hy3 轨迹复盘台 API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    @application.exception_handler(RequestValidationError)
    async def request_validation_error(
        _request: Request, _error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": "请求未通过校验"},
        )

    @application.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            live_provider_configured=bool(os.environ.get("HY3_API_KEY", "").strip())
        )

    @application.get("/api/fixtures", response_model=list[FixtureSummary])
    async def list_fixtures() -> list[FixtureSummary]:
        return fixture_store.list()

    @application.get("/api/fixtures/{fixture_id}", response_model=TaskSpec)
    async def get_fixture(fixture_id: str) -> TaskSpec:
        try:
            return fixture_store.load_task(fixture_id)
        except FixtureNotFoundError as error:
            raise HTTPException(status_code=404, detail="未找到内置轨迹") from error

    @application.post("/api/import", response_model=TaskSpec)
    async def import_task(request: ImportRequest) -> TaskSpec:
        try:
            return parse_imported_task(
                filename=request.filename,
                content_type=request.content_type,
                content=request.content,
            )
        except ImportRejectedError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @application.post("/api/analyze", response_model=AnalyzeResponse)
    async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
        try:
            task = (
                fixture_store.load_task(request.fixture_id)
                if request.fixture_id is not None
                else request.task
            )
            if task is None:
                raise AssertionError("validated analysis input is missing")
            if request.provider == "fake":
                if request.fixture_id is None:
                    raise HTTPException(
                        status_code=400,
                        detail="自定义导入需要使用在线 Hy3",
                    )
                provider_output = fixture_store.load_provider_output(request.fixture_id)
                report = await ReplayLabService(StaticProvider(provider_output)).analyze(task)
            else:
                settings = Hy3Settings.from_env()
                async with Hy3Provider(settings) as provider:
                    report = await ReplayLabService(provider).analyze(task)
        except FixtureNotFoundError as error:
            raise HTTPException(status_code=404, detail="未找到内置轨迹") from error
        except Hy3ProviderError as error:
            if str(error) == "Hy3 live provider is not configured":
                raise HTTPException(
                    status_code=503, detail="尚未配置在线 Hy3"
                ) from error
            if error.status_code == 429:
                retry_after = str(error.retry_after_seconds or 1)
                raise HTTPException(
                    status_code=429,
                    detail="Hy3 当前请求受限",
                    headers={"Retry-After": retry_after},
                ) from error
            raise HTTPException(status_code=502, detail="Hy3 分析请求失败") from error
        except (ProviderOutputError, OutputValidationError) as error:
            raise HTTPException(status_code=502, detail="分析结果未通过安全校验") from error
        return AnalyzeResponse(
            report=report,
            exports=ExportPayload(
                json_export=export_report_json(report),
                markdown_export=export_report_markdown(report),
            ),
        )

    return application


app = create_app()
