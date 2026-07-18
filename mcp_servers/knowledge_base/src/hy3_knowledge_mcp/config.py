"""知识库 MCP 服务的环境配置。"""

import json
import os
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from platformdirs import user_data_path
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    model_validator,
)

from .errors import ConfigurationError
from .models import EndpointProfile, Hy3AnswerPayload, Hy3SummaryPayload, ReasoningEffort


def _schema_chars(model: type[BaseModel]) -> int:
    """返回模型 JSON Schema 的紧凑序列化字符数。"""
    serialized = json.dumps(
        model.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return len(serialized)


def answer_schema_chars() -> int:
    """返回回答载荷 JSON Schema 的字符预算。"""
    return _schema_chars(Hy3AnswerPayload)


def summary_schema_chars() -> int:
    """返回总结载荷 JSON Schema 的字符预算。"""
    return _schema_chars(Hy3SummaryPayload)


def max_structured_schema_chars() -> int:
    """返回所有结构化响应中最大的 JSON Schema 字符预算。"""
    return max(answer_schema_chars(), summary_schema_chars())


class Settings(BaseModel):
    """经过严格验证且不可变的服务配置。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_key: SecretStr | None = None
    base_url: str = "http://127.0.0.1:8000/v1"
    model: str = "hy3"
    endpoint_profile: EndpointProfile = EndpointProfile.LOCAL
    reasoning_effort: ReasoningEffort = ReasoningEffort.HIGH
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    max_retries: int = Field(default=2, ge=0, le=5)
    max_output_tokens: int = Field(default=2048, ge=1, le=16384)
    allowed_root_paths: tuple[Path, ...]
    storage_dir: Path
    max_file_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    max_files_per_run: int = Field(default=500, ge=1, le=5000)
    max_total_bytes_per_run: int = Field(
        default=100 * 1024 * 1024,
        ge=1024,
        le=1024 * 1024 * 1024,
    )
    max_discovery_entries: int = Field(default=20000, ge=1, le=1_000_000)
    max_discovery_directories: int = Field(default=2000, ge=1, le=100_000)
    max_discovery_depth: int = Field(default=64, ge=1, le=256)
    max_pdf_pages: int = Field(default=500, ge=1, le=5000)
    chunk_chars: int = Field(default=3000, ge=500, le=20000)
    chunk_overlap_chars: int = Field(default=300, ge=0, le=5000)
    max_context_chars: int = Field(default=90000, ge=5000, le=500000)
    prompt_reserve_chars: int = Field(default=8000, ge=1000, le=100000)
    max_summary_requests: int = Field(default=16, ge=2, le=64)

    @model_validator(mode="after")
    def validate_cross_field_constraints(self) -> "Settings":
        """验证分块、上下文预算和本地端点的组合约束。"""
        if self.chunk_overlap_chars >= self.chunk_chars:
            raise ValueError("chunk overlap 必须小于 chunk chars")
        if self.chunk_overlap_chars * 2 > self.chunk_chars:
            raise ValueError("chunk overlap 不得超过 chunk chars 的一半")

        conservative_output = self.max_output_tokens * 8
        required_context = (
            self.chunk_chars
            + max_structured_schema_chars()
            + self.prompt_reserve_chars
            + conservative_output
        )
        if self.max_context_chars < required_context:
            raise ValueError("max context 无法容纳 chunk、schema、prompt reserve 和 output budget")

        try:
            parsed_url = urlparse(self.base_url)
            hostname = parsed_url.hostname
            port = parsed_url.port
        except ValueError:
            raise ValueError("base_url 必须是有效的 HTTP 或 HTTPS URL") from None

        if (
            parsed_url.scheme.lower() not in {"http", "https"}
            or hostname is None
            or parsed_url.username is not None
            or parsed_url.password is not None
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ValueError("base_url 必须是无用户凭据的有效 HTTP 或 HTTPS URL")

        if self.endpoint_profile is EndpointProfile.LOCAL and hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("local endpoint profile 必须使用 loopback 主机")
        return self

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        """从环境变量加载设置并避免在错误中暴露敏感值。"""
        if environ is None:
            load_dotenv(override=False)
            source: Mapping[str, str] = os.environ
        else:
            source = environ

        raw_roots = source.get("HY3_KB_ROOTS", "")
        root_values = tuple(part.strip() for part in raw_roots.split(os.pathsep) if part.strip())
        if not root_values:
            raise ConfigurationError("缺少必需配置 HY3_KB_ROOTS")

        raw_storage = source.get("HY3_KB_STORAGE_DIR", "").strip()
        storage_value = (
            Path(raw_storage)
            if raw_storage
            else user_data_path("hy3-knowledge-mcp", ensure_exists=False)
        )

        path_error = False
        try:
            candidate_roots = tuple(Path(value).resolve(strict=True) for value in root_values)
            resolved_storage = Path(storage_value).resolve(strict=False)
        except OSError:
            path_error = True
        else:
            storage_ancestor = resolved_storage
            while not storage_ancestor.exists() and storage_ancestor != storage_ancestor.parent:
                storage_ancestor = storage_ancestor.parent

            if any(not root.is_dir() for root in candidate_roots) or not storage_ancestor.is_dir():
                path_error = True
            else:
                unique_roots = []
                seen_roots = set()
                for root in candidate_roots:
                    normalized_root = os.path.normcase(str(root))
                    if normalized_root not in seen_roots:
                        seen_roots.add(normalized_root)
                        unique_roots.append(root)
                resolved_roots = tuple(unique_roots)

        if path_error:
            raise ConfigurationError("知识库路径配置无效")

        values: dict[str, object] = {
            "api_key": source.get("HY3_API_KEY") or None,
            "base_url": source.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
            "model": source.get("HY3_MODEL", "hy3"),
            "endpoint_profile": source.get("HY3_ENDPOINT_PROFILE", "local"),
            "reasoning_effort": source.get("HY3_REASONING_EFFORT", "high"),
            "timeout_seconds": source.get("HY3_TIMEOUT_SECONDS", "60"),
            "max_retries": source.get("HY3_MAX_RETRIES", "2"),
            "max_output_tokens": source.get("HY3_MAX_OUTPUT_TOKENS", "2048"),
            "allowed_root_paths": resolved_roots,
            "storage_dir": resolved_storage,
            "max_file_bytes": source.get("HY3_KB_MAX_FILE_BYTES", str(10 * 1024 * 1024)),
            "max_files_per_run": source.get("HY3_KB_MAX_FILES_PER_RUN", "500"),
            "max_total_bytes_per_run": source.get(
                "HY3_KB_MAX_TOTAL_BYTES_PER_RUN", str(100 * 1024 * 1024)
            ),
            "max_discovery_entries": source.get("HY3_KB_MAX_DISCOVERY_ENTRIES", "20000"),
            "max_discovery_directories": source.get("HY3_KB_MAX_DISCOVERY_DIRECTORIES", "2000"),
            "max_discovery_depth": source.get("HY3_KB_MAX_DISCOVERY_DEPTH", "64"),
            "max_pdf_pages": source.get("HY3_KB_MAX_PDF_PAGES", "500"),
            "chunk_chars": source.get("HY3_KB_CHUNK_CHARS", "3000"),
            "chunk_overlap_chars": source.get("HY3_KB_CHUNK_OVERLAP_CHARS", "300"),
            "max_context_chars": source.get("HY3_KB_MAX_CONTEXT_CHARS", "90000"),
            "prompt_reserve_chars": source.get("HY3_KB_PROMPT_RESERVE_CHARS", "8000"),
            "max_summary_requests": source.get("HY3_KB_MAX_SUMMARY_REQUESTS", "16"),
        }
        try:
            return cls.model_validate(values)
        except ValidationError as exc:
            messages = []
            for error in exc.errors(include_input=False, include_url=False):
                location = ".".join(str(part) for part in error["loc"])
                messages.append(f"{location}: {error['msg']}")
            error_message = "配置无效: " + "; ".join(messages)
        except ValueError:
            error_message = "配置无效"

        raise ConfigurationError(error_message)
