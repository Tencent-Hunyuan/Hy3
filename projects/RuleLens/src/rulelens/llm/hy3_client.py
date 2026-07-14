"""Hy3 客户端封装（OpenAI 兼容 Chat Completions）。

- 封装 SDK 初始化、超时、重试与模型参数；
- 提供 ``generate_text`` 与 ``generate_validated``；
- ``generate_validated`` 接收目标 Pydantic 类型，解析失败时最多发起一次 JSON 修复请求；
- 将 SDK 异常转换为项目自定义异常；
- 所有 API 差异集中在适配层（extra_body / reasoning 参数）。

测试使用 :class:`FakeHy3Client`，不调用真实 API。
"""

from __future__ import annotations

import time
from typing import Type, TypeVar

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from ..config import Settings
from ..exceptions import (
    Hy3AuthenticationError,
    Hy3RateLimitError,
    Hy3ResponseError,
    Hy3TimeoutError,
    SchemaValidationError,
)
from .json_parser import JsonParseError, extract_json_object
from .prompts import build_json_fix_prompt

T = TypeVar("T", bound=BaseModel)

# 可重试的瞬时异常类型
_RETRYABLE = (APITimeoutError, APIConnectionError, RateLimitError, APIError)


class Hy3ClientBase:
    """客户端接口，便于在测试中以 Fake 替换。"""

    def generate_text(self, system: str, user: str, *, reasoning_effort: str | None = None) -> str:
        raise NotImplementedError

    def generate_validated(
        self, system: str, user: str, target_type: Type[T], *, reasoning_effort: str | None = None
    ) -> T:
        raise NotImplementedError


