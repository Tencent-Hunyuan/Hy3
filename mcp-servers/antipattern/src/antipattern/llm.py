"""Hy3 LLM 调用抽象层（OpenAI 兼容协议）。"""

import asyncio
import logging
import os

from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

logger = logging.getLogger("antipattern")

# 默认超时（秒）：连接 10s，总读取 120s（深度推理可能很慢）
_DEFAULT_TIMEOUT = 120.0
_MAX_TOKENS = 4096


class LLMError(Exception):
    """LLM 调用失败时抛出，携带用户友好的错误信息。"""
    pass


class Hy3Client:
    """封装 Hy3 API 调用，支持 reasoning_effort 分层。"""

    def __init__(self):
        self.client = OpenAI(
            base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
            api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
            timeout=_DEFAULT_TIMEOUT,
        )
        self.model = os.environ.get("HY3_MODEL", "hy3")

    def _call_sync(self, system: str, user: str, deep: bool) -> str:
        """同步调用（内部方法，由 async 包装调用）。"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.9,
                top_p=1.0,
                max_tokens=_MAX_TOKENS,
                extra_body={
                    "chat_template_kwargs": {
                        "reasoning_effort": "high" if deep else "no_think"
                    }
                },
            )
        except APITimeoutError:
            raise LLMError("Hy3 响应超时（120s），请检查服务端是否正常运行。")
        except APIConnectionError:
            raise LLMError("无法连接 Hy3 API，请检查 HY3_BASE_URL 配置。")
        except RateLimitError:
            raise LLMError("Hy3 API 限流（429），请稍后重试。")
        except APIError as e:
            raise LLMError(f"Hy3 API 错误：{e.status_code} - {e.message}")

        # 防护：choices 为空或 content 为 None
        if not resp.choices:
            raise LLMError("Hy3 返回空响应（无 choices）。")
        content = resp.choices[0].message.content
        if content is None:
            raise LLMError("Hy3 返回空内容（content=null），可能是模型拒绝或参数异常。")
        return content

    async def reason(self, system: str, user: str, deep: bool = True) -> str:
        """异步深度推理调用（不阻塞事件循环）。

        Args:
            system: 系统提示（persona + 策略注入）
            user: 用户输入内容
            deep: True 使用 reasoning_effort="high"（策略推理），
                  False 使用 "no_think"（轻量格式化）
        """
        logger.info("LLM call: model=%s, deep=%s, system_len=%d, user_len=%d",
                    self.model, deep, len(system), len(user))
        return await asyncio.to_thread(self._call_sync, system, user, deep)

    async def format(self, system: str, user: str) -> str:
        """轻量格式化调用（不需要深度思维链）。"""
        return await self.reason(system, user, deep=False)
