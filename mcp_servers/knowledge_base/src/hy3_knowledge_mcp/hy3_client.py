"""OpenAI-compatible Hy3 异步客户端。"""

from __future__ import annotations

import json
from typing import Any, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from .config import Settings
from .errors import (
    Hy3AuthenticationError,
    Hy3RateLimitError,
    Hy3ResponseError,
    Hy3TimeoutError,
    KnowledgeBaseError,
)
from .models import EndpointProfile, Hy3AnswerPayload, Hy3SummaryPayload, ReasoningEffort

PayloadT = TypeVar("PayloadT", bound=BaseModel)
UNSUPPORTED_STRUCTURED_SCHEMA_KEYWORDS = frozenset({"minLength", "maxLength"})


def _sanitize_structured_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """递归移除端点不支持的 schema 关键词, 且不修改输入。"""

    def sanitize_value(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: sanitize_value(item)
                for key, item in value.items()
                if key not in UNSUPPORTED_STRUCTURED_SCHEMA_KEYWORDS
            }
        if isinstance(value, list):
            return [sanitize_value(item) for item in value]
        return value

    return sanitize_value(schema)


def _outbound_schema(model: type[BaseModel]) -> dict[str, Any]:
    """返回与真实结构化请求完全相同的端点兼容 Schema。"""
    return _sanitize_structured_schema(model.model_json_schema())


def _outbound_schema_chars(model: type[BaseModel]) -> int:
    """返回真实出站 Schema 的紧凑 JSON 字符预算。"""
    return len(json.dumps(_outbound_schema(model), ensure_ascii=False, separators=(",", ":")))


def answer_schema_chars() -> int:
    """返回回答请求真实出站 Schema 的字符预算。"""
    return _outbound_schema_chars(Hy3AnswerPayload)


def summary_schema_chars() -> int:
    """返回总结请求真实出站 Schema 的字符预算。"""
    return _outbound_schema_chars(Hy3SummaryPayload)


def _reasoning_body(
    profile: EndpointProfile,
    effort: ReasoningEffort,
) -> dict[str, object] | None:
    """生成端点明确支持的推理控制字段。"""
    if profile is EndpointProfile.OPENROUTER:
        return {"reasoning": {"effort": effort.value}}
    if profile is EndpointProfile.LOCAL:
        local_effort = "no_think" if effort is ReasoningEffort.NONE else effort.value
        return {"chat_template_kwargs": {"reasoning_effort": local_effort}}
    return None


def _status_error(status_code: int) -> Hy3ResponseError:
    """仅保留状态码, 避免响应正文或端点 URL 进入领域异常。"""
    if status_code == 400:
        return Hy3ResponseError(
            "Hy3 endpoint rejected structured request; verify model, json_schema, "
            "and endpoint configuration"
        )
    return Hy3ResponseError(f"Hy3 endpoint returned HTTP {status_code}")


class Hy3Client:
    """复用单个 AsyncOpenAI 实例调用 Hy3 结构化输出。"""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        if settings.api_key is None and settings.endpoint_profile is not EndpointProfile.LOCAL:
            raise Hy3AuthenticationError("HY3_API_KEY is required for remote Hy3 endpoint profiles")

        self.settings = settings
        self._closed = False
        if client is not None:
            self.client = client
            return

        try:
            created_client = AsyncOpenAI(
                api_key=(
                    settings.api_key.get_secret_value() if settings.api_key is not None else "EMPTY"
                ),
                base_url=settings.base_url,
                timeout=settings.timeout_seconds,
                max_retries=settings.max_retries,
            )
        except Exception:
            initialization_error = Hy3ResponseError("Failed to initialize Hy3 client")
        else:
            self.client = created_client
            return

        raise initialization_error from None

    async def close(self) -> None:
        """关闭底层客户端; 成功关闭后重复调用不产生副作用。"""
        if self._closed:
            return
        await self.client.close()
        self._closed = True

    async def _create_completion(self, request: dict[str, object]) -> object:
        """调用 SDK 并将其异常映射为不携带敏感上下文的领域异常。"""
        mapped_error: KnowledgeBaseError | None = None
        try:
            return await self.client.chat.completions.create(**request)
        except AuthenticationError:
            mapped_error = Hy3AuthenticationError("Hy3 authentication failed")
        except RateLimitError:
            mapped_error = Hy3RateLimitError("Hy3 rate limit exceeded; retry later")
        except (APITimeoutError, APIConnectionError):
            mapped_error = Hy3TimeoutError("Hy3 request timed out or could not connect")
        except APIStatusError as exc:
            mapped_error = _status_error(exc.status_code)

        raise mapped_error from None

    @staticmethod
    def _parse_payload(response: object, schema: type[PayloadT]) -> PayloadT:
        """只接受 chat completions 的字符串 content 并严格校验 JSON。"""
        invalid_error: Hy3ResponseError | None = None
        try:
            content = response.choices[0].message.content  # type: ignore[attr-defined]
        except (AttributeError, IndexError, KeyError, TypeError):
            invalid_error = Hy3ResponseError("Hy3 returned invalid structured output")
        else:
            if content is None or content == "":
                raise Hy3ResponseError("Hy3 returned an empty structured response")
            if not isinstance(content, str):
                raise Hy3ResponseError("Hy3 returned invalid structured output")
            try:
                decoded = json.loads(content)
                return schema.model_validate(decoded)
            except (json.JSONDecodeError, ValidationError, TypeError):
                invalid_error = Hy3ResponseError("Hy3 returned invalid structured output")

        raise invalid_error from None

    async def _structured(
        self,
        messages: list[dict[str, str]],
        schema: type[PayloadT],
        *,
        schema_name: str,
        reasoning_effort: ReasoningEffort,
    ) -> PayloadT:
        """发送严格 JSON Schema 请求并返回已验证载荷。"""
        request: dict[str, object] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": 0.2,
            "top_p": 1.0,
            "max_completion_tokens": self.settings.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": _outbound_schema(schema),
                },
            },
        }
        reasoning_body = _reasoning_body(self.settings.endpoint_profile, reasoning_effort)
        if reasoning_body is not None:
            request["extra_body"] = reasoning_body

        for attempt in range(2):
            response = await self._create_completion(request)
            try:
                return self._parse_payload(response, schema)
            except Hy3ResponseError:
                if attempt == 1:
                    raise

        raise AssertionError("unreachable")

    async def answer(
        self,
        messages: list[dict[str, str]],
        *,
        reasoning_effort: ReasoningEffort,
    ) -> Hy3AnswerPayload:
        """生成基于证据的结构化回答。"""
        return await self._structured(
            messages,
            Hy3AnswerPayload,
            schema_name="hy3_kb_answer",
            reasoning_effort=reasoning_effort,
        )

    async def summarize(
        self,
        messages: list[dict[str, str]],
        *,
        reasoning_effort: ReasoningEffort,
    ) -> Hy3SummaryPayload:
        """生成基于证据的结构化总结。"""
        return await self._structured(
            messages,
            Hy3SummaryPayload,
            schema_name="hy3_kb_summary",
            reasoning_effort=reasoning_effort,
        )
