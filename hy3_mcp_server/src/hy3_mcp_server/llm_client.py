"""Hy3 LLM 客户端。

通过 OpenAI 兼容协议调用 Hy3 API，所有配置从环境变量读取。

用法：
    from hy3_mcp_server.llm_client import LLMClient
    client = LLMClient()
    reply = client.chat([{"role": "user", "content": "你好"}])
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI


class LLMConfigError(RuntimeError):
    pass


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    temperature: float
    top_p: float
    reasoning_effort: str


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise LLMConfigError(f"环境变量 {name} 未设置，请在 .env 中配置。")
    return value


def load_config() -> LLMConfig:
    """从环境变量加载 Hy3 配置。"""
    api_key = _require("HY3_API_KEY")
    base_url = os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1").strip()
    model = os.environ.get("HY3_MODEL", "hy3").strip()

    if base_url.rstrip("/").endswith("/chat/completions"):
        raise LLMConfigError(
            f"HY3_BASE_URL 应以 /v1 结尾，当前值 '{base_url}' 包含了多余的 /chat/completions。"
        )

    return LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=float(os.environ.get("LLM_TEMPERATURE", "0.9")),
        top_p=float(os.environ.get("LLM_TOP_P", "1.0")),
        reasoning_effort=os.environ.get("LLM_REASONING_EFFORT", "high").strip(),
    )


class LLMClient:
    """Hy3 对话客户端。"""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or load_config()
        self._client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def chat(self, messages: list[dict[str, str]], *, temperature: float | None = None, top_p: float | None = None) -> str:
        """发起对话补全，返回回复文本。"""
        kwargs: dict = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature if temperature is None else temperature,
            "top_p": self.config.top_p if top_p is None else top_p,
            "extra_body": {
                "chat_template_kwargs": {"reasoning_effort": self.config.reasoning_effort}
            },
        }
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


def describe_active_backend() -> str:
    """返回当前后端描述（不含密钥）。"""
    cfg = load_config()
    return f"provider=hy3 base_url={cfg.base_url} model={cfg.model}"
