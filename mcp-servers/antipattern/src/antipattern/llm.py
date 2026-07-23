"""Hy3 LLM 调用抽象层（OpenAI 兼容协议）。

支持：per-tool temperature、指数退避重试（429/5xx）、流式输出。
stdio 模式下为单连接，流式迭代直接同步阻塞事件循环即可。
"""

import logging
import os
import time
from typing import Generator

from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

logger = logging.getLogger("antipattern")

_DEFAULT_TIMEOUT = 120.0
_MAX_TOKENS = 4096
_MAX_RETRIES = 2
_RETRY_DELAYS = (2.0, 4.0)  # 指数退避间隔


class LLMError(Exception):
    """LLM 调用失败时抛出，携带用户友好的错误信息。"""
    pass


def _is_retryable(exc: Exception) -> bool:
    """判断异常是否值得重试（429 限流、5xx 服务端错误、连接超时）。"""
    if isinstance(exc, (RateLimitError, APITimeoutError, APIConnectionError)):
        return True
    if isinstance(exc, APIError) and exc.status_code is not None and exc.status_code >= 500:
        return True
    return False


class Hy3Client:
    """封装 Hy3 API 调用，支持 reasoning_effort 分层、per-tool temperature、重试、流式。"""

    def __init__(self):
        self.client = OpenAI(
            base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
            api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
            timeout=_DEFAULT_TIMEOUT,
        )
        self.model = os.environ.get("HY3_MODEL", "hy3")

    def _build_params(self, system: str, user: str, deep: bool, temperature: float, stream: bool = False):
        """构造 API 调用参数。"""
        params = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            top_p=1.0,
            max_tokens=_MAX_TOKENS,
            extra_body={
                "chat_template_kwargs": {
                    "reasoning_effort": "high" if deep else "no_think"
                }
            },
        )
        if stream:
            params["stream"] = True
        return params

    def _call_sync(self, system: str, user: str, deep: bool, temperature: float) -> str:
        """同步非流式调用，带重试。"""
        last_exc = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(
                    **self._build_params(system, user, deep, temperature)
                )
                if not resp.choices:
                    raise LLMError("Hy3 返回空响应（无 choices）。")
                content = resp.choices[0].message.content
                if content is None:
                    raise LLMError("Hy3 返回空内容（content=null），可能是模型拒绝或参数异常。")
                return content
            except (APITimeoutError, APIConnectionError, RateLimitError, APIError) as e:
                last_exc = e
                if _is_retryable(e) and attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning("Hy3 API %s, retrying in %.0fs (attempt %d/%d)...",
                                   type(e).__name__, delay, attempt + 1, _MAX_RETRIES)
                    time.sleep(delay)
                    continue
                break

        # 所有重试耗尽，抛出用户友好错误
        if isinstance(last_exc, APITimeoutError):
            raise LLMError("Hy3 响应超时（120s），请检查服务端是否正常运行。")
        if isinstance(last_exc, APIConnectionError):
            raise LLMError("无法连接 Hy3 API，请检查 HY3_BASE_URL 配置。")
        if isinstance(last_exc, RateLimitError):
            raise LLMError("Hy3 API 限流（429），重试后仍失败，请稍后再试。")
        if isinstance(last_exc, APIError):
            raise LLMError(f"Hy3 API 错误：{last_exc.status_code} - {last_exc.message}")
        raise LLMError(f"未知错误：{last_exc}")

    def _stream_sync(self, system: str, user: str, deep: bool, temperature: float) -> Generator[str, None, None]:
        """同步流式调用，yield 文本 chunk。带重试（重试时重建整个 stream）。"""
        last_exc = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                stream = self.client.chat.completions.create(
                    **self._build_params(system, user, deep, temperature, stream=True)
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return  # 流正常结束
            except (APITimeoutError, APIConnectionError, RateLimitError, APIError) as e:
                last_exc = e
                if _is_retryable(e) and attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning("Hy3 stream %s, retrying in %.0fs (attempt %d/%d)...",
                                   type(e).__name__, delay, attempt + 1, _MAX_RETRIES)
                    time.sleep(delay)
                    continue
                break

        if isinstance(last_exc, APITimeoutError):
            raise LLMError("Hy3 响应超时（120s），请检查服务端是否正常运行。")
        if isinstance(last_exc, APIConnectionError):
            raise LLMError("无法连接 Hy3 API，请检查 HY3_BASE_URL 配置。")
        if isinstance(last_exc, RateLimitError):
            raise LLMError("Hy3 API 限流（429），重试后仍失败，请稍后再试。")
        if isinstance(last_exc, APIError):
            raise LLMError(f"Hy3 API 错误：{last_exc.status_code} - {last_exc.message}")
        raise LLMError(f"未知错误：{last_exc}")

    async def reason(self, system: str, user: str, deep: bool = True, temperature: float = 0.9) -> str:
        """异步非流式调用（完整返回）。

        Args:
            system: 系统提示（persona + 策略注入）
            user: 用户输入内容
            deep: True 使用 reasoning_effort="high"，False 使用 "no_think"
            temperature: 采样温度（challenge=0.9, remix=1.0, stress=0.65, escalate=0.85）
        """
        import asyncio
        logger.info("LLM call: model=%s, deep=%s, temp=%.2f, system_len=%d, user_len=%d",
                    self.model, deep, temperature, len(system), len(user))
        return await asyncio.to_thread(self._call_sync, system, user, deep, temperature)

    def reason_stream(self, system: str, user: str, deep: bool = True, temperature: float = 0.9) -> Generator[str, None, None]:
        """同步流式调用，yield 文本 chunk。

        stdio 单连接模式下直接同步迭代，不阻塞其他请求（因为没有其他请求）。
        """
        logger.info("LLM stream: model=%s, deep=%s, temp=%.2f, system_len=%d, user_len=%d",
                    self.model, deep, temperature, len(system), len(user))
        return self._stream_sync(system, user, deep, temperature)

    async def format(self, system: str, user: str, temperature: float = 0.7) -> str:
        """轻量格式化调用（不需要深度思维链）。"""
        return await self.reason(system, user, deep=False, temperature=temperature)