class Hy3Client(Hy3ClientBase):
    def __init__(self, settings: Settings) -> None:
        settings.validate_required()
        self.settings = settings
        # 关闭 SDK 自带重试，改由本地 tenacity 风格循环控制。
        self.client = OpenAI(
            api_key=settings.hy3_api_key,
            base_url=settings.hy3_base_url,
            timeout=settings.hy3_timeout_seconds,
            max_retries=0,
        )

    # ------------------------------------------------------------------ #
    def _json_schema_response_format(self, target_type: Type[T]) -> dict:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": target_type.__name__,
                "schema": target_type.model_json_schema(),
            },
        }

    def _build_kwargs(
        self,
        system: str,
        user: str,
        reasoning_effort: str | None,
        *,
        response_format: dict | None = None,
    ) -> dict:
        effort = reasoning_effort or self.settings.hy3_reasoning_effort
        kwargs: dict = {
            "model": self.settings.hy3_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "top_p": 1.0,
        }
        if self.settings.hy3_enable_reasoning_param:
            if self.settings.hy3_reasoning_param_style == "direct":
                kwargs["extra_body"] = {"reasoning_effort": effort}
            else:
                kwargs["extra_body"] = {"chat_template_kwargs": {"reasoning_effort": effort}}
        if response_format is not None:
            kwargs["response_format"] = response_format
        return kwargs

    def _call_with_retry(self, kwargs: dict) -> str:
        last_exc: Exception | None = None
        attempts = self.settings.hy3_max_retries + 1
        for attempt in range(attempts):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content if resp.choices else None
                if not content or not content.strip():
                    raise Hy3ResponseError(
                        user_message="Hy3 返回了空内容，请稍后重试或使用其它文档。"
                    )
                return content
            except (
                AuthenticationError,
                RateLimitError,
                APITimeoutError,
                APIConnectionError,
                APIStatusError,
                APIError,
            ) as exc:
                if self._should_retry_without_response_format(exc, kwargs):
                    fallback_kwargs = dict(kwargs)
                    fallback_kwargs.pop("response_format", None)
                    return self._call_with_retry(fallback_kwargs)
                last_exc = exc
                mapped = self._map_exception(exc)
                # 仅在可重试且仍有次数时退避
                if isinstance(exc, _RETRYABLE) and attempt < attempts - 1:
                    backoff = min(2 ** (attempt + 1), 30)
                    time.sleep(backoff)
                    continue
                raise mapped from exc
        # 理论上不会到达，保险起见
        raise self._map_exception(last_exc) if last_exc else Hy3ResponseError()

    @staticmethod
    def _should_retry_without_response_format(exc: Exception, kwargs: dict) -> bool:
        """网关明确拒绝结构化输出参数时，回退到普通 JSON 文本。"""
        if "response_format" not in kwargs or not isinstance(exc, APIStatusError):
            return False
        if exc.status_code not in (400, 404, 422):
            return False
        detail = str(exc).lower()
        return any(
            marker in detail
            for marker in ("response_format", "json_schema", "structured output", "unsupported")
        )

    @staticmethod
    def _map_exception(exc: Exception) -> Exception:
        if isinstance(exc, AuthenticationError):
            return Hy3AuthenticationError(
                str(exc), user_message="Hy3 鉴权失败，请检查 .env 中的 HY3_API_KEY 是否正确。"
            )
        if isinstance(exc, RateLimitError):
            return Hy3RateLimitError(str(exc), user_message="Hy3 接口限流，请稍后重试。")
        if isinstance(exc, APITimeoutError):
            return Hy3TimeoutError(str(exc), user_message="Hy3 响应超时，请稍后重试。")
        if isinstance(exc, APIConnectionError):
            return Hy3ResponseError(
                str(exc),
                user_message="无法连接到 Hy3 服务，请检查 .env 中的 HY3_BASE_URL 是否正确。",
            )
        if isinstance(exc, APIStatusError):
            return Hy3ResponseError(
                f"Hy3 返回状态码 {exc.status_code}",
                user_message=f"Hy3 返回异常状态码 {exc.status_code}，请稍后重试。",
            )
        return Hy3ResponseError(str(exc), user_message="Hy3 返回了异常响应，请稍后重试。")

    # ------------------------------------------------------------------ #
    def generate_text(self, system: str, user: str, *, reasoning_effort: str | None = None) -> str:
        kwargs = self._build_kwargs(system, user, reasoning_effort)
        return self._call_with_retry(kwargs)

    def generate_validated(
        self, system: str, user: str, target_type: Type[T], *, reasoning_effort: str | None = None
    ) -> T:
        response_format = (
            self._json_schema_response_format(target_type)
            if self.settings.hy3_enable_response_format
            else None
        )
        kwargs = self._build_kwargs(
            system,
            user,
            reasoning_effort,
            response_format=response_format,
        )
        raw = self._call_with_retry(kwargs)
        try:
            data = extract_json_object(raw)
            return target_type.model_validate(data)
        except (JsonParseError, ValidationError) as exc:
            # 仅修复一次
            fix_user = build_json_fix_prompt(target_type.__name__, str(exc)[:500], raw)
            try:
                fix_kwargs = self._build_kwargs(
                    system,
                    fix_user,
                    "no_think",
                    response_format=response_format,
                )
                raw2 = self._call_with_retry(fix_kwargs)
                data2 = extract_json_object(raw2)
                return target_type.model_validate(data2)
            except (JsonParseError, ValidationError) as exc2:
                raise SchemaValidationError(
                    "模型输出格式异常，可重试。", user_message="模型输出格式异常，可点击重试。"
                ) from exc2


class FakeHy3Client(Hy3ClientBase):
    """测试用假客户端：按目标类型名返回预置响应，不访问网络。"""

    def __init__(
        self,
        responses: dict[str, BaseModel] | None = None,
        raw_responses: dict[str, str] | None = None,
    ) -> None:
        self._responses = responses or {}
        self._raw = raw_responses or {}
        self.calls: list[tuple[str, str]] = []

    def _pick(self, target_type: Type[T]) -> T:
        key = target_type.__name__
        if key in self._responses:
            return self._responses[key]  # type: ignore[return-value]
        if key in self._raw:
            from .json_parser import extract_json_object

            raw = self._raw[key]
            data = raw if isinstance(raw, dict) else extract_json_object(raw)
            return target_type.model_validate(data)
        raise RuntimeError(f"FakeHy3Client 未提供 {key} 的响应")

    def generate_text(self, system: str, user: str, *, reasoning_effort: str | None = None) -> str:
        self.calls.append((system, user))
        return "{}"

    def generate_validated(
        self, system: str, user: str, target_type: Type[T], *, reasoning_effort: str | None = None
    ) -> T:
        self.calls.append((system, user))
        return self._pick(target_type)
